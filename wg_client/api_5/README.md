# API 5 — Shop Parser (Парсинг магазина)

**Версия:** 1.0  
**Статус:** 🚧 В разработке

---

## 📋 Назначение

API 5 — сервис парсинга и аналитики игровых магазинов в трёх городах:
- **Sova Moscow** (бот в Москве)
- **Sova Oasis** (бот в Оазисе)
- **Sova Neva** (бот в Неве)

### Задачи
1. Аутентификация ботов в игре и вход в магазины городов
2. Парсинг протокола магазина (`<SH c="..." s="..." p="..." />`)
3. Сбор снимков ассортимента (snapshots) каждый час
4. Отслеживание изменений цен, появления/исчезновения товаров
5. Аналитика рынка (цены, качество, редкие предметы)
6. REST API для запросов к данным магазина

---

## 🏗️ Архитектура

### Боты-парсеры (3 воркера)

По аналогии с XML Workers, используем **3 параллельных воркера**:

```yaml
shop_worker_moscow:
  bot_login: Sova
  bot_password: ${SOVA_MOSCOW_PASSWORD}
  shop_code: moscow
  shop_location: "Moscow"

shop_worker_oasis:
  bot_login: Sova
  bot_password: ${SOVA_OASIS_PASSWORD}
  shop_code: oasis
  shop_location: "Oasis"

shop_worker_neva:
  bot_login: Sova
  bot_password: ${SOVA_NEVA_PASSWORD}
  shop_code: neva
  shop_location: "Neva"
```

### Протокол работы

1. **Аутентификация:** Бот логинится в игру через socket
2. **Вход в магазин:** Бот перемещается в магазин своего города
3. **Парсинг категорий:** Запрос всех категорий (`k`, `p`, `v`, `h`, ...)
4. **Пагинация:** Перебор страниц `p=0,1,2,...` до повтора
5. **Раскрытие групп:** Если `count="N"` → рекурсивный запрос
6. **Сохранение:** Upsert в БД `api5_shop`
7. **Снимок:** Создание snapshot_id и привязка товаров
8. **Дифф:** Сравнение с предыдущим снимком

### Clean Architecture (как API 4)

```
api_5/
├── app/
│   ├── domain/              # Сущности
│   │   ├── entities.py      # Shop, Item, Snapshot
│   │   └── mappers.py       # XML → Domain
│   ├── usecases/            # Прикладные сценарии
│   │   ├── authenticate_bot.py
│   │   ├── parse_shop_category.py
│   │   ├── create_snapshot.py
│   │   └── calculate_diff.py
│   ├── ports/               # Интерфейсы
│   │   ├── shop_repository.py
│   │   ├── game_client.py
│   │   └── bot_session_manager.py
│   ├── infrastructure/      # Реализации
│   │   ├── db/
│   │   │   ├── repositories.py
│   │   │   └── models.py
│   │   ├── game_socket_client.py
│   │   ├── bot_session.py
│   │   └── di_container.py
│   ├── interfaces/http/     # FastAPI роуты
│   ├── parsers/             # XML парсеры
│   │   ├── shop_parser.py
│   │   └── normalizer.py
│   └── main.py
├── shop_workers/            # 3 воркера (moscow/oasis/neva)
│   ├── worker_base.py
│   ├── moscow_worker.py
│   ├── oasis_worker.py
│   └── neva_worker.py
├── migrations/              # Flyway миграции
├── marts/                   # SQL витрины
├── Dockerfile
└── requirements.txt
```

---

## 🔐 Аутентификация ботов

### Протокол логина (упрощённый)

```xml
<!-- 1. Запрос логина -->
<LOGIN name="Sova" password="..." />

<!-- 2. Ответ сервера -->
<LOGIN_OK session_id="abc123" />

<!-- 3. Все последующие запросы с session_id -->
<SH c="k" s="" p="0" session_id="abc123" />
```

### BotSession (хранение сессий)

```python
class BotSession:
    bot_login: str
    shop_code: str        # moscow/oasis/neva
    session_id: str
    authenticated: bool
    last_activity: datetime
    location: str         # текущая локация бота
```

### Управление сессиями

- **Keep-alive:** Ping каждые 30 секунд
- **Переподключение:** Если сессия истекла → реавторизация
- **Isolation:** Каждый воркер работает в своей сессии

---

## 📊 База данных (PostgreSQL `api5_shop`)

### Основные таблицы

