from fastapi import FastAPI, HTTPException
import os
import pymysql
import redis
import json
from typing import Optional

app = FastAPI(title="API_FATHER")

redis_client: Optional[redis.Redis] = None
QUEUE_REQUESTS = os.getenv("QUEUE_REQUESTS", "queue:requests")
QUEUE_EVENTS = os.getenv("QUEUE_EVENTS", "queue:events")


def get_dsn_and_db():
    mode = os.getenv("DB_MODE", "test").lower()
    if mode == "prod":
        host = os.getenv("DB_PROD_HOST")
        port = int(os.getenv("DB_PROD_PORT", "3306"))
        user = os.getenv("DB_PROD_USER")
        password = os.getenv("DB_PROD_PASSWORD")
        name = os.getenv("DB_PROD_NAME", "tzserver")
    else:
        host = os.getenv("DB_TEST_HOST", "db")
        port = int(os.getenv("DB_TEST_PORT", "3306"))
        user = os.getenv("DB_TEST_USER", "tzuser")
        password = os.getenv("DB_TEST_PASSWORD", "tzpass")
        name = os.getenv("DB_TEST_NAME", "tzserver")
    dsn = dict(host=host, port=port, user=user, password=password, database=name, cursorclass=pymysql.cursors.DictCursor)
    return dsn, name


@app.on_event("startup")
def init_redis():
    global redis_client
    url = os.getenv("REDIS_URL", "redis://api_father_redis:6379/0")
    try:
        redis_client = redis.from_url(url)
        # ленивое создание «очередей»: просто убедимся, что ключи доступны (например, добавим пустую очистку)
        # Ничего не делаем, если очереди уже существуют
        redis_client.ping()
    except Exception as e:
        # не валим сервис, но фиксируем ошибку подключения
        redis_client = None
        print(f"[startup] Redis init failed: {e}")


@app.get("/internal/health")
def health():
    ok = True
    details = {"redis": False}
    try:
        if redis_client is not None and redis_client.ping():
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
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    try:
        qname = item.pop("queue", QUEUE_REQUESTS)
        redis_client.rpush(qname, json.dumps(item, ensure_ascii=False))
        return {"queued": True, "queue": qname}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
