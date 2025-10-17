from typing import Protocol


class GameServerClient(Protocol):
    async def register_user(self, *, host: str, port: int, login: str, password: str, gender: int) -> None:
        ...



