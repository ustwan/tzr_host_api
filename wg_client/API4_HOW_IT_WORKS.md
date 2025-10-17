# 🔍 API 4 - Как это работает

## 📋 КРАТКОЕ ОПИСАНИЕ

**API 4** - система аналитики логов боев

- **Что делает:** Парсит .tzb файлы (XML логи боев), извлекает метаданные, сохраняет в PostgreSQL, предоставляет аналитику
- **БД:** PostgreSQL api4_battles (СВОЯ БД на HOST_API, НЕ MySQL tzserver!)
- **Файлы:** Через api_mother → btl_syncer → btl_rsyncd (HOST_SERVER)

---

## 🏗️ АРХИТЕКТУРА API 4

### Полная цепочка работы:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. HOST_SERVER (/home/zero/logs/btl)                        │
│    • Игровой сервер создает логи боев (.tzb файлы)         │
│    • Шардирование: index/50000 = папка                      │
│    • Формат: 3674169.tzb (XML)                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ rsync (read-only)
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. btl_rsyncd (HOST_SERVER :873)                            │
│    • rsync daemon                                           │
│    • Экспорт логов в RO режиме                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ rsync pull
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. btl_syncer (HOST_API)                                    │
│    • Синхронизация логов: HOST_SERVER → HOST_API           │
│    • Зеркало: ./xml/mirror (локал) или /srv/btl_mirror     │
│    • Интервал: каждые 60 сек                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. btl_compressor (HOST_API)                                │
│    • Сжатие: .tzb → .tzb.gz                                 │
│    • Шардирование: index/50000 = папка                      │
│    • Хранилище: ./xml/gz (локал) или /srv/btl_store/gz     │
│    • Интервал: каждые 30 сек                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. API 4 (FastAPI :8084)                                    │
│    ┌───────────────────────────────────────────────────┐   │
│    │ Синхронизация и парсинг                           │   │
│    ├───────────────────────────────────────────────────┤   │
│    │ POST /api/sync                                    │   │
│    │   └─ Сканирует ./xml/mirror или ./xml/gz          │   │
│    │   └─ Парсит .tzb файлы (XML)                      │   │
│    │   └─ Извлекает метаданные:                        │   │
│    │      • battle_id, date, winner                     │   │
│    │      • participants (игроки, кланы)                │   │
│    │      • monsters (виды, количество)                 │   │
│    │      • resources (добыча)                          │   │
│    │   └─ Сохраняет в PostgreSQL                       │   │
│    └───────────────────────────────────────────────────┘   │
│                                                             │
│    ┌───────────────────────────────────────────────────┐   │
│    │ PostgreSQL api4_battles (СВОЯ БД!)                │   │
│    ├───────────────────────────────────────────────────┤   │
│    │ Таблицы:                                          │   │
│    │ • battles - основные данные боев                  │   │
│    │ • players - справочник игроков                    │   │
│    │ • clans - справочник кланов                       │   │
│    │ • monsters - справочник монстров                  │   │
│    │ • resources - справочник ресурсов                 │   │
│    │ • battle_participants - участники боев            │   │
│    │ • battle_monsters - монстры в боях                │   │
│    │ • battle_resources - ресурсы из боев              │   │
│    │                                                   │   │
│    │ Витрины (data marts):                             │   │
│    │ • daily_player_features - фичи игроков            │   │
│    │ • daily_clan_features - агрегат по кланам         │   │
│    │ • resource_anomalies - аномалии в экономике       │   │
│    │ • bot_suspicion - скоринг антибота                │   │
│    └───────────────────────────────────────────────────┘   │
│                                                             │
│    ┌───────────────────────────────────────────────────┐   │
│    │ API Endpoints (аналитика)                         │   │
│    ├───────────────────────────────────────────────────┤   │
│    │ GET /api/battle/{id} - детали боя                 │   │
│    │ GET /api/battle/list - список боев                │   │
│    │ GET /api/battle/search - поиск боев               │   │
│    │                                                   │   │
│    │ GET /api/analytics/player/{login} - игрок         │   │
│    │ GET /api/analytics/clan/{name} - клан             │   │
│    │ GET /api/analytics/resource/{name} - ресурс       │   │
│    │ GET /api/analytics/monster/{kind} - монстр        │   │
│    │ GET /api/analytics/anomalies - аномалии           │   │
│    │ GET /api/analytics/stats - общая статистика       │   │
│    └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 ПОЛНЫЙ ПОТОК ДАННЫХ

