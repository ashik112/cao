from pydantic import BaseModel, Field
from typing import Any, Dict

class StartJobRequest(BaseModel):
    feature_name: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    user_id: str  # Required for priority lookup

class JobCreateResponse(BaseModel):
    success: bool
    job_id: str
    priority: str  # Return assigned priority
    monitor_url: str
    status: str
