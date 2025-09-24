# WG_CLIENT

Каркас клиента, работающего внутри WireGuard VPN без TLS, с единой точкой доступа к БД (API_FATHER) и маршрутизацией через Traefik.

## Архитектура
- Сети
  - `apinet` — внешняя docker-сеть (общая: Traefik + WG + доступ из VPN)
  - `backnet` — внутренняя сеть API_* ↔ API_FATHER (internal)
  - `dbnet` — внутренняя сеть API_FATHER ↔ DB (internal)
- Сервисы
  - `wg_vpn` — WireGuard-клиент; API_* работают в его net-namespace (`network_mode: service:wg_vpn`)
  - `traefik` — маршрутизация и UI (доступ только из VPN), HTTP на `:80`
  - `api_father` — единая точка к БД, плюс внутренний Redis
  - `api_1`, `api_2`, `api_3` — бизнес-ручки (слушают 0.0.0.0 на портах 8081/8082/8083 внутри netns wg_vpn)
  - `db` (MySQL 8.0.42) — только в режиме теста

Ключевое: у API_* нет собственных IP; Traefik проксирует на `http://wg_vpn:<порт>` (файловый провайдер `traefik/dynamic/apis.yml`).

## Предварительно
- Linux, Docker, Docker Compose
- WG-клиент/конфиг для `wg_vpn` (ключи/параметры в `.env`)
- Создайте сеть один раз:
```bash
docker network create apinet
```

## Быстрый старт
1) Клонирование и окружение
```bash
git clone https://github.com/ustwan/WG_CLIENT.git
cd WG_CLIENT/wg_client
cp env.example .env
nano .env
```

2) Поднять без тестовой БД (DB_MODE=prod — подключение к боевой MySQL в ЛАН):
```bash
bash tools/ctl.sh up
```

3) Поднять с тестовой БД (DB_MODE=test, авто-миграции если `MIGRATE_ON_START_TEST=1`):
```bash
bash tools/ctl.sh up-testdb
```

4) Доступы (внутри VPN)
- Traefik UI: `http://<WG_IP_CLIENTA>:80/dashboard` (basic auth из `.env`)
- Пример роутов (см. `traefik/dynamic/apis.yml`):
  - `GET http://<WG_IP_CLIENTA>/api/registration/health`
  - `GET http://<WG_IP_CLIENTA>/api/bonus/health`
  - `GET http://<WG_IP_CLIENTA>/api/info/health`

## Переключатель БД
- В `.env`: `DB_MODE=test|prod`
  - `test` — MySQL в контейнере (`compose.db.test.yml`), миграции могут применяться автоматически
  - `prod` — БД в вашей ЛАН; креды храните в `.env.secrets` (не коммитить)
- `api_father` сам выбирает DSN по `DB_MODE`

## Миграции
- Скрипты: `wg_client/db/migrations` (под Flyway)
- Тест (авто при старте, если включено): профиль `up-testdb`
- Продакшн (ручной запуск):
```bash
bash tools/ctl.sh migrate-prod
```

## Traefik (file provider)
- Статика: `traefik/traefik.yml` (entrypoint `vpn: :80`, dashboard включён)
- Динамика: `traefik/dynamic/apis.yml`
  - Пример:
```yaml
http:
  routers:
    api1:
      rule: "PathPrefix(`/api/registration`)"
      entryPoints: [ "vpn" ]
      service: api1_svc
  services:
    api1_svc:
      loadBalancer:
        servers:
          - url: "http://wg_vpn:${API1_PORT}"
```

## Добавить новый API
1) Создайте `api_4` (Dockerfile + код), слушайте `0.0.0.0:8084` внутри
2) В `compose.apis.yml` добавлять не требуется (работа в netns `wg_vpn` общая) — при необходимости добавьте build-секцию
3) В `traefik/dynamic/apis.yml` добавьте `router` и `service`:
```yaml
  routers:
    api4:
      rule: "PathPrefix(`/api/new`)"
      entryPoints: [ "vpn" ]
      service: api4_svc
  services:
    api4_svc:
      loadBalancer:
        servers:
          - url: "http://wg_vpn:8084"
```
4) Перезапуск Traefik:
```bash
docker compose -f compose.base.yml up -d traefik
```

