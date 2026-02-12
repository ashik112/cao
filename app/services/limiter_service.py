import time
import uuid
import redis
from typing import Optional
from app.config import REDIS_URL

r = redis.from_url(REDIS_URL, decode_responses=True)

class LimiterService:
    def acquire(self, service_name: str, limit: int, lease_ttl: int, wait_timeout: int) -> Optional[str]:
        token = str(uuid.uuid4())
        counter_key = f"conc:{service_name}"
        lease_key = f"lease:{service_name}:{token}"

        lua = """
        local counter_key = KEYS[1]
        local lease_key = KEYS[2]
        local limit = tonumber(ARGV[1])
        local ttl = tonumber(ARGV[2])

        local cur = tonumber(redis.call("GET", counter_key) or "0")
        if cur >= limit then
            return nil
        end

        redis.call("INCR", counter_key)
        redis.call("SET", lease_key, "1", "EX", ttl)
        return lease_key
        """

        start = time.time()
        while True:
            lease = r.eval(lua, 2, counter_key, lease_key, str(limit), str(lease_ttl))
            if lease:
                return lease
            if time.time() - start > wait_timeout:
                return None
            time.sleep(0.5)

    def release(self, service_name: str, lease_key: str):
        counter_key = f"conc:{service_name}"
        lua = """
        local counter_key = KEYS[1]
        local lease_key = KEYS[2]
        if redis.call("DEL", lease_key) == 1 then
            local cur = tonumber(redis.call("GET", counter_key) or "0")
            if cur > 0 then redis.call("DECR", counter_key) end
        end
        return 1
        """
        r.eval(lua, 2, counter_key, lease_key)
