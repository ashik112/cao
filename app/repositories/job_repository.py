import time
from typing import Optional, Dict, Any
from sqlmodel import Session
from app.repositories.base_repository import BaseRepository
from app.models.job import Job
from app.models.enums import JobStatus

class JobRepository(BaseRepository):
    def get(self, job_id: str) -> Optional[Job]:
        return self.session.get(Job, job_id)

    def create(self, job_id: str, feature_name: str, initial_input: Dict[str, Any]) -> Job:
        job = Job(
            id=job_id,
            feature_name=feature_name,
            status=JobStatus.PENDING,
            context={"initial_input": initial_input},
        )
        self.session.add(job)
        self.session.commit()
        return job

    def set_status(self, job: Job, status: JobStatus):
        job.status = status
        job.updated_at = time.time()
        self.session.add(job)
        self.session.commit()

    def fail(self, job: Job, code: str, message: str, retryable: bool):
        job.status = JobStatus.FAILED
        job.error_code = code
        job.error_log = message
        job.retryable = retryable
        job.updated_at = time.time()
        self.session.add(job)
        self.session.commit()

    def clear_failure(self, job: Job) -> JobStatus:
        prev = job.status
        job.status = JobStatus.RUNNING
        job.error_code = None
        job.error_log = None
        job.retryable = None
        job.updated_at = time.time()
        self.session.add(job)
        self.session.commit()
        return prev

    def save_step(self, job: Job, step_key: str, step_payload: Dict[str, Any]):
        job.context[step_key] = step_payload
        job.last_progress_at = time.time()
        job.updated_at = time.time()
        self.session.add(job)
        self.session.commit()

    def bump_step_index(self, job: Job):
        job.current_step_index += 1
        job.last_progress_at = time.time()
        job.updated_at = time.time()
        self.session.add(job)
        self.session.commit()
