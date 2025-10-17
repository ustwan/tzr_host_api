# 🏗️ Архитектура получения статуса сервера

> Правильная архитектура: кеширование + периодическое обновление

---

## ❌ Проблема текущей реализации

**Сейчас (плохо):**

```
Сайт (каждый запрос) 
  ↓ fetch('/api/server/status')
API_1 
  ↓ SELECT * FROM constants (каждый запрос!)
MySQL
  ↓ читает данные
Ответ сайту
```

**Проблемы:**
- 🔴 При 1000 посетителях = 1000 запросов к БД
- 🔴 Высокая нагрузка на MySQL
- 🔴 Медленно (~100-200ms на запрос)
- 🔴 Если БД упадет = сайт не работает

---

## ✅ Правильная архитектура

**Должно быть (хорошо):**

```
┌─────────────────────────────────────────────────────────────┐
│ Background Task (раз в 10 минут, автоматически)            │
│                                                             │
│ API Worker → Game Server → получает статус                 │
│           → сохраняет в Redis/БД                            │
│           → timestamp последнего обновления                 │
└─────────────────────────────────────────────────────────────┘
                             ↓
                    ┌────────────────────┐
                    │ Redis Cache        │
                    │ key: server:status │
                    │ TTL: 10 минут      │
                    │ value: {           │
                    │   online: true,    │
                    │   players: 150,    │
                    │   rates: {...}     │
                    │ }                  │
                    └────────────────────┘
                             ↑
                             │ Быстрое чтение (~5ms)
                             │
┌─────────────────────────────────────────────────────────────┐
│ Сайт (каждый пользователь)                                 │
│   ↓ fetch('/api/server/status')                            │
│ API_1                                                       │
│   ↓ GET from Redis (НЕ обращается к Game Server!)         │
│ Ответ из кеша (очень быстро)                               │
└─────────────────────────────────────────────────────────────┘
```

**Преимущества:**
- ✅ **Быстро:** ~5-10ms (из Redis)
- ✅ **Разгружает Game Server:** только 1 запрос в 10 минут
- ✅ **Масштабируемость:** 10000 пользователей = 0 нагрузки
- ✅ **Надежность:** если Game Server упал, отдаем последние данные

---

## 🔧 Реализация

### Вариант 1: Background Task в FastAPI

**`wg_client/api_1/app/main.py`:**

```python
from fastapi import FastAPI, BackgroundTasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import redis
import json
import pymysql
import logging

logger = logging.getLogger(__name__)

# Redis клиент
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

# Планировщик задач
scheduler = AsyncIOScheduler()

async def update_server_status():
    """
    Обновляет статус сервера в Redis
    Вызывается автоматически каждые 10 минут
    """
    try:
        logger.info("🔄 Обновление статуса сервера...")
        
        # 1. Получаем данные из БД (константы)
        dsn = get_db_config()
        conn = pymysql.connect(**dsn)
        
        with conn.cursor() as cur:
            cur.execute("SELECT Name, Value, Description FROM constants")
            rows = cur.fetchall()
        
        conn.close()
        
        # 2. Формируем JSON
        status_data = {
            "server_status": get_value(rows, "ServerStatus", 1.0),
            "rates": {
                "exp": get_value(rows, "RateExp", 1.0),
                "pvp": get_value(rows, "RatePvp", 1.0),
                "pve": get_value(rows, "RatePve", 1.0),
                "color_mob": get_value(rows, "RateColorMob", 1.0),
                "skill": get_value(rows, "RateSkill", 1.0)
            },
            "client_status": get_value(rows, "CLIENT_STATUS", 256.0),
            "updated_at": time.time(),
            "_meta": {row["Name"]: row["Description"] for row in rows}
        }
        
        # 3. Сохраняем в Redis (TTL 15 минут на случай сбоя)
        redis_client.setex(
            "server:status",
            900,  # 15 минут TTL
            json.dumps(status_data, ensure_ascii=False)
        )
        
        logger.info(f"✅ Статус обновлен: online={status_data['server_status']}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статуса: {e}")


@app.on_event("startup")
async def startup_event():
    """
    При старте приложения:
    1. Сразу обновляем статус
    2. Запускаем планировщик (каждые 10 минут)
    """
    # Первое обновление сразу
    await update_server_status()
    
    # Планировщик: каждые 10 минут
    scheduler.add_job(
        update_server_status,
        'interval',
        minutes=10,
        id='update_server_status'
    )
    scheduler.start()
    
    logger.info("✅ Background task запущен (обновление каждые 10 минут)")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Останавливаем планировщик при остановке
    """
    scheduler.shutdown()


@app.get("/server/status")
async def get_server_status():
    """
    Возвращает статус сервера из КЕША (Redis)
    
    Быстро (~5ms), без нагрузки на Game Server
    """
    try:
        # Читаем из Redis
        cached = redis_client.get("server:status")
        
        if cached:
            data = json.loads(cached)
            
            # Добавляем info о кеше
            data["_cache"] = {
                "cached": True,
                "age_seconds": int(time.time() - data.get("updated_at", 0))
            }
            
            return data
        
        # Если кеша нет - обновляем сейчас
        logger.warning("⚠️ Кеш пуст, обновляю сейчас...")
        await update_server_status()
        
        cached = redis_client.get("server:status")
        if cached:
            return json.loads(cached)
        
        # Fallback
        return {
            "server_status": 1.0,
            "rates": {"exp": 1.0, "pvp": 1.0, "pve": 1.0},
            "client_status": 256.0,
            "_cache": {"cached": False, "error": "Cache miss"}
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_value(rows, name, default):
    """Получить значение из списка констант"""
    for row in rows:
        if row["Name"] == name:
            return float(row["Value"])
    return default
```