```sql
-- 1. Магазины
CREATE TABLE shops (
  id   SERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,     -- moscow, oasis, neva
  name TEXT NOT NULL,             -- Moscow, Oasis, Neva
  bot_login TEXT                  -- Sova
);

-- 2. Шаблоны товаров
CREATE TABLE item_templates (
  id       SERIAL PRIMARY KEY,
  type     TEXT NOT NULL,
  name     TEXT NOT NULL,
  category TEXT NOT NULL,
  UNIQUE(type, name, category)
);

-- 3. Товары (экземпляры)
CREATE TABLE shop_items (
  id BIGINT PRIMARY KEY,
  template_id INT REFERENCES item_templates(id),
  shop_id     INT REFERENCES shops(id),
  price       NUMERIC,
  current_quality INT,
  max_quality     INT,
  damage      JSONB,
  protect     JSONB,
  requirements JSONB,
  attack_modes JSONB,
  infinty     BOOLEAN,
  owner       TEXT,
  added_at    TIMESTAMP,
  updated_at  TIMESTAMP
);

-- 4. Снимки
CREATE TABLE snapshots (
  id         SERIAL PRIMARY KEY,
  shop_id    INT REFERENCES shops(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  items_count INT,
  worker_name TEXT
);

-- 5. Привязка товаров к снимку
CREATE TABLE snapshot_items (
  snapshot_id INT REFERENCES snapshots(id),
  item_id     BIGINT REFERENCES shop_items(id),
  PRIMARY KEY(snapshot_id, item_id)
);

-- 6. История изменений
CREATE TABLE item_changes (
  id          SERIAL PRIMARY KEY,
  item_id     BIGINT REFERENCES shop_items(id),
  snapshot_id INT REFERENCES snapshots(id),
  change_type TEXT,
  old_price   NUMERIC,
  new_price   NUMERIC,
  old_quality INT,
  new_quality INT,
  detected_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 7. Сессии ботов
CREATE TABLE bot_sessions (
  id            SERIAL PRIMARY KEY,
  bot_login     TEXT NOT NULL,
  shop_code     TEXT NOT NULL,
  session_id    TEXT,
  authenticated BOOLEAN DEFAULT FALSE,
  last_activity TIMESTAMP,
  location      TEXT,
  created_at    TIMESTAMP DEFAULT NOW()
);
```

---

## 🚀 Запуск

### Локальная разработка

```bash
# 1. Создать БД
docker-compose -f HOST_API_SERVICE_SHOP_API.yml up -d api_5_db

# 2. Применить миграции
docker-compose -f HOST_API_SERVICE_SHOP_API.yml up api_5_migrator

# 3. Запустить API
docker-compose -f HOST_API_SERVICE_SHOP_API.yml up api_5
```

### Через ctl.sh

```bash
# Запуск всех компонентов
bash tools/ctl.sh api5-up-db

# Только API
bash tools/ctl.sh api5-up

# Логи
bash tools/ctl.sh api5-logs

# Миграции
bash tools/ctl.sh api5-migrate
```

---

## 📡 Основные эндпоинты

### Health & Service (3)
- `GET /healthz` — проверка работоспособности
- `GET /shop/health` — проверка модуля магазина
- `GET /db/health` — проверка БД

### Снимки (5)
- `GET /snapshots/list` — список снимков
- `GET /snapshots/{id}` — детали снимка
- `POST /snapshots/create` — создать снимок (админ)
- `GET /snapshots/{id}/diff` — сравнение снимков
- `GET /snapshots/latest` — последний снимок

### Товары (8)
- `GET /items/list` — список товаров
- `GET /items/{id}` — детали товара
- `GET /items/search` — поиск
- `GET /items/{id}/history` — история изменений

### Аналитика (10)
- `GET /analytics/prices/distribution`
- `GET /analytics/prices/anomalies`
- `GET /analytics/market/velocity`
- `GET /analytics/weapons/damage`
- `GET /analytics/armor/protection`

### Администрирование (5)
- `POST /admin/snapshot/trigger` — запустить снимок
- `POST /admin/sync/{shop_code}` — синхронизация магазина
- `GET /admin/bots/status` — статус ботов
- `POST /admin/bots/reconnect` — переподключить бота

---

## 🔧 Конфигурация

### Переменные окружения

**⚡ ВАЖНО: Shop Workers используют ТЕ ЖЕ ключи что и XML Workers!**

```bash
# БД
DB_API5_TEST_HOST=api_5_db
DB_API5_TEST_PORT=5432
DB_API5_TEST_NAME=api5_shop
DB_API5_TEST_USER=api5_user
DB_API5_TEST_PASSWORD=api5_pass

# Игровой сервер (как в XML Workers)
GAME_SERVER_HOST=185.92.72.18
GAME_SERVER_PORT=5190

# Боты (те же что в XML Workers!)
SOVA_MOSCOW_LOGIN=Sova
SOVA_MOSCOW_KEY=<из XML Workers>
SOVA_OASIS_LOGIN=Sova
SOVA_OASIS_KEY=<из XML Workers>
SOVA_NEVA_LOGIN=Sova
SOVA_NEVA_KEY=<из XML Workers>

# Планировщик
SNAPSHOT_INTERVAL=3600  # 1 час
KEEPALIVE_INTERVAL=30   # 30 секунд
```

---

## 📚 Связанные документы

- `example/main_shop.md` — полное описание протокола магазина
- `API5_SHOP_FEASIBILITY_ANALYSIS.md` — анализ возможности реализации
- `BATTLE_COMPLETE_GUIDE.md` — пример API 4 (образец архитектуры)
- `XML_WORKERS_ARCHITECTURE.md` — паттерн параллельных воркеров

---

## ⚠️ Важные нюансы

### 1. Боты должны находиться В магазинах
- ❌ Нельзя парсить магазин удалённо
- ✅ Бот должен быть залогинен и находиться в магазине города
- ✅ Каждый бот привязан к своему магазину (Moscow/Oasis/Neva)

### 2. Управление сессиями
- ✅ Хранение session_id для каждого бота
- ✅ Keep-alive пинги каждые 30 секунд
- ✅ Автоматическое переподключение при обрыве

### 3. Параллелизм
- ✅ 3 воркера работают независимо
- ✅ Каждый воркер парсит свой магазин
- ✅ Снимки делаются одновременно для всех магазинов

---

**Статус разработки:** 🚧 См. TODO список (56 задач)

**Автор:** AI Assistant  
**Версия:** 1.0


