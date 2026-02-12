from celery import Celery
from app.config import REDIS_URL, SANITY_CHECK_INTERVAL_SECONDS

celery_app = Celery("cao", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.beat_schedule = {
    "sanity-check-stuck-jobs": {
        "task": "worker.tasks.sanity_check_stuck_jobs",
        "schedule": SANITY_CHECK_INTERVAL_SECONDS,
    },
    "reap-expired-leases": {
        "task": "worker.tasks.reap_expired_leases",
        "schedule": 30.0,
    }
}