---

### Вариант 2: Отдельный Worker (рекомендуется для production)

**`wg_client/status_worker/worker.py`:**

```python
#!/usr/bin/env python3
"""
Background worker для обновления статуса сервера
Запускается как отдельный контейнер
"""

import time
import redis
import pymysql
import json
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

# MySQL
db_config = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "tzuser"),
    "password": os.getenv("DB_PASSWORD", "tzpass"),
    "database": os.getenv("DB_NAME", "tzserver"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def fetch_server_status():
    """Получить статус из БД"""
    try:
        conn = pymysql.connect(**db_config)
        
        with conn.cursor() as cur:
            cur.execute("SELECT Name, Value, Description FROM constants")
            rows = cur.fetchall()
        
        conn.close()
        
        # Формируем данные
        status_data = {
            "server_status": get_value(rows, "ServerStatus", 1.0),
            "rates": {
                "exp": get_value(rows, "RateExp", 1.0),
                "pvp": get_value(rows, "RatePvp", 1.0),
                "pve": get_value(rows, "RatePve", 1.0),
                "color_mob": get_value(rows, "RateColorMob", 1.0),
                "skill": get_value(rows, "RateSkill", 1.0)
            },
            "client_status": get_value(rows, "CLIENT_STATUS", 256.0),
            "updated_at": datetime.now().isoformat(),
            "_meta": {row["Name"]: row["Description"] for row in rows}
        }
        
        return status_data
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса: {e}")
        return None


def get_value(rows, name, default):
    """Получить значение константы"""
    for row in rows:
        if row["Name"] == name:
            return float(row["Value"])
    return default


def update_cache():
    """Обновить кеш в Redis"""
    try:
        logger.info(f"🔄 [{datetime.now()}] Обновление статуса...")
        
        status = fetch_server_status()
        
        if status:
            # Сохраняем в Redis (TTL 15 минут)
            redis_client.setex(
                "server:status",
                900,  # 15 минут (на случай сбоя worker)
                json.dumps(status, ensure_ascii=False)
            )
            
            logger.info(f"✅ Статус обновлен: online={status['server_status']}, " +
                       f"rates_exp={status['rates']['exp']}")
            return True
        else:
            logger.error("❌ Не удалось получить статус")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка обновления кеша: {e}")
        return False


def main():
    """Главный цикл worker"""
    logger.info("🚀 Status Worker запущен")
    logger.info(f"📋 Интервал обновления: 10 минут")
    logger.info(f"📋 Redis: {os.getenv('REDIS_URL', 'redis://localhost:6379/0')}")
    
    # Первое обновление сразу
    update_cache()
    
    # Бесконечный цикл с обновлением каждые 10 минут
    while True:
        time.sleep(600)  # 10 минут = 600 секунд
        update_cache()


if __name__ == "__main__":
    main()
```

