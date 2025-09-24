import os
import json
import time
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://api_father_redis:6379/0")
QUEUE_REQUESTS = os.getenv("QUEUE_REQUESTS", "queue:requests")

r = redis.from_url(REDIS_URL)
print(f"[worker] started. listening on {QUEUE_REQUESTS}")

while True:
    try:
        item = r.brpop(QUEUE_REQUESTS, timeout=10)
        if not item:
            continue
        _, raw = item
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw.decode("utf-8", errors="ignore")}
        print(f"[worker] got: {payload}")
        # TODO: here do actual processing (DB writes, calls, etc.)
    except Exception as e:
        print(f"[worker] error: {e}")
        time.sleep(1)
