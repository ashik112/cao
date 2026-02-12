import json
import redis
from app.config import REDIS_URL

r = redis.from_url(REDIS_URL, decode_responses=True)

class WSService:
    def publish(self, job_id: str, payload: dict):
        r.publish(f"ws:{job_id}", json.dumps(payload))
