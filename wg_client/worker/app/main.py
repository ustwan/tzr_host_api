import os
import json
import asyncio
from .adapters.redis_queue import RedisQueue
from .usecases.process_event import ProcessEventUseCase

REDIS_URL = os.getenv("REDIS_URL", "redis://api_father_redis:6379/0")
QUEUE_REQUESTS = os.getenv("QUEUE_REQUESTS", "queue:requests")


async def main() -> None:
    queue = RedisQueue(REDIS_URL)
    uc = ProcessEventUseCase()
    print(f"[worker] started. listening on {QUEUE_REQUESTS}")

    while True:
        try:
            item = await queue.brpop(QUEUE_REQUESTS, timeout=10)
            if not item:
                continue
            _, raw = item
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"raw": raw.decode("utf-8", errors="ignore")}
            print(f"[worker] got: {payload}")
            await uc.execute(payload)
        except Exception as e:
            print(f"[worker] error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
