from typing import Optional, Tuple

from ports.user_repository import UserRepository
from ports.game_server_client import GameServerClient
from ports.queue import Queue
from ports.telegram_checker import TelegramChecker


class RegisterUserUseCase:
    def __init__(
        self, 
        repo: UserRepository, 
        gs_client: GameServerClient, 
        tg_checker: Optional[TelegramChecker] = None,
        queue: Queue | None = None, 
        requests_queue: str = "queue:requests"
    ):
        self._repo = repo
        self._gs = gs_client
        self._tg_checker = tg_checker
        self._queue = queue
        self._requests_queue = requests_queue

    async def execute(
        self,
        *,
        login: str,
        password: str,
        gender: int,
        telegram_id: int,
        username: Optional[str],
        game_server_host: str,
        game_server_port: int,
    ) -> None:
        # Проверка членства в Telegram группе (если настроено)
        if self._tg_checker is not None:
            if not await self._tg_checker.is_user_in_group(telegram_id):
                raise ValueError("not_in_group")
        
        # Проверка лимита - максимум 5 аккаунтов на telegram_id
        if await self._repo.count_telegram_players(telegram_id) >= 5:
            raise ValueError("limit_exceeded")

        # уникальность логина
        if await self._repo.is_login_taken(login):
            raise ValueError("login_taken")

        # создаём в БД
        await self._repo.insert_user_and_tgplayer(login, gender, telegram_id, username)

        # отправляем в game server
        await self._gs.register_user(
            host=game_server_host,
            port=game_server_port,
            login=login,
            password=password,
            gender=gender,
        )

        # необязательная постановка в очередь для последующей обработки
        if self._queue is not None:
            await self._queue.enqueue(self._requests_queue, {
                "type": "register",
                "login": login,
                "telegram_id": telegram_id,
            })