**`wg_client/status_worker/Dockerfile`:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker.py .

CMD ["python", "worker.py"]
```

**`wg_client/status_worker/requirements.txt`:**

```
redis==5.0.1
pymysql==1.1.0
```

**`wg_client/docker-compose.status-worker.yml`:**

```yaml
version: '3.8'

services:
  status_worker:
    build: ./status_worker
    container_name: status_worker
    restart: unless-stopped
    
    environment:
      - REDIS_URL=redis://api_father_redis:6379/0
      - DB_HOST=db
      - DB_PORT=3306
      - DB_USER=tzuser
      - DB_PASSWORD=tzpass
      - DB_NAME=tzserver
    
    networks:
      - host-api-network
    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  host-api-network:
    external: true
```

---

## 🔄 Обновленный API_1 (читает из кеша)

**`wg_client/api_1/app/main.py`:**

```python
import redis
import json
from fastapi import HTTPException

# Redis клиент
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

@app.get("/server/status")
async def get_server_status():
    """
    Возвращает статус сервера из КЕША
    
    Данные обновляются background worker'ом каждые 10 минут
    Очень быстро (~5ms), без нагрузки на БД/Game Server
    """
    try:
        # Читаем из Redis
        cached = redis_client.get("server:status")
        
        if cached:
            data = json.loads(cached)
            return data
        
        # Если кеша нет - fallback на БД (редко)
        logger.warning("⚠️ Кеш пуст, читаю из БД напрямую...")
        return await get_status_from_db()
        
    except redis.RedisError as e:
        logger.error(f"Redis ошибка: {e}, читаю из БД...")
        return await get_status_from_db()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_status_from_db():
    """Fallback: читаем напрямую из БД"""
    conn = pymysql.connect(**db_config)
    
    with conn.cursor() as cur:
        cur.execute("SELECT Name, Value, Description FROM constants")
        rows = cur.fetchall()
    
    conn.close()
    
    return {
        "server_status": get_value(rows, "ServerStatus", 1.0),
        "rates": {...},
        "client_status": get_value(rows, "CLIENT_STATUS", 256.0),
        "_cache": {"cached": False, "source": "database"}
    }
```

---

## 📊 Сравнение производительности

| Метод | Время ответа | Нагрузка на БД | Нагрузка на Game Server |
|-------|--------------|----------------|-------------------------|
| **Текущий** (напрямую к БД) | 100-200ms | 1000 req/мин | - |
| **С кешем** (Redis) | 5-10ms | 0.1 req/мин | - |
| **С worker** (фон обновление) | 5-10ms | 0.1 req/мин | 0.1 req/мин |

**Выигрыш:**
- ⚡ **Скорость:** в 20 раз быстрее
- 💾 **Нагрузка на БД:** в 10000 раз меньше
- 🎮 **Game Server:** не перегружается

---

## 🚀 Запуск

### Локальная разработка:

```bash
# Запустить все сервисы + worker
cd wg_client
docker-compose -f HOST_API_SERVICE_DB_API.yml up -d
docker-compose -f docker-compose.status-worker.yml up -d

# Проверить логи worker
docker logs status_worker -f

# Должно быть:
# 🚀 Status Worker запущен
# ✅ Статус обновлен: online=1.0, rates_exp=1.0
```

### Production:

```bash
# На WG_CLIENT (внутри VPN)
docker-compose -f docker-compose.status-worker.yml up -d
```

---

## 🧪 Тестирование

### 1. Проверка что worker работает

```bash
# Проверить логи
docker logs status_worker