## Утилиты
```bash
bash tools/ctl.sh up           # traefik + wg_vpn + api_father + apis
bash tools/ctl.sh up-testdb    # + db + migrator (профиль testdb)
bash tools/ctl.sh down         # остановить базовый стек
bash tools/ctl.sh down-all     # остановить всё, удалить тома test-DB
bash tools/ctl.sh logs         # общие логи
bash tools/ctl.sh restart-api1 # перезапуск конкретного API
bash tools/ctl.sh migrate-prod # миграции на PROD (осознанно)
```

## Безопасность
- Порты наружу не публикуем; `traefik` слушает только на IP интерфейса WG (`TRAEFIK_BIND_IP`)
- Секреты — в `.env.secrets` / Docker secrets, не коммитить
- Доступ к UI только из VPN; по необходимости усилить IP‑фильтрами

## Структура
```
wg_client/
  compose.base.yml
  compose.apis.yml
  compose.db.test.yml
  traefik/
    traefik.yml
    dynamic/apis.yml
  db/
    init/001_schema.sql
    migrations/
  api_father/
  api_1/
  api_2/
  api_3/
  tools/ctl.sh
  env.example
```

## Как добавить новый API (очень подробно)
Ниже пошагово описано, как добавить ещё один сервис (условно `api_4`) и сделать его доступным внутри VPN через Traefik.

### 1. Определиться с портом сервиса
- Принята схема: каждый API слушает внутри контейнера на своём порту.
- Уже занято: `api_1` → 8081, `api_2` → 8082, `api_3` → 8083.
- Новый сервис: выберите следующий свободный порт, например `8084`.
- Важно: сервис должен слушать на `0.0.0.0:<порт>` внутри контейнера, чтобы к нему могли обращаться другие контейнеры.

### 2. Подготовить структуру каталога и Dockerfile
Создайте каталог с кодом нового сервиса, например:
```
wg_client/
  api_4/
    Dockerfile
    app/  # ваш код (например, FastAPI/Flask/Node и т.п.)
```
Пример Dockerfile (Python + Uvicorn):
```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app/ /app/
RUN pip install --no-cache-dir -r requirements.txt
# ВАЖНО: слушать 0.0.0.0 и нужный порт
ENV PORT=8084
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8084"]
```

### 3. Подключить сервис к общему сетевому пространству WG
У наших API нет отдельных IP — они «живут» внутри сетевого пространства `wg_vpn`.
Это делается через `network_mode: "service:wg_vpn"`. Добавьте в `wg_client/compose.apis.yml` блок для `api_4` (или создайте файл, если его нет):
```yaml
services:
  api_4:
    build: ./api_4
    network_mode: "service:wg_vpn"     # общий net-namespace с wg_vpn
    depends_on: [ wg_vpn, api_father ]  # wg_vpn должен быть поднят
    environment:
      - TZ=${TZ}
      - API_FATHER_URL=http://api_father:9000
```
Не публикуйте наружу порты (`ports:` не нужен). Весь доступ идёт через Traefik.

### 4. Дать знать Traefik, куда проксировать (file provider)
Мы используем файлового провайдера Traefik (`wg_client/traefik/dynamic/apis.yml`). Здесь описываются правила и соответствующие им сервисы.
- Выберите URL-префикс, по которому сервис будет доступен. Например, `/api/new`.
- Добавьте `router` (правило входа) и `service` (куда Traefik шлёт трафик), указывая адрес `http://wg_vpn:8084` (порт — ваш выбранный).

Пример добавления в конец `wg_client/traefik/dynamic/apis.yml`:
```yaml
http:
  routers:
    api4:
      rule: "PathPrefix(`/api/new`)"   # любой запрос, начинающийся с /api/new
      entryPoints: [ "vpn" ]           # внутренний entrypoint vpn (HTTP внутри VPN)
      service: api4_svc
  services:
    api4_svc:
      loadBalancer:
        servers:
          - url: "http://wg_vpn:8084"  # адрес внутри общего netns
```
Подсказка: если реальный бэкенд-эндпоинт — `/healthz`, а снаружи вы хотите `/api/new/healthz`, ничего больше делать не нужно. Если ваш сервис ожидает корень `/`, а вы проксируете с префиксом (`/api/new`), то можно добавить middleware `stripPrefix` для среза префикса. Пример:
```yaml
  routers:
    api4:
      rule: "PathPrefix(`/api/new`)"
      entryPoints: [ "vpn" ]
      service: api4_svc
      middlewares: [ "api4-strip" ]
  middlewares:
    api4-strip:
      stripPrefix:
        prefixes: [ "/api/new" ]
```

