import json
from typing import Optional

import redis


class RedisQueue:
    def __init__(self, url: Optional[str] = None):
        self._client = redis.from_url(url or "redis://api_father_redis:6379/0")

    async def enqueue(self, name: str, item: dict) -> None:
        # redis-py sync; keep simple for now
        self._client.rpush(name, json.dumps(item, ensure_ascii=False))



