import time
from typing import Dict, Optional
from sqlmodel import SQLModel, Field, JSON
from app.models.enums import JobStatus

class Job(SQLModel, table=True):
    id: str = Field(primary_key=True)
    feature_name: str
    status: JobStatus = Field(default=JobStatus.PENDING)
    current_step_index: int = Field(default=0)

    context: Dict = Field(default_factory=dict, sa_type=JSON)

    error_log: Optional[str] = None
    error_code: Optional[str] = None
    retryable: Optional[bool] = None

    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    last_progress_at: float = Field(default_factory=time.time)
