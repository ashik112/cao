import time
from sqlalchemy.exc import OperationalError
from app.config import FEATURES, SERVICES
from app.models.enums import JobStatus, WebSocketEvent, StepStatus
from app.repositories.job_repository import JobRepository
from app.services.ws_service import WSService
from app.services.limiter_service import LimiterService
from app.services.http_service_client import HTTPServiceClient, ServiceCallError

class OrchestratorService:
    def __init__(self, repo: JobRepository, ws: WSService, limiter: LimiterService, client: HTTPServiceClient):
        self.repo = repo
        self.ws = ws
        self.limiter = limiter
        self.client = client

    def execute_one_step(self, job_id: str) -> str:
        job = self.repo.get(job_id)
        if not job:
            return "JOB_NOT_FOUND"
        if job.status in (JobStatus.CANCELLED, JobStatus.COMPLETED):
            return f"STOPPED_{job.status}"
        if job.feature_name not in FEATURES:
            self.repo.fail(job, "INVALID_FEATURE", f"Unknown feature {job.feature_name}", False)
            self.ws.publish(job_id, {"type": WebSocketEvent.ERROR, "job_id": job_id,
                                    "error_code": "INVALID_FEATURE", "message": "Unknown feature",
                                    "action": "CONTACT_SUPPORT"})
            return "FAILED"

        recipe = FEATURES[job.feature_name]
        total_steps = len(recipe)

        if job.current_step_index >= total_steps:
            self.repo.set_status(job, JobStatus.COMPLETED)
            self.ws.publish(job_id, {"type": WebSocketEvent.JOB_COMPLETE, "job_id": job_id, "message": "Job completed"})
            return "DONE"

        step_index = job.current_step_index
        service_name = recipe[step_index]
        conf = SERVICES[service_name]

        step_key = f"step_{step_index}_{service_name}"
        attempts_key = f"{step_key}__attempts"

        # Idempotency at orchestrator level: skip if already recorded
        existing = job.context.get(step_key)
        if existing and existing.get("status") == StepStatus.SUCCESS:
            prev = job.current_step_index
            self.repo.bump_step_index(job)
            if job.current_step_index <= prev:
                self.repo.fail(job, "LOOP_DETECTED", "Step index did not advance", True)
                return "FAILED"
            return "SKIPPED_ALREADY_DONE"

        attempts = int(job.context.get(attempts_key, 0))
        if attempts >= conf["max_step_attempts"]:
            self.repo.fail(job, "MAX_STEP_ATTEMPTS", f"Exceeded attempts for {step_key}", False)
            self.ws.publish(job_id, {"type": WebSocketEvent.ERROR, "job_id": job_id,
                                    "error_code": "MAX_STEP_ATTEMPTS",
                                    "message": "Exceeded attempts for step", "action": "CONTACT_SUPPORT"})
            return "FAILED"

        self.ws.publish(job_id, {"type": WebSocketEvent.WAITING, "job_id": job_id,
                                "step_name": service_name, "step_index": step_index,
                                "total_steps": total_steps, "message": "Waiting for capacity..."})

        lease = self.limiter.acquire(service_name, conf["limit"], conf["lease_ttl"], conf["timeout"])
        if not lease:
            self.repo.fail(job, "RESOURCE_EXHAUSTED", f"Semaphore timeout after {conf['timeout']}s", True)
            self.ws.publish(job_id, {"type": WebSocketEvent.ERROR, "job_id": job_id,
                                    "error_code": "RESOURCE_EXHAUSTED",
                                    "message": "Service busy. Resume available.", "action": "RETRY_AVAILABLE"})
            return "FAILED"

        try:
            # bump attempts
            job.context[attempts_key] = attempts + 1
            self.repo.set_status(job, JobStatus.RUNNING)

            self.ws.publish(job_id, {"type": WebSocketEvent.STEP_START, "job_id": job_id,
                                    "step_name": service_name, "step_index": step_index,
                                    "total_steps": total_steps, "message": f"Running {service_name}..."})

            envelope = {
                "meta": {
                    "job_id": job_id,
                    "step_index": step_index,
                    "service_name": service_name,
                    "attempt": attempts + 1,
                    "timestamp": int(time.time()),
                },
                "payload": {
                    "params": job.context.get("params", {}),
                    "context": job.context,
                }
            }

            t0 = time.time()
            out = self.client.call(service_name, envelope, conf["timeout"])
            exec_ms = int((time.time() - t0) * 1000)

            step_payload = {
                "status": StepStatus.SUCCESS,
                "data": out.get("data", {}),
                "metrics": {**out.get("metrics", {}), "execution_time_ms": exec_ms},
                "timestamp": int(time.time()),
            }
            self.repo.save_step(job, step_key, step_payload)

            prev = job.current_step_index
            self.repo.bump_step_index(job)
            if job.current_step_index <= prev:
                self.repo.fail(job, "LOOP_DETECTED", "Step index did not advance", True)
                return "FAILED"

            self.ws.publish(job_id, {"type": WebSocketEvent.STEP_COMPLETE, "job_id": job_id,
                                    "step_name": service_name, "step_index": step_index,
                                    "total_steps": total_steps, "message": f"Completed {service_name}"})
            return "OK"

        except OperationalError as e:
            # Let Celery retry for DB outages (handled in worker)
            raise

        except ServiceCallError as e:
            self.repo.fail(job, e.code, str(e), e.retryable)
            self.ws.publish(job_id, {"type": WebSocketEvent.ERROR, "job_id": job_id,
                                    "error_code": e.code, "message": str(e),
                                    "action": "RETRY_AVAILABLE" if e.retryable else "CONTACT_SUPPORT"})
            return "FAILED"

        finally:
            self.limiter.release(service_name, lease)