# Должно быть (каждые 10 минут):
# 🔄 [2025-10-14 12:00:00] Обновление статуса...
# ✅ Статус обновлен: online=1.0
```

### 2. Проверка Redis кеша

```bash
# Подключиться к Redis
docker exec -it api_father_redis redis-cli

# Проверить ключ
GET server:status

# Должен вернуть JSON
# {"server_status":1.0,"rates":{...},"updated_at":"2025-10-14T12:00:00"}

# Проверить TTL
TTL server:status

# Должно быть ~900 секунд (15 минут)
```

### 3. Проверка API

```bash
# Запрос к API
curl http://localhost:8090/api/server/status

# Должен вернуть данные ИЗ КЕША
# Время ответа: ~5-10ms (очень быстро!)
```

### 4. Stress test

```bash
# 100 запросов подряд
for i in {1..100}; do
  curl -s http://localhost:8090/api/server/status > /dev/null &
done

wait

# Проверить логи БД - должно быть 0 запросов!
# Все запросы обслужены из Redis кеша
```

---

## 📈 Мониторинг

### 1. Проверка freshness (свежести) данных

```python
@app.get("/server/status/debug")
async def debug_status():
    """Отладочная информация о кеше"""
    cached = redis_client.get("server:status")
    
    if cached:
        data = json.loads(cached)
        updated_at = data.get("updated_at")
        age = time.time() - updated_at if updated_at else None
        
        return {
            "cached": True,
            "updated_at": updated_at,
            "age_seconds": age,
            "ttl": redis_client.ttl("server:status"),
            "is_fresh": age < 600 if age else False  # < 10 минут
        }
    
    return {"cached": False}
```

### 2. Health check worker'а

```python
# В worker.py
@app.get("/health")
def health():
    """Health check для worker"""
    try:
        # Проверяем что кеш свежий
        cached = redis_client.get("server:status")
        if cached:
            data = json.loads(cached)
            age = time.time() - data.get("updated_at", 0)
            
            if age < 900:  # < 15 минут
                return {"status": "ok", "age_seconds": age}
        
        return {"status": "stale", "message": "Cache too old"}
    except:
        return {"status": "error"}
```

---

## ⚙️ Настройки

### Переменные окружения:

```bash
# Интервал обновления (секунды)
STATUS_UPDATE_INTERVAL=600  # 10 минут

# TTL кеша (секунды)
STATUS_CACHE_TTL=900  # 15 минут

# Redis
REDIS_URL=redis://api_father_redis:6379/0
```

### Динамический интервал:

```python
# Можно менять интервал на лету через Redis
interval = int(redis_client.get("config:status_interval") or 600)
scheduler.add_job(update_server_status, 'interval', seconds=interval)
```

---

## 🔧 Альтернатива: Cron в существующем контейнере

Если не хотите отдельный worker, используйте **APScheduler** прямо в API_1:

```python
# В api_1/app/main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    # Запуск фоновой задачи
    scheduler.add_job(update_server_status, 'interval', minutes=10)
    scheduler.start()
```

**Плюсы:** Просто, нет отдельного контейнера  
**Минусы:** API_1 перезапустился = статус не обновляется

---

## ✅ Итоговая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│ Production Flow                                             │
└─────────────────────────────────────────────────────────────┘

Сайт → Nginx (pub) → VPN → Nginx Proxy → API_1
                                            ↓
                                    Redis (get "server:status")
                                            ↑
                                      Status Worker
                                      (каждые 10 мин)
                                            ↓
                                      MySQL / Game Server
```

**Пользователи получают:**
- ⚡ Быстрый ответ (~5ms)
- 📊 Актуальные данные (обновляются каждые 10 минут)
- 🛡️ Надежность (даже если Game Server упал)

**Серверы получают:**
- 💚 Минимальная нагрузка
- 🔄 Предсказуемый трафик
- 📈 Масштабируемость

---

## 🎯 Рекомендация

**Для production используйте Worker!**

Это best practice для:
- Высоконагруженных систем
- Кеширования дорогих операций
- Отделения фоновых задач от API

---

**Следующий шаг:** Хотите чтобы я реализовал Status Worker?



