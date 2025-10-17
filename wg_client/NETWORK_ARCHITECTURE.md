# Архитектура сетей WG_HUB

## Обзор

Проект использует **ОДНУ ОБЩУЮ СЕТЬ** для максимальной простоты и надежности:

```
┌─────────────────────────────────────────────────────────────┐
│                   HOST-API-NETWORK                           │
│                  (Одна общая сеть)                           │
├─────────────────────────────────────────────────────────────┤
│  Frontend:                                                   │
│  • Traefik, Swagger UI, ReDoc                                │
│  • Monitoring (Netdata, Portainer, Homarr)                   │
│                                                              │
│  Backend:                                                    │
│  • API (api_1, api_2, api_4, api_father, api_mother)        │
│  • XML Workers (6 параллельных воркеров)                     │
│  • BTL Workers (compressor, syncer)                          │
│                                                              │
│  Database:                                                   │
│  • PostgreSQL (api_4_db), MySQL (db-1), Redis               │
│  • pgAdmin, Metabase                                         │
└─────────────────────────────────────────────────────────────┘
```

## Детальная схема

### Единая сеть (`host-api-network`)

**Назначение:** Все сервисы проекта в одной сети

**Контейнеры:**
- `traefik` - Reverse proxy и маршрутизация (bridge между frontend и backend)
- `swagger-ui` - API документация
- `redoc` - API документация (альтернативная)
- `portainer` - UI управления Docker
- `netdata` - Мониторинг системы
- `dozzle` - Просмотр логов
- `uptime-kuma` - Мониторинг аптайма
- `homarr` - Dashboard
- `filebrowser` - Браузер файлов
- `ttyd` - Web terminal

### 2. Backend-Net (`host-api-backend-net`)

**Назначение:** Бизнес-логика, API, обработка данных

**Контейнеры:**

#### API Сервисы:
- `api_1` - API v1 (легковесный)
- `api_2` - API v2 (легковесный)
- `api_4` - API v4 (тяжеловесный, основной)
- `api_father` - API Father (координатор)
- `api_mother` - API Mother (агрегатор)

#### XML Workers:
- `xml_worker_1` - Sova Oasis
- `xml_worker_2` - Sova Neva
- `xml_worker_3` - Sova Jerusalem
- `xml_worker_4` - Sova Kabul
- `xml_worker_5` - Sova SYN
- `xml_worker_6` - Sova Moscow

#### Background Workers:
- `worker` - Фоновые задачи
- `btl_syncer` - Синхронизация логов
- `btl_compressor` - Сжатие логов
- `game_server_mock` - Мок игрового сервера

### 3. Database-Net (`host-api-database-net`)

**Назначение:** Хранение данных

**Контейнеры:**
- `api_4_db` - PostgreSQL для API 4 (основная БД боев)
- `db-1` - MySQL (основная БД проекта)
- `api_father_redis` - Redis (очереди, кеш)
- `metabase-db` - PostgreSQL для Metabase
- `pgadmin` - UI для PostgreSQL
- `migrator` - Flyway миграции

## Связи между сетями

### Traefik (Frontend ↔ Backend)
Traefik находится в **обеих** сетях (frontend-net + backend-net) и выступает мостом:
- Принимает HTTP запросы от UI (frontend-net)
- Маршрутизирует к API сервисам (backend-net)

### API Сервисы (Backend ↔ Database)
API сервисы находятся в **обеих** сетях (backend-net + database-net):
- Обрабатывают запросы от Traefik (backend-net)
- Обращаются к БД (database-net)

### UI Сервисы
Swagger UI и ReDoc находятся в **обеих** сетях (frontend-net + backend-net):
- Обслуживаются через frontend-net
- Получают OpenAPI specs от API через backend-net

## Преимущества архитектуры

1. **Безопасность:**
   - UI не имеет прямого доступа к БД
   - Четкое разделение слоев

2. **Масштабируемость:**
   - Каждый слой можно масштабировать независимо
   - Backend может иметь несколько реплик

3. **Простота управления:**
   - Логичное разделение по функциональности
   - Легко понять кто с кем общается

4. **Производительность:**
   - Только необходимые связи между контейнерами
   - Нет лишних сетевых интерфейсов

## Compose файлы

| Файл | Сети | Сервисы |
|------|------|---------|
| `HOST_API_SERVICE_INFRASTRUCTURE.yml` | frontend + backend + database | Traefik, Redis |
| `HOST_API_SERVICE_MONITORING.yml` | frontend + backend | UI, мониторинг |
| `HOST_API_SERVICE_DB_API.yml` | database | PostgreSQL, MySQL |
| `HOST_API_SERVICE_DB_MONITORING.yml` | database | Metabase |
| `HOST_API_SERVICE_UTILITIES.yml` | database | pgAdmin |
| `HOST_API_SERVICE_FATHER_API.yml` | backend + database | API Father |
| `HOST_API_SERVICE_LIGHT_WEIGHT_API.yml` | backend + database | API 1, 2, Mother |
| `HOST_API_SERVICE_HEAVY_WEIGHT_API.yml` | backend + database | API 4 |
| `HOST_API_SERVICE_XML_WORKERS.yml` | backend | XML Workers (6) |
| `HOST_API_SERVICE_WORKERS.yml` | backend | BTL Workers |

## Создание сетей

Сети создаются автоматически при запуске через `ctl.sh`, но можно создать вручную:

```bash
docker network create host-api-frontend-net --driver bridge
docker network create host-api-backend-net --driver bridge
docker network create host-api-database-net --driver bridge
```

## Проверка связности

```bash
# Проверка контейнеров в сетях
docker network inspect host-api-frontend-net | jq -r '.[] | .Containers | to_entries[] | .value.Name'
docker network inspect host-api-backend-net | jq -r '.[] | .Containers | to_entries[] | .value.Name'
docker network inspect host-api-database-net | jq -r '.[] | .Containers | to_entries[] | .value.Name'

# Проверка связи API 4 → XML Workers
curl http://localhost:8084/admin/xml-workers/health?admin_token=test_admin_token_123

# Проверка связи API 4 → БД
docker exec wg-client-api_4-1 nc -zv host-api-service-api_4_db-1 5432
```

## История изменений

### v3.3 (2025-10-09)
- ✅ Миграция с 4 несогласованных сетей на 3-сетевую архитектуру
- ✅ Устранено дублирование контейнеров в сетях
- ✅ Исправлена проблема с доступностью XML Workers из API 4
- ✅ Обновлены все 11 compose файлов

### До v3.3
- ❌ 4 сети с неясным назначением (apinet, backnet, dbnet, host-api-network)
- ❌ Массовое дублирование контейнеров
- ❌ Проблемы с доступностью между сервисами

