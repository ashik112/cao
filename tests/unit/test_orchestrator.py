import pytest
from unittest.mock import MagicMock
from app.services.orchestrator_service import OrchestratorService
from app.models.enums import JobStatus, StepStatus
from app.services.http_service_client import ServiceCallError

def test_orchestrator_execute_success(session, mocker):
    # Mock dependencies
    repo = MagicMock()
    ws = MagicMock()
    limiter = MagicMock()
    client = MagicMock()
    
    # Mock job retrieval
    job = MagicMock()
    job.id = "job-1"
    job.feature_name = "business_plan" # Valid feature
    job.status = JobStatus.PENDING
    job.current_step_index = 0
    job.context = {}
    repo.get.return_value = job

    # Simulate bump_step_index behavior
    def bump_side_effect(j):
        j.current_step_index += 1
    repo.bump_step_index.side_effect = bump_side_effect
    
    # Mock limiter lease
    limiter.acquire.return_value = "lease-token"
    
    # Mock service client response
    client.call.return_value = {"status": "SUCCESS", "data": {"result": "ok"}}
    
    service = OrchestratorService(repo, ws, limiter, client)
    result = service.execute_one_step("job-1")
    
    assert result == "OK", f"Failed with: {repo.fail.call_args}"
    repo.set_status.assert_called_with(job, JobStatus.RUNNING)
    repo.save_step.assert_called()
    repo.bump_step_index.assert_called()
    limiter.release.assert_called()

def test_orchestrator_max_attemps(session, mocker):
    repo = MagicMock()
    ws = MagicMock()
    limiter = MagicMock()
    client = MagicMock()
    
    job = MagicMock()
    job.id = "job-1"
    job.feature_name = "business_plan"
    job.current_step_index = 0
    # Simulate max attempts reached
    job.context = {"step_0_prompt_enhancer__attempts": 10} 
    repo.get.return_value = job
    
    service = OrchestratorService(repo, ws, limiter, client)
    result = service.execute_one_step("job-1")
    
    assert result == "FAILED"
    from unittest.mock import ANY
    repo.fail.assert_called_with(job, "MAX_STEP_ATTEMPTS", ANY, False)
