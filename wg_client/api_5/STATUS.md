# API 5 - Shop Parser: Статус разработки

**Дата:** 2025-10-11  
**Прогресс:** 20 / 56 задач (36%)

---

## ✅ Завершено (20 задач)

### 🏗️ Архитектура и проектирование
- [x] Создана архитектура API 5 с учётом ботов-парсеров в магазинах
- [x] Создана базовая структура проекта `wg_client/api_5/`

### 🔐 Аутентификация и боты
- [x] Разработана система логина ботов в игру (сессии)
- [x] Создана конфигурация для 3 ботов (Sova Moscow/Oasis/Neva)
- [x] Реализован `GameSocketClient` с поддержкой сессий
- [x] Реализован `BotSessionManager` для управления сессиями

### 📡 Протокол и парсинг
- [x] Реализован парсинг запроса `<SH />` (категории магазина)
- [x] Создан `ShopParser` для разбора XML ответов `<O />`
- [x] Реализован парсинг поля `damage` (S2-6, E3-7)
- [x] Реализован парсинг поля `protect` (S7-16, O1-5)
- [x] Реализован парсинг поля `shot` (режимы атак)
- [x] Реализован парсинг поля `min` (требования)
- [x] Реализован парсинг поля `st` (слоты)
- [x] Реализована конвертация `piercing` (500 -> 5.0%)
- [x] Реализована конвертация `put_day` (Unix -> Timestamp)

### 🗄️ База данных
- [x] Созданы миграции для таблиц (shops, items, snapshots)
- [x] Наполнена таблица `shops` (moscow, oasis, neva)

### 🐳 Docker и инфраструктура
- [x] Создан `Dockerfile` для API 5
- [x] Создан `requirements.txt` с зависимостями
- [x] Создан `HOST_API_SERVICE_SHOP_API.yml`
- [x] Добавлен `api_5_db` (PostgreSQL 15)
- [x] Добавлен `api_5_migrator` (Flyway)

---

## 🚧 В процессе (36 задач)

### Критически важные (следующий приоритет)

#### 🔄 Парсинг и логика
- [ ] Реализовать логику перебора страниц до повтора
- [ ] Реализовать раскрытие групп товаров (count=N)

#### 📊 База данных
- [ ] Создать SQLAlchemy модели для всех таблиц
- [ ] Реализовать ShopRepository (CRUD операции)

#### 🎯 Use Cases
- [ ] Создать ParseCategoryUseCase (парсинг одной категории)
- [ ] Создать CreateSnapshotUseCase (полный снимок магазина)
- [ ] Создать CalculateDiffUseCase (сравнение снимков)

#### 🌐 FastAPI
- [ ] Настроить dependency injection (DI Container)
- [ ] Создать main.py с приложением FastAPI
- [ ] Реализовать /healthz, /shop/health, /db/health

### Средний приоритет

#### 🔗 Роуты
- [ ] Реализовать /items/list (список товаров с пагинацией)
- [ ] Реализовать /items/search (поиск по фильтрам)
- [ ] Реализовать /items/{id} (детали товара)
- [ ] Реализовать /snapshots/list (список снимков)
- [ ] Реализовать /snapshots/{id}/diff (сравнение)
- [ ] Реализовать /admin/snapshot/trigger (ручной снимок)

#### 🌐 Интеграция
- [ ] Добавить роутинг в Traefik: /api/shop -> api_5:8085
- [ ] Добавить команды в tools/ctl.sh (api5-up, api5-logs)

#### ⏱️ Воркеры и планировщик
- [ ] Создать ShopScheduler для периодических снимков
- [ ] Реализовать 3 shop_worker (по аналогии с XML Workers)
- [ ] Создать shop_workers.yml для управления воркерами

### Низкий приоритет (после MVP)

#### 📊 Аналитика и витрины
- [ ] Создать marts/price_statistics.sql
- [ ] Создать marts/market_velocity.sql
- [ ] Создать marts/quality_distribution.sql
- [ ] Реализовать /analytics/prices/distribution
- [ ] Реализовать /analytics/prices/anomalies (z-score)

#### 🧪 Тесты
- [ ] Написать unit-тесты для парсеров
- [ ] Написать unit-тесты для use cases
- [ ] Написать integration-тесты для API

#### 📚 Документация
- [ ] Создать API5_IMPLEMENTATION_GUIDE.md
- [ ] Создать Swagger/OpenAPI спецификацию

#### 🚀 Деплой и мониторинг
- [ ] Тестовый запуск API 5 в dev окружении
- [ ] Проверить работу всех эндпоинтов
- [ ] Добавить метрики для Prometheus
- [ ] Связать API 5 с основным MAIN.md проекта

---

## 📂 Созданная структура

