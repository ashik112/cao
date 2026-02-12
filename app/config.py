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

SERVICES = {
    "video_gen_v2": {
        "limit": 2, "queue": "heavy", "timeout": 600, "lease_ttl": 660, "max_step_attempts": 3,
        "base_url": os.getenv("VIDEO_GEN_V2_URL", "http://video-gen:9000"),
        "execute_path": "/v1/execute", "health_path": "/health",
        "auth": {"type": "api_key_header", "header": "X-Internal-Key"},
    },
    "fast_chat_llm": {
        "limit": 15, "queue": "medium", "timeout": 15, "lease_ttl": 30, "max_step_attempts": 5,
        "base_url": os.getenv("FAST_CHAT_LLM_URL", "http://fast-chat:9000"),
        "execute_path": "/v1/execute", "health_path": "/health",
        "auth": {"type": "api_key_header", "header": "X-Internal-Key"},
    },
    "summarizer_pro": {
        "limit": 10, "queue": "medium", "timeout": 30, "lease_ttl": 60, "max_step_attempts": 5,
        "base_url": os.getenv("SUMMARIZER_PRO_URL", "http://summarizer:9000"),
        "execute_path": "/v1/execute", "health_path": "/health",
        "auth": {"type": "api_key_header", "header": "X-Internal-Key"},
    },
    "prompt_enhancer": {
        "limit": 50, "queue": "default", "timeout": 5, "lease_ttl": 15, "max_step_attempts": 6,
        "base_url": os.getenv("PROMPT_ENHANCER_URL", "http://prompt-enhancer:9000"),
        "execute_path": "/v1/execute", "health_path": "/health",
        "auth": {"type": "api_key_header", "header": "X-Internal-Key"},
    },
    "email_notifier": {
        "limit": 100, "queue": "default", "timeout": 5, "lease_ttl": 15, "max_step_attempts": 6,
        "base_url": os.getenv("EMAIL_NOTIFIER_URL", "http://email-notifier:9000"),
        "execute_path": "/v1/execute", "health_path": "/health",
        "auth": {"type": "api_key_header", "header": "X-Internal-Key"},
    },
}

FEATURES = {
    "business_plan": ["prompt_enhancer", "fast_chat_llm", "summarizer_pro", "email_notifier"],
    "viral_video": ["prompt_enhancer", "video_gen_v2", "email_notifier"],
}
