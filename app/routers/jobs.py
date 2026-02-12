import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.dependencies import get_session
from app.schemas.jobs import StartJobRequest
from app.repositories.job_repository import JobRepository
from app.config import FEATURES, SERVICES
from worker.tasks import execute_job_step

router = APIRouter()

@router.post("/jobs", status_code=201)
def start_job(req: StartJobRequest, session: Session = Depends(get_session)):
    if req.feature_name not in FEATURES:
        raise HTTPException(400, "Unknown feature recipe")

    job_id = str(uuid.uuid4())
    repo = JobRepository(session)
    repo.create(job_id, req.feature_name, req.input_data)

    first_service = FEATURES[req.feature_name][0]
    queue = SERVICES[first_service]["queue"]
    execute_job_step.apply_async(args=[job_id], queue=queue)

    return {
        "success": True,
        "job_id": job_id,
        "monitor_url": f"ws://localhost:8000/ws/{job_id}",
        "status": "PENDING"
    }

@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str, session: Session = Depends(get_session)):
    repo = JobRepository(session)
    job = repo.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    prev = repo.clear_failure(job)

    recipe = FEATURES[job.feature_name]
    if job.current_step_index >= len(recipe):
        return {"success": True, "job_id": job_id, "previous_status": prev, "new_status": "COMPLETED", "resuming_from_step": None}

    next_service = recipe[job.current_step_index]
    queue = SERVICES[next_service]["queue"]
    execute_job_step.apply_async(args=[job_id], queue=queue)

    return {
        "success": True,
        "job_id": job_id,
        "previous_status": prev,
        "new_status": "RUNNING",
        "resuming_from_step": next_service
    }
