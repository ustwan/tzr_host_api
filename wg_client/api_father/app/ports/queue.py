from typing import Protocol


class Queue(Protocol):
    async def enqueue(self, name: str, item: dict) -> None:
        ...



