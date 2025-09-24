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
