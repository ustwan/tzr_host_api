"""
FastAPI приложение для API_4
Тонкий каркас: маршруты и зависимости подключаются через DI-контейнер
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.utils.logger import setup_logger
from infrastructure.container import build_app


# Логирование
logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация API_4...")
    async with build_app(app) as _:
        yield
    logger.info("API_4 остановлен")


app = FastAPI(
    title="API_4 Battle Logs",
    description="API для работы с логами боёв (.tzb файлы)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
