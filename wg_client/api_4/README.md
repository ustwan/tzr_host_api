# API_4: Battle Logs System

Система для работы с логами боёв (.tzb файлы), извлечения метаданных и предоставления API для поиска и анализа боёв.

## Возможности

- **Парсинг XML файлов** (.tzb) с извлечением метаданных
- **Нормализованная схема БД** со справочниками для игроков, кланов, монстров, ресурсов
- **Потоковая загрузка** боёв с автоматическим наполнением справочников
- **13 витрин данных** для быстрого доступа к агрегированным данным
- **Аналитика** включая антибот, экономику, командную динамику
- **REST API** для поиска и анализа боёв
- **Автоматические расписания** обновления витрин

## Архитектура

```
API_4 (FastAPI)
├── Парсинг XML (.tzb файлы)
├── Извлечение метаданных
├── Нормализация данных (справочники)
├── Потоковая загрузка в БД
├── Витрины (data marts)
├── Аналитика и антибот
└── API эндпоинты
```

## Структура проекта

```
api_4/
├── app/
│   ├── main.py          # FastAPI приложение
│   ├── models.py        # Pydantic модели
│   ├── parser.py        # XML парсер
│   ├── database.py      # Работа с БД
│   ├── loader.py        # Загрузчик данных
│   ├── analytics.py     # Аналитические запросы
│   └── utils.py         # Утилиты (сжатие карт)
├── migrations/
│   ├── V3__battle_logs.sql
│   └── V4__reference_tables.sql
├── marts/
│   ├── daily_player_features.sql
│   ├── daily_clan_features.sql
│   ├── daily_player_sessions.sql
│   ├── daily_resource_inflow.sql
│   ├── resource_anomalies.sql
│   ├── daily_spec_stats.sql
│   └── bot_suspicion.sql
├── Dockerfile
├── requirements.txt
└── README.md
```

## Витрины данных

| Витрина | Назначение | Частота обновления |
|---------|------------|-------------------|
| `daily_player_features` | Фичи игроков за день (SR, KPT, активность) | Ежедневно |
| `daily_clan_features` | Агрегат по кланам | Ежедневно |
| `daily_player_sessions` | Сессии для антибота | Ежедневно |
| `daily_resource_inflow` | Экономика - приток ресурсов | Ежедневно |
| `resource_anomalies` | Аномалии в экономике (z-score) | Ежедневно |
| `daily_spec_stats` | Баланс PvE по монстрам | Ежедневно |
| `bot_suspicion` | Скоринг антибота | Ежедневно |

## API Эндпоинты

### Основные
- `GET /healthz` - Проверка здоровья
- `GET /api/battle/{battle_id}` - Информация о бое
- `GET /api/battle/list` - Список боёв с пагинацией
- `GET /api/battle/search` - Поиск боёв по критериям
- `GET /api/battle/{battle_id}/raw` - Сырые данные боя

### Синхронизация
- `POST /api/sync` - Синхронизация новых файлов
- `POST /api/sync/reprocess` - Повторная обработка файлов с ошибками

### Аналитика
- `GET /api/analytics/player/{login}` - Аналитика игрока
- `GET /api/analytics/players/top` - Топ игроков
- `GET /api/analytics/clan/{name}` - Аналитика клана
- `GET /api/analytics/resource/{name}` - Аналитика ресурса
- `GET /api/analytics/monster/{kind}` - Аналитика монстра
- `GET /api/analytics/anomalies` - Аномалии в ресурсах
- `GET /api/analytics/bot-suspicion/{login}` - Анализ подозрения на бота
- `GET /api/analytics/stats` - Общая статистика

### Администрирование
- `GET /api/admin/loading-stats` - Статистика загрузки
- `POST /api/admin/cleanup` - Очистка старых записей

## Переменные окружения

```bash
# Основные настройки
LOGS_BASE=/home/zero/logs/btl
DB_MODE=test

# PostgreSQL БД для API_4
DB_API4_TEST_NAME=api4_battles
DB_API4_TEST_USER=api4_user
DB_API4_TEST_PASSWORD=api4_pass
DB_API4_PROD_HOST=localhost
DB_API4_PROD_PORT=5432
DB_API4_PROD_NAME=api4_battles
DB_API4_PROD_USER=api4_user
DB_API4_PROD_PASSWORD=api4_pass

# Настройки загрузки
BATCH_SIZE=100
MAX_WORKERS=4
RETRY_ATTEMPTS=3
RETRY_DELAY=1.0
```

## Запуск

### Docker Compose
```bash
cd HOST_API_SERVICE
docker-compose -f compose.base.yml up api_4
```

### Локально
```bash
cd api_4
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8084
```

## Миграции БД

```bash
# Подключиться к PostgreSQL
docker exec -it HOST_API_SERVICE-api_4_db-1 psql -U api4_user -d api4_battles

# Применить миграции
\i migrations/V3__battle_logs.sql
\i migrations/V4__reference_tables.sql

# Создать витрины
\i marts/daily_player_features.sql
\i marts/daily_clan_features.sql
\i marts/daily_player_sessions.sql
\i marts/daily_resource_inflow.sql
\i marts/resource_anomalies.sql
\i marts/daily_spec_stats.sql
\i marts/bot_suspicion.sql
```

## Примеры использования

### Поиск боёв игрока
```bash
curl "http://localhost/api/battle/search?player=PlayerName&limit=10"
```

### Аналитика игрока
```bash
curl "http://localhost/api/analytics/player/PlayerName?days=30"
```

### Синхронизация новых файлов
```bash
curl -X POST "http://localhost/api/sync"
```

### Проверка аномалий в ресурсах
```bash
curl "http://localhost/api/analytics/anomalies?days=7"
```

## Мониторинг

- **Логи**: Docker logs api_4
- **Метрики**: `/api/admin/loading-stats`
- **Здоровье**: `/healthz`

## Производительность

- **Индексы БД** для быстрого поиска
- **Сжатие карт** для экономии места
- **Пагинация** для ограничения результатов
- **Асинхронность** FastAPI + asyncpg
- **Потоковая загрузка** для больших объёмов данных

## Безопасность

- **Валидация данных** через Pydantic
- **Ограничение доступа** через Traefik
- **Логирование** всех операций
- **Обработка ошибок** с детальными сообщениями
