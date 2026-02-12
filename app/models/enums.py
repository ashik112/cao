from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class WebSocketEvent(str, Enum):
    CONNECT = "WS_CONNECTED"
    WAITING = "WAITING_FOR_SLOT"
    STEP_START = "STEP_STARTED"
    STEP_COMPLETE = "STEP_COMPLETED"
    JOB_COMPLETE = "JOB_COMPLETED"
    ERROR = "JOB_ERROR"

class StepStatus(str, Enum):
    SUCCESS = "SUCCESS"
