from typing import Optional


class UserRepository:
    async def count_telegram_players(self, telegram_id: int) -> int:
        raise NotImplementedError

    async def is_login_taken(self, login: str) -> bool:
        raise NotImplementedError

    async def insert_user_and_tgplayer(self, login: str, gender: int, telegram_id: int, username: Optional[str]) -> None:
        raise NotImplementedError



