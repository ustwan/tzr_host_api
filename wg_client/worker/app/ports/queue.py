from typing import Optional, Tuple


class Queue:
    async def brpop(self, name: str, timeout: int) -> Optional[Tuple[str, bytes]]:
        raise NotImplementedError



