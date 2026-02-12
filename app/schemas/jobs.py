from pydantic import BaseModel, Field
from typing import Any, Dict

class StartJobRequest(BaseModel):
    feature_name: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
