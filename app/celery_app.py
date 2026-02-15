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
    },
    "promote-waiting-jobs": {
        "task": "worker.tasks.promote_waiting_jobs",
        "schedule": 300.0,  # Every 5 minutes
    }
}

# Enable priority support in Celery
celery_app.conf.task_acks_late = True
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.broker_transport_options = {
    'priority_steps': list(range(10)),  # Enable 0-9 priority levels
}