### 1. Создание лога:
```
Game Server (HOST_SERVER) → создает 3674169.tzb
    ↓ сохраняет в /home/zero/logs/btl/73/ (73 = 3674169/50000)
```

### 2. Синхронизация:
```
btl_syncer (HOST_API) → rsync pull → btl_rsyncd (HOST_SERVER)
    ↓ копирует в ./xml/mirror/3674169.tzb
```

### 3. Сжатие:
```
btl_compressor (HOST_API) → gzip
    ↓ создает ./xml/gz/73/3674169.tzb.gz
```

### 4. Парсинг и загрузка:
```
API 4: POST /api/sync
    ↓ сканирует ./xml/gz/
    ↓ парсит 3674169.tzb.gz (XML)
    ↓ извлекает:
      • battle_id: 3674169
      • date: 2025-10-01
      • winner: Игрок123
      • participants: [Игрок123, Игрок456]
      • monsters: [Goblin x10, Orc x5]
      • resources: [Gold: 100, Wood: 50]
    ↓ сохраняет в PostgreSQL api4_battles
```

### 5. Аналитика:
```
API 4: GET /api/analytics/player/Игрок123
    ↓ SELECT FROM daily_player_features
    ↓ агрегация: battles_count, wins, SR, KPT
    ↓ возврат JSON
```

---

## 📊 ВСЕ ENDPOINT API 4

### Health (1 шт):
1. `GET /healthz` - проверка здоровья

### Боевые логи (3 шт):
2. `GET /api/battle/{battle_id}` - детали боя
3. `GET /api/battle/list` - список боев (пагинация)
4. `GET /api/battle/search` - поиск боев (игрок, клан, дата, тип)

### Синхронизация (2 шт):
5. `POST /api/sync` - синхронизация новых файлов
6. `POST /api/sync/reprocess` - повторная обработка ошибок

### Аналитика (7 шт):
7. `GET /api/analytics/player/{login}` - аналитика игрока
8. `GET /api/analytics/players/top` - топ игроков
9. `GET /api/analytics/clan/{name}` - аналитика клана
10. `GET /api/analytics/resource/{name}` - аналитика ресурса
11. `GET /api/analytics/monster/{kind}` - аналитика монстра
12. `GET /api/analytics/anomalies` - аномалии в ресурсах
13. `GET /api/analytics/stats` - общая статистика

### Администрирование (2 шт):
14. `GET /api/admin/loading-stats` - статистика загрузки (требует токен)
15. `POST /api/admin/cleanup` - очистка старых записей (требует токен)

**ИТОГО: 15 endpoint**

---

## 🔍 КАК API 4 ПОЛУЧАЕТ ФАЙЛЫ

### Вариант 1: Через btl_syncer (автоматически)

```
btl_syncer (каждые 60 сек)
    ↓ rsync pull
    ↓ ./xml/mirror/

btl_compressor (каждые 30 сек)
    ↓ gzip
    ↓ ./xml/gz/

API 4: POST /api/sync
    ↓ сканирует ./xml/gz/
    ↓ парсит и загружает в БД
```

### Вариант 2: Через api_mother (по требованию)

```
API 4 → api_mother
    ↓ GET /gz/{path}
    ↓ получает сжатый файл
    ↓ парсит локально
    ↓ загружает в БД
```

**Текущая реализация:** Вариант 1 (автоматическая синхронизация)

---

## 🗄️ БАЗЫ ДАННЫХ API 4

### PostgreSQL api4_battles (СВОЯ БД на HOST_API):

**Основные таблицы:**
- `battles` - метаданные боев
- `battle_participants` - участники
- `battle_monsters` - монстры
- `battle_resources` - ресурсы

**Справочники:**
- `players` - все игроки
- `clans` - все кланы
- `monsters` - виды монстров
- `resources` - типы ресурсов

**Витрины (data marts):**
- `daily_player_features` - агрегаты по игрокам
- `daily_clan_features` - агрегаты по кланам
- `resource_anomalies` - аномалии в экономике
- `bot_suspicion` - антибот скоринг

