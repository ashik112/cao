import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/orchestrator")

JOB_STUCK_SECONDS = int(os.getenv("JOB_STUCK_SECONDS", "7200"))
SANITY_CHECK_INTERVAL_SECONDS = int(os.getenv("SANITY_CHECK_INTERVAL_SECONDS", "60"))

HTTP_CONNECT_TIMEOUT_S = float(os.getenv("HTTP_CONNECT_TIMEOUT_S", "3.0"))
HTTP_READ_TIMEOUT_S = float(os.getenv("HTTP_READ_TIMEOUT_S", "30.0"))

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

# External API for user priority lookup
PRIORITY_API_URL = os.getenv("PRIORITY_API_URL", "http://priority-service:8000")

# Priority promotion thresholds (in seconds)
PROMOTE_LOW_TO_MEDIUM_AFTER = int(os.getenv("PROMOTE_LOW_TO_MEDIUM_AFTER", "1800"))  # 30 min
PROMOTE_MEDIUM_TO_HIGH_AFTER = int(os.getenv("PROMOTE_MEDIUM_TO_HIGH_AFTER", "3600"))  # 60 min

# Celery queue names
QUEUE_HIGH = "high_priority"
QUEUE_MEDIUM = "medium_priority"
QUEUE_LOW = "low_priority"

# AI Service configurations - removed queue field, keeping concurrency limits
SERVICES = {
    "prompt_enhancer": {
        "limit": 5,
        "timeout": 120,
        "lease_ttl": 150,
        "max_step_attempts": 3,
        "base_url": os.getenv("PROMPT_ENHANCER_URL", "http://prompt-enhancer:9000"),
        "execute_path": "/v1/execute",
        "health_path": "/health",
        "auth": {"type": "api_key_header", "header": "X-Internal-Key"},
    },
    "fast_chat_llm": {
        "limit": 4,
        "timeout": 180,
        "lease_ttl": 210,
        "max_step_attempts": 3,
        "base_url": os.getenv("FAST_CHAT_LLM_URL", "http://fast-chat:9000"),
        "execute_path": "/v1/execute",
        "health_path": "/health",
        "auth": {"type": "api_key_header", "header": "X-Internal-Key"},
    },
    "image_gen": {
        "limit": 1,
        "timeout": 360,
        "lease_ttl": 400,
        "max_step_attempts": 2,
        "base_url": os.getenv("IMAGE_GEN_URL", "http://image-gen:9000"),
        "execute_path": "/v1/execute",
        "health_path": "/health",
        "auth": {"type": "api_key_header", "header": "X-Internal-Key"},
    },
    "model_3d_gen": {
        "limit": 1,
        "timeout": 420,
        "lease_ttl": 460,
        "max_step_attempts": 2,
        "base_url": os.getenv("MODEL_3D_GEN_URL", "http://model-3d-gen:9000"),
        "execute_path": "/v1/execute",
        "health_path": "/health",
        "auth": {"type": "api_key_header", "header": "X-Internal-Key"},
    },
}

# Multi-step pipeline definitions
FEATURES = {
    "full_pipeline": ["prompt_enhancer", "fast_chat_llm", "image_gen", "model_3d_gen"],
    "text_only": ["prompt_enhancer", "fast_chat_llm"],
}
