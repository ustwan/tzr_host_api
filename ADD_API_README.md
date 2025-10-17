## Как добавить новое API (шаблон и пошаговая инструкция)

Ниже — простой чек‑лист и минимальные шаблоны файлов, чтобы быстро поднять новый сервис в стиле Чистой архитектуры.

### 1) Создаём каркас сервиса
- Каталог: `wg_client/api_<name>/app`
- Базовая структура слоёв:
```
wg_client/api_<name>/app/
  domain/
    entities.py
    mappers.py
  usecases/
    example_usecase.py
  ports/
    example_port.py
  infrastructure/
    repositories/
      example_repository.py
    container.py
  interfaces/
    http/
      routes.py
  main.py
  tests/
    test_smoke.py
```

Идея: 
- `domain` — модели и преобразования данных (без завязки на фреймворки и БД).
- `usecases` — прикладные сценарии (минимальная логика, максимум смысла).
- `ports` — интерфейсы зависимостей (репозитории, клиенты и т.п.).
- `infrastructure` — конкретные реализации портов и DI‑контейнер.
- `interfaces/http` — FastAPI‑роуты (входная граница), только «приняли запрос → вызвали use case → вернули ответ».
- `main.py` — тонкий вход: инициализация приложения и подключение роутов через контейнер.

### 2) Шаблоны файлов

1) Порт (интерфейс) — `ports/example_port.py`
```python
from typing import Protocol, Any

class ExamplePort(Protocol):
    async def get_something(self, *, key: str) -> Any: ...
```

2) Реализация порта — `infrastructure/repositories/example_repository.py`
```python
from typing import Any
from ports.example_port import ExamplePort

class ExampleRepository(ExamplePort):
    def __init__(self):
        pass

    async def get_something(self, *, key: str) -> Any:
        # сходить в БД/HTTP и вернуть данные
        return {"key": key, "value": 42}
```

3) Use case — `usecases/example_usecase.py`
```python
from typing import Any
from ports.example_port import ExamplePort

class ExampleUseCase:
    def __init__(self, repo: ExamplePort):
        self._repo = repo

    async def execute(self, key: str) -> Any:
        return await self._repo.get_something(key=key)
```

4) Роутер — `interfaces/http/routes.py`
```python
from fastapi import APIRouter, Query
from usecases.example_usecase import ExampleUseCase

def build_router(*, example_uc: ExampleUseCase) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @router.get("/api/example")
    async def example(key: str = Query("demo")):
        return await example_uc.execute(key)

    return router
```

5) Контейнер — `infrastructure/container.py`
```python
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI

from infrastructure.repositories.example_repository import ExampleRepository
from usecases.example_usecase import ExampleUseCase
from interfaces.http.routes import build_router

@asynccontextmanager
async def build_app() -> AsyncIterator[FastAPI]:
    app = FastAPI(title="API_<NAME>")

    # wiring зависимостей
    repo = ExampleRepository()
    example_uc = ExampleUseCase(repo)

    app.include_router(build_router(example_uc=example_uc))
    try:
        yield app
    finally:
        pass
```

6) Точка входа — `main.py`
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.container import build_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with build_app() as wired_app:
        # перенаправим роутер/состояние при необходимости
        yield

app = FastAPI(title="API_<NAME>", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

7) Смоук‑тест — `tests/test_smoke.py`
```python
from fastapi.testclient import TestClient
from app.main import app

def test_health():
    r = TestClient(app).get("/healthz")
    assert r.status_code in (200, 503)
```

### 3) Регистрация и запуск
- Локально: `pytest -q` — базовые проверки.
- Для docker‑композов — добавьте сервис в соответствующий `HOST_API_SERVICE_*.yml`, а маршрутизацию — в Traefik конфиг (`wg_client/traefik/dynamic/apis.yml`).

### 4) Правила и советы
- В роутерах — ноль бизнес‑логики. Только: принять → валидировать → дернуть use case → вернуть DTO.
- Use case зависим только от портов, а не от конкретных БД/клиентов.
- Все импорты внутри сервиса — абсолютные (упрощает тесты и устранение циклов).
- Сначала пишем use case и тест к нему, затем прикручиваем адаптер и роутер.
- Регрессию по слоям проверяет `tools/layer_lint.py`.

### 5) Быстрый чек‑лист
- [ ] Создана структура слоёв
- [ ] Написан порт(а) и адаптер(ы)
- [ ] Use case покрыт юнит‑тестом
- [ ] Роутер подключён через контейнер
- [ ] `/healthz` доступен
- [ ] Добавлено описание в README, обновлены compose/traefik при необходимости


