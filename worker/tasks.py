import time
import redis
from celery import Task
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, create_engine

from app.celery_app import celery_app
from app.config import DATABASE_URL, FEATURES, SERVICES, JOB_STUCK_SECONDS, REDIS_URL
from app.repositories.job_repository import JobRepository
from app.services.ws_service import WSService
from app.services.limiter_service import LimiterService, r as redis_conn
from app.services.http_service_client import HTTPServiceClient
from app.services.orchestrator_service import OrchestratorService
from app.models.enums import JobStatus

engine = create_engine(DATABASE_URL)
r = redis.from_url(REDIS_URL, decode_responses=True)

class BaseTaskWithRetry(Task):
    autoretry_for = (redis.exceptions.RedisError, OperationalError)
    retry_kwargs = {"max_retries": 10, "countdown": 3}
    retry_backoff = True

@celery_app.task(bind=True, base=BaseTaskWithRetry, acks_late=True)
def execute_job_step(self, job_id: str):
    with Session(engine) as session:
        repo = JobRepository(session)
        orchestrator = OrchestratorService(
            repo=repo,
            ws=WSService(),
            limiter=LimiterService(),
            client=HTTPServiceClient()
        )

        result = orchestrator.execute_one_step(job_id)
        if result in ("OK", "SKIPPED_ALREADY_DONE"):
            # queue next step
            job = repo.get(job_id)
            if not job:
                return "JOB_NOT_FOUND"
            recipe = FEATURES[job.feature_name]
            if job.current_step_index < len(recipe):
                next_service = recipe[job.current_step_index]
                next_queue = SERVICES[next_service]["queue"]
                execute_job_step.apply_async(args=[job_id], queue=next_queue)
            else:
                repo.set_status(job, JobStatus.COMPLETED)
        return result

@celery_app.task
def reap_expired_leases():
    # recompute counters from leases
    from app.services.limiter_service import r as rr
    for svc in SERVICES.keys():
        leases = rr.keys(f"lease:{svc}:*")
        rr.set(f"conc:{svc}", len(leases))

@celery_app.task
def sanity_check_stuck_jobs():
    now = time.time()
    with Session(engine) as session:
        # lightweight raw query to avoid heavy ORM scans; optimize later
        rows = session.exec("SELECT id, last_progress_at FROM job WHERE status='RUNNING'").all()
        repo = JobRepository(session)
        ws = WSService()
        for job_id, last_prog in rows:
            if now - float(last_prog) > JOB_STUCK_SECONDS:
                job = repo.get(job_id)
                if not job or job.status != JobStatus.RUNNING:
                    continue
                repo.fail(job, "STUCK_DETECTED", f"No progress > {JOB_STUCK_SECONDS}s", True)
                ws.publish(job_id, {
                    "type": "JOB_ERROR",
                    "job_id": job_id,
                    "error_code": "STUCK_DETECTED",
                    "message": "Job paused due to inactivity. You can resume.",
                    "action": "RETRY_AVAILABLE"
                })