### 5. Перезапустить Traefik и собрать сервис
Применить изменения:
```bash
cd wg_client
# пересобрать только api_4 (если нужно)
docker compose -f compose.apis.yml build api_4
# поднять Traefik (если уже работает, up применит конфиги)
docker compose -f compose.base.yml up -d traefik
# поднять новый сервис
docker compose -f compose.apis.yml up -d api_4
```

### 6. Проверить доступ из VPN
Предположим, клиент в VPN видит IP машины WG_CLIENT (где запущен Traefik) как `10.8.0.2`.
Тогда доступ к новому сервису:
```bash
# health
curl -i http://10.8.0.2/api/new/healthz
# пример POST
curl -sS -X POST http://10.8.0.2/api/new/raw \
  -H 'Content-Type: application/json' \
  -d '{"text":"пример"}'
```
Если вы добавили `stripPrefix`, убедитесь, что реальный путь в приложении совпадает (например, `/healthz`, `/raw`).

### 7. Частые ошибки и диагностика
- Сервис не виден, 404 от Traefik:
  - Проверьте, что вы редактировали `wg_client/traefik/dynamic/apis.yml` и перезапустили Traefik (`up -d traefik`).
  - Проверьте правило `rule` (точное написание `PathPrefix(`/api/new`)`).
- 502/connection refused:
  - Сервис не слушает на `0.0.0.0:8084`.
  - Контейнер не запущен или упал: `docker compose -f compose.apis.yml ps`, `logs`.
- Внутренний адрес:
  - Должен быть `http://wg_vpn:<порт>` (а не `localhost`/`127.0.0.1`).
- Проверка сетей:
  - `docker inspect <id_traefik> | jq '.NetworkSettings.Networks'` — Traefik в `apinet`.
  - `docker inspect <id_api4> | jq '.HostConfig.NetworkMode'` — для API должен быть `service:wg_vpn`.
- UI Traefik:
  - `http://10.8.0.2/dashboard` (только из VPN). В разделах Routers/Services можно увидеть `api4`.

### 8. Итоговая памятка по портам
- Внутри контейнера API_4 слушает `8084`.
- Traefik внутри VPN слушает HTTP на `:80` (привязан к `TRAEFIK_BIND_IP`, обычно адрес интерфейса WG, например 10.8.0.2).
- Доступ к сервису извне контейнеров (из вашей машины в VPN): `http://10.8.0.2/api/new/...`.
- Наружные публикации `ports:` для API_* не требуются — вход централизован через Traefik.

## Пул портов для API (внутренний)
Принята единая политика распределения портов внутри общего сетевого пространства WG (без публикации наружу):

- 8000–8099: прикладные API
  - 8081: api_1
  - 8082: api_2
  - 8083: api_3
  - 8084–8099: новые API (api_4, api_5, ...)
- 8100–8199: служебные/вспомогательные mini-API
- 9000: API_FATHER
- 9100–9199: админ-панели внутренних сервисов (при необходимости)
- 9300–9399: внутренние адаптеры/интеграции
- 6379: Redis (только в backnet)
- 3306: MySQL (только в dbnet, режим test)

Правила:
- Каждый новый API получает следующий свободный порт из диапазона 8084–8099, затем 8100+.
- Сервис слушает строго `0.0.0.0:<порт>` внутри контейнера.
- Traefik проксирует на `http://wg_vpn:<порт>` через файлового провайдера (`traefik/dynamic/apis.yml`).
- Наружных `ports:` для API не задаём; вход централизован через Traefik на WG-IP:80.

Краткий шаблон для нового API:
- Dockerfile: `--host 0.0.0.0 --port 8084`
- `compose.apis.yml`: `network_mode: "service:wg_vpn"`
- `traefik/dynamic/apis.yml`:
```yaml
http:
  routers:
    api4:
      rule: "PathPrefix(`/api/new`)"
      entryPoints: [ "vpn" ]
      service: api4_svc
  services:
    api4_svc:
      loadBalancer:
        servers:
          - url: "http://wg_vpn:8084"
```
