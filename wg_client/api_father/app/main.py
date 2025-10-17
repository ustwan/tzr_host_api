from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import os
import json
import pymysql
import redis

from shared.utils.logger import setup_logger
from adapters.mysql_user_repository import MysqlUserRepository
from adapters.socket_game_server_client import SocketGameServerClient
from adapters.redis_queue import RedisQueue
from adapters.telegram_group_checker import TelegramGroupChecker
from usecases.register_user import RegisterUserUseCase
from interfaces.http import build_router
from infrastructure.db import get_dsn_and_db

app = FastAPI(title="API_FATHER")

# CORS middleware для Swagger UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


## get_dsn_and_db moved to infrastructure/db.py


@asynccontextmanager
async def lifespan(app: FastAPI):
    # game server settings
    mode = os.getenv("GAME_SERVER_MODE", "test").lower()
    if mode == "prod":
        app.state.game_server_host = os.getenv("GAME_SERVER_PROD_HOST", os.getenv("GAME_SERVER_HOST", "10.8.0.4"))
        app.state.game_server_port = int(os.getenv("GAME_SERVER_PROD_PORT", os.getenv("GAME_SERVER_PORT", "5190")))
    else:
        app.state.game_server_host = os.getenv("GAME_SERVER_TEST_HOST", "game_server_mock")
        app.state.game_server_port = int(os.getenv("GAME_SERVER_TEST_PORT", "5190"))

    # usecase
    queue_name = os.getenv("QUEUE_REQUESTS", "queue:requests")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_checker = TelegramGroupChecker(telegram_token) if telegram_token else None
    app.state.register_uc = RegisterUserUseCase(
        repo=MysqlUserRepository(),
        gs_client=SocketGameServerClient(),
        tg_checker=tg_checker,
        queue=RedisQueue(),
        requests_queue=queue_name
    )

    # redis client
    try:
        app.state.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://api_father_redis:6379/0"))
        app.state.redis_client.ping()
    except Exception as e:
        app.state.redis_client = None
        print(f"[startup] Redis init failed: {e}")

    # attach router
    app.include_router(build_router(app.state.register_uc))
    yield


app.router.lifespan_context = lifespan


@app.get("/internal/health")
def health():
    ok = True
    details = {"redis": False}
    try:
        if getattr(app.state, "redis_client", None) is not None and app.state.redis_client.ping():
            details["redis"] = True
    except Exception:
        ok = False
    return {"status": "ok" if ok else "degraded", "details": details}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/info/internal/health")
def info_internal_health():
    ok = True
    details = {"redis": False}
    try:
        if getattr(app.state, "redis_client", None) is not None and app.state.redis_client.ping():
            details["redis"] = True
    except Exception:
        ok = False
    return {"status": "ok" if ok else "degraded", "details": details}


@app.get("/internal/constants")
def constants():
    dsn, db_name = get_dsn_and_db()
    sql = f"SELECT Name, Value, Description FROM `{db_name}`.constants ORDER BY Value ASC"
    try:
        conn = pymysql.connect(**dsn)
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass

    data = {row["Name"]: {"value": float(row["Value"]), "description": row["Description"]} for row in rows}
    return data


@app.post("/internal/queue/enqueue")
def enqueue(item: dict):
    if getattr(app.state, "redis_client", None) is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    try:
        qname = item.pop("queue", os.getenv("QUEUE_REQUESTS", "queue:requests"))
        app.state.redis_client.rpush(qname, json.dumps(item, ensure_ascii=False))
        return {"queued": True, "queue": qname}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/server/status")
def server_status():
    """
    Возвращает статус игрового сервера
    """
    return {
        "online": True,
        "players_online": 0,
        "max_players": 1000,
        "version": "1.0.0",
        "uptime_seconds": 0
    }