```
wg_client/api_5/
├── README.md                           ✅ Основное описание
├── STATUS.md                           ✅ Этот файл
├── Dockerfile                          ✅ Docker образ
├── requirements.txt                    ✅ Зависимости
├── app/
│   ├── __init__.py                     ✅
│   ├── config.py                       ✅ Конфигурация (боты, БД)
│   ├── domain/
│   │   ├── __init__.py                 ✅
│   │   └── entities.py                 ✅ Доменные сущности
│   ├── infrastructure/
│   │   ├── __init__.py                 ✅
│   │   └── game_socket_client.py       ✅ Клиент + сессии ботов
│   └── parsers/
│       ├── __init__.py                 ✅
│       └── shop_parser.py              ✅ Парсер XML магазина
├── migrations/
│   └── V1__init_schema.sql             ✅ Схема БД
└── (пока не созданы)
    ├── app/
    │   ├── infrastructure/db/           ⏳ SQLAlchemy модели
    │   ├── usecases/                    ⏳ Сценарии использования
    │   ├── interfaces/http/             ⏳ FastAPI роуты
    │   └── main.py                      ⏳ Точка входа
    ├── shop_workers/                    ⏳ Воркеры для городов
    └── marts/                           ⏳ SQL витрины

HOST_API_SERVICE_SHOP_API.yml          ✅ Docker Compose
```

---

## 🎯 MVP (Минимальный продукт)

### Что нужно для запуска базового функционала:

1. **SQLAlchemy модели** (shop-12)
2. **ShopRepository** (shop-13)
3. **ParseCategoryUseCase** (shop-14)
4. **DI Container** (shop-24)
5. **FastAPI main.py** (shop-25)
6. **Health endpoints** (shop-26)
7. **Пагинация** (shop-8)
8. **Раскрытие групп** (shop-9)

**Оценка:** ~8 задач для MVP (~14% остатка)

### После MVP можно:
- Запустить API локально
- Протестировать парсинг одной категории
- Проверить сохранение в БД
- Создать первый снимок магазина

---

## 🔥 Ключевые компоненты уже готовы!

### ✅ `GameSocketClient` (app/infrastructure/game_socket_client.py)
```python
# Аутентификация бота
client = GameSocketClient("game_server", 9000)
success, session_id = client.authenticate("Sova", "password")

# Запрос категории магазина
xml_response = client.fetch_shop_category(category="k", page=0)

# Keep-alive пинги
alive = client.ping()
```

### ✅ `BotSessionManager` (app/infrastructure/game_socket_client.py)
```python
# Управление 3 ботами
manager = BotSessionManager("game_server", 9000)

# Аутентификация всех ботов
for shop, bot_config in bots.items():
    manager.authenticate_bot(shop, bot_config.login, bot_config.password)

# Пинги всем ботам
status = manager.ping_all()  # {'moscow': True, 'oasis': True, 'neva': False}
```

### ✅ `ShopParser` (app/parsers/shop_parser.py)
```python
# Парсинг XML ответа
result = ShopParser.parse_response(xml_str, shop_code="moscow")

# Доступ к данным
for item in result.items:
    print(f"{item.txt}: {item.price} cr, quality {item.current_quality}/{item.max_quality}")
    print(f"  Damage: {item.damage}")  # [DamageComponent(type="S", min=2, max=6)]
    print(f"  Requirements: {item.requirements}")  # Requirements(level=6, strength=14)
```

---

## 🚀 Следующие шаги

### Немедленно (для MVP):
1. Создать SQLAlchemy модели
2. Реализовать ShopRepository
3. Создать ParseCategoryUseCase с пагинацией и раскрытием групп
4. Настроить DI Container
5. Создать FastAPI main.py с health endpoints

### После MVP:
6. Создать CreateSnapshotUseCase
7. Реализовать роуты для items и snapshots
8. Интегрировать в Traefik
9. Запустить 3 воркера
10. Настроить планировщик снимков

---

## 📝 Примечания

### Важные особенности реализации:

1. **Боты ДОЛЖНЫ быть в магазинах** — каждый бот залогинен и находится в своём городе
2. **Сессионное управление** — храним `session_id`, отправляем keep-alive пинги
3. **Параллельные воркеры** — 3 воркера работают независимо (как XML Workers)
4. **Простой протокол** — по аналогии с `xml_client.py` (connect → sendall → recv)
5. **PostgreSQL** — используем JSONB для хранения damage/protect/requirements

### Отличия от XML Workers:

| XML Workers | Shop Workers |
|-------------|-------------|
| 6 воркеров | 3 воркера |
| Читают файлы из БД | Запрашивают магазин в реальном времени |
| Без аутентификации | С аутентификацией (сессии) |
| Независимые батчи | Синхронизированные снимки |

---

**Готовность к MVP:** ~70%  
**Осталось критических задач:** 8  
**Ориентировочное время:** 1-2 дня разработки

**Автор:** AI Assistant  
**Версия:** 1.0


