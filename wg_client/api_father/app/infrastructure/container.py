from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from adapters.mysql_user_repository import MysqlUserRepository
from adapters.socket_game_server_client import SocketGameServerClient
from adapters.redis_queue import RedisQueue
from adapters.telegram_group_checker import TelegramGroupChecker
from usecases.register_user import RegisterUserUseCase
from interfaces.http import build_router


@asynccontextmanager
async def build_app() -> AsyncIterator[FastAPI]:
    app = FastAPI(title="API_FATHER")

    # Создаем TelegramChecker (если токен не указан, проверка пропускается)
    tg_checker = TelegramGroupChecker()
    
    register_uc = RegisterUserUseCase(
        MysqlUserRepository(), 
        SocketGameServerClient(), 
        tg_checker,
        RedisQueue()
    )
    app.include_router(build_router(register_uc))

    app.state.game_server_host = None
    app.state.game_server_port = None
    try:
        yield app
    finally:
        pass


