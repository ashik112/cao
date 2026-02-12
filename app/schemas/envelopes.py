from pydantic import BaseModel, Field
from typing import Any, Dict

class InputMeta(BaseModel):
    job_id: str
    step_index: int
    service_name: str
    attempt: int
    timestamp: int

class InputPayload(BaseModel):
    params: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)

class InputEnvelope(BaseModel):
    meta: InputMeta
    payload: InputPayload

class OutputEnvelope(BaseModel):
    status: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