### НЕ использует:
- ❌ MySQL tzserver (это для регистрации/констант)
- ❌ db_bridge (не нужен, своя БД)

---

## 🔗 ИНТЕГРАЦИЯ С ДРУГИМИ СЕРВИСАМИ

### API 4 обращается к:

1. **api_mother** (опционально):
   - `GET /sync` - запросить синхронизацию
   - `GET /gz/{path}` - получить конкретный файл

2. **PostgreSQL api4_battles**:
   - Своя БД на HOST_API
   - Прямое подключение (localhost:5432)

3. **Файловая система**:
   - Чтение из ./xml/mirror или ./xml/gz
   - Парсинг .tzb файлов

### API 4 НЕ обращается к:
- ❌ api_father (нет необходимости)
- ❌ db_bridge (нет необходимости)
- ❌ MySQL tzserver (своя БД)
- ❌ Game Server (нет необходимости)

---

## 📈 ПРИМЕР РАБОТЫ API 4

### Сценарий: Получить аналитику игрока

```
1. Клиент → GET /api/analytics/player/Игрок123?days=30
   ↓
2. API 4 → PostgreSQL api4_battles
   ↓ SELECT FROM daily_player_features
   ↓ WHERE login = 'Игрок123' AND date >= NOW() - INTERVAL '30 days'
   ↓
3. PostgreSQL → результат:
   {
     "battles_count": 150,
     "wins": 120,
     "losses": 30,
     "sr_avg": 0.80,
     "kpt_avg": 5.2,
     "resources_total": 15000,
     "exp_gained": 50000
   }
   ↓
4. API 4 → возврат JSON клиенту
```

---

## 🎯 ОСНОВНЫЕ USE CASES

### 1. Синхронизация новых логов:
```bash
POST /api/sync
→ API 4 сканирует ./xml/gz/
→ Находит новые файлы
→ Парсит XML
→ Загружает в PostgreSQL
→ Ответ: {"synced": 10, "total": 100}
```

### 2. Поиск боев игрока:
```bash
GET /api/battle/search?player=Игрок123&limit=10
→ API 4 → SELECT FROM battles
→ JOIN battle_participants
→ WHERE player_login = 'Игрок123'
→ LIMIT 10
→ Ответ: {"battles": [...], "total": 150}
```

### 3. Аналитика клана:
```bash
GET /api/analytics/clan/МойКлан?days=7
→ API 4 → SELECT FROM daily_clan_features
→ WHERE clan_name = 'МойКлан'
→ AND date >= NOW() - INTERVAL '7 days'
→ Ответ: {"battles": 50, "avg_members": 12, "wins": 40}
```

### 4. Поиск аномалий:
```bash
GET /api/analytics/anomalies?days=7
→ API 4 → SELECT FROM resource_anomalies
→ WHERE z_score > 3  # статистические выбросы
→ Ответ: [{"player": "Bot123", "resource": "Gold", "z_score": 5.2}]
```

---

## 📦 ЗАВИСИМОСТИ API 4

### Сервисы (HOST_API):
- **btl_syncer** - синхронизация файлов
- **btl_compressor** - сжатие файлов
- **api_4_db** - PostgreSQL база данных
- **api_mother** - (опционально) HTTP API для файлов

### Внешние (HOST_SERVER):
- **btl_rsyncd** - rsync daemon для логов

### НЕ зависит от:
- ❌ api_father
- ❌ db_bridge
- ❌ MySQL tzserver
- ❌ Game Server

---

## 🔧 ТЕХНИЧЕСКИЙ СТЕК

- **Framework:** FastAPI (async)
- **БД:** PostgreSQL (asyncpg)
- **Парсинг:** XML (lxml или встроенный)
- **Файлы:** pathlib, gzip
- **Аналитика:** SQL витрины
- **Clean Architecture:** ports, adapters, usecases

---

## ✅ ИТОГО: API 4

**Назначение:** Аналитика логов боев

**Входные данные:** .tzb файлы (XML логи)

**Обработка:** Парсинг → Нормализация → Витрины

**Выходные данные:** JSON API (поиск, аналитика)

**БД:** PostgreSQL api4_battles (СВОЯ!)

**Endpoint:** 15 штук

**Статус:** Полностью автономный микросервис

---

**Дата:** 2025-10-01
