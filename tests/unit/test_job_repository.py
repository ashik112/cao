import pytest
from app.repositories.job_repository import JobRepository
from app.models.enums import JobStatus

def test_create_job(session):
    repo = JobRepository(session)
    job = repo.create("job-1", "feature-1", {"input": "test"})
    assert job.id == "job-1"
    assert job.status == JobStatus.PENDING
    assert job.context["initial_input"] == {"input": "test"}

def test_job_transitions(session):
    repo = JobRepository(session)
    job = repo.create("job-2", "feature-1", {})
    
    repo.set_status(job, JobStatus.RUNNING)
    updated = repo.get("job-2")
    assert updated.status == JobStatus.RUNNING
    
    repo.fail(job, "ERROR_CODE", "Error message", True)
    failed = repo.get("job-2")
    assert failed.status == JobStatus.FAILED
    assert failed.error_code == "ERROR_CODE"
    assert failed.retryable is True
    
    repo.clear_failure(job)
    cleared = repo.get("job-2")
    assert cleared.status == JobStatus.RUNNING
    assert cleared.error_code is None
