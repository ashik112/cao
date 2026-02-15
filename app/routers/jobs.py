import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.dependencies import get_session
from app.schemas.jobs import StartJobRequest, JobCreateResponse
from app.repositories.job_repository import JobRepository
from app.config import FEATURES
from worker.tasks import execute_job_step

router = APIRouter()

@router.post("/jobs", status_code=201)
def start_job(req: StartJobRequest, session: Session = Depends(get_session)):
    if req.feature_name not in FEATURES:
        raise HTTPException(400, "Unknown feature recipe")
    
    from app.services.priority_service import PriorityService
    from app.config import QUEUE_HIGH, QUEUE_MEDIUM, QUEUE_LOW
    
    # 1. Fetch user priority from external API
    priority_service = PriorityService()
    priority = priority_service.get_user_priority(req.user_id)
    
    # 2. Create job with priority
    job_id = str(uuid.uuid4())
    repo = JobRepository(session)
    job = repo.create(job_id, req.feature_name, req.input_data)
    
    # Set priority fields
    job.priority = priority
    job.original_priority = priority
    job.user_id = req.user_id
    session.add(job)
    session.commit()
    
    # 3. Determine target queue based on priority
    queue_map = {
        "high": QUEUE_HIGH,
        "medium": QUEUE_MEDIUM,
        "low": QUEUE_LOW
    }
    target_queue = queue_map[priority]
    
    # 4. Queue first step to priority queue
    execute_job_step.apply_async(args=[job_id], queue=target_queue)

    return {
        "success": True,
        "job_id": job_id,
        "priority": priority,
        "monitor_url": f"ws://localhost:8000/ws/{job_id}",
        "status": "PENDING"
    }

@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str, session: Session = Depends(get_session)):
    from app.config import QUEUE_HIGH, QUEUE_MEDIUM, QUEUE_LOW
    
    repo = JobRepository(session)
    job = repo.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    prev = repo.clear_failure(job)

    recipe = FEATURES[job.feature_name]
    if job.current_step_index >= len(recipe):
        return {"success": True, "job_id": job_id, "previous_status": prev, "new_status": "COMPLETED", "resuming_from_step": None}

    # Route to priority queue based on job's current priority
    queue_map = {
        "high": QUEUE_HIGH,
        "medium": QUEUE_MEDIUM,
        "low": QUEUE_LOW
    }
    target_queue = queue_map.get(job.priority, QUEUE_MEDIUM)
    
    execute_job_step.apply_async(args=[job_id], queue=target_queue)

    return {
        "success": True,
        "job_id": job_id,
        "previous_status": prev,
        "new_status": "RUNNING",
        "resuming_from_step": recipe[job.current_step_index]
    }
