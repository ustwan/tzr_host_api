import redis
from typing import Optional, Tuple

from ..ports.queue import Queue


class RedisQueue(Queue):
    def __init__(self, url: str):
        self._r = redis.from_url(url)

    async def brpop(self, name: str, timeout: int) -> Optional[Tuple[str, bytes]]:
        # sync client; keep simple
        return self._r.brpop(name, timeout=timeout)



