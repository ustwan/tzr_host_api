# API_1 (server_status)

Цель: отдать агрегированный статус сервера в формате JSON (server_status + rates + meta), читая данные из БД через API_FATHER.

Итоговый формат JSON (окончательный)
```json
{
  "server_status": 1.0,
  "rates": {
    "exp": 1.0,
    "pvp": 1.0,
    "pve": 1.0,
    "color_mob": 1.0,
    "skill": 1.0
  },
  "client_status": 256.0,
  "_meta": {
    "ServerStatus": "1 = всем доступен серв",
    "RateExp": "Опыт",
    "RatePvp": "ПВП",
    "RatePve": "ПВЕ",
    "RateColorMob": "x1",
    "RateSkill": "Скиллы",
    "CLIENT_STATUS": "статус"
  }
}
```

## 1) Подготовка окружения
- Перейдите в каталог проекта:
```bash
cd wg_client
```
- Скопируйте и заполните `.env`:
```bash
cp env.example .env
nano .env
```
- Создайте внешнюю сеть (один раз):
```bash
docker network create apinet
```

## 2) Поднять стек (без/с тестовой БД)
- Без контейнерной БД (DB_MODE=prod):
```bash
bash tools/ctl.sh up
```
- С тестовой БД (DB_MODE=test) и авто-миграциями (если включено в .env):
```bash
bash tools/ctl.sh up-testdb
```

## 3) Что уже реализовано
- API_FATHER (FastAPI, порт 9000) — читает MySQL и отдаёт `/internal/constants` как мапу `Name -> {value, description}`
  - Код: `wg_client/api_father/app/main.py`
- API_1 (FastAPI, порт 8081) — ходит к API_FATHER и собирает итоговый JSON
  - Код: `wg_client/api_1/app/main.py`
  - Эндпоинты:
    - `/healthz` — проверка живости
    - `/server/status` — итоговый JSON (схема выше)
- Traefik (file provider, HTTP внутри VPN на :80)
  - Роут `/api/server/*` → API_1 (срез префикса): `stripPrefix: /api/server`
  - Конфигурация: `wg_client/traefik/dynamic/apis.yml`

## 4) Как это работает (поток запросов)
1. Клиент в VPN делает запрос: `GET http://<WG_IP_CLIENTA>:80/api/server/status`
2. Traefik (entrypoint vpn:80) маршрутизирует на `http://wg_vpn:8081/server/status`
3. API_1 запрашивает у API_FATHER `GET http://api_father:9000/internal/constants`
4. API_FATHER читает таблицу `tzserver.constants` и отдаёт мапу
5. API_1 собирает итоговый JSON и возвращает клиенту

## 5) Проверка
- UI Traefik: `http://<WG_IP_CLIENTA>/dashboard`
- API_1:
```bash
curl -i http://<WG_IP_CLIENTA>/api/server/status
```
Замените `<WG_IP_CLIENTA>` на адрес вашей WG-интерфейса у клиента (например, 10.8.0.2).

## 6) Тонкости и ошибки
- API_1 и API_FATHER должны быть подняты:
```bash
docker compose -f compose.base.yml up -d traefik api_father
docker compose -f compose.apis.yml up -d api_1
```
- Внутренние порты:
  - API_1 слушает `0.0.0.0:8081`
  - API_FATHER слушает `0.0.0.0:9000`
- DB_MODE:
  - `test` — используется контейнерная MySQL (композ `compose.db.test.yml`),
  - `prod` — LAN‑БД из `.env` (секреты в `.env.secrets`).
- Если `/api/server/status` отдаёт 502:
  - Проверьте, доступен ли API_FATHER: `curl -s http://api_father:9000/internal/health` из контейнера API_1,
  - Посмотрите логи API_1: `docker logs <container_api_1>`.
- Если 404 на `/api/server/status`:
  - Перезапустите Traefik и проверьте `wg_client/traefik/dynamic/apis.yml` (rule, service):
```bash
docker compose -f compose.base.yml up -d traefik
```

## 7) Добавить следующий API — полный пример
Ниже полный пример создания `api_4` с нуля (каталог, Dockerfile, код, маршрутизация, запуск).

1. Создайте каталог и Dockerfile
```bash
mkdir -p wg_client/api_4/app
cat > wg_client/api_4/Dockerfile <<'DOCKER'
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY app/ /app/
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8084"]
DOCKER
```

2. Создайте минимальный FastAPI‑приложение
```bash
cat > wg_client/api_4/app/main.py <<'PY'
from fastapi import FastAPI
app = FastAPI(title="API_4 example")
@app.get("/healthz")
def health():
    return {"status": "ok"}
PY
```

3. Подключите сервис к общему netns wg_vpn (compose.apis.yml)
```yaml
services:
  api_4:
    build: ./api_4
    network_mode: "service:wg_vpn"
    depends_on: [ wg_vpn, api_father ]
    environment:
      - TZ=${TZ}
      - API_FATHER_URL=http://api_father:9000
```

4. Пропишите маршрутизацию в Traefik (file provider)
Добавьте в `wg_client/traefik/dynamic/apis.yml`:
```yaml
http:
  routers:
    api4:
      rule: "PathPrefix(`/api/new`)"
      entryPoints: [ "vpn" ]
      service: api4_svc
      middlewares: [ "api4-strip" ]
  services:
    api4_svc:
      loadBalancer:
        servers:
          - url: "http://wg_vpn:8084"
  middlewares:
    api4-strip:
      stripPrefix:
        prefixes: [ "/api/new" ]
```

5. Соберите и запустите
```bash
cd wg_client
# собрать новый сервис
docker compose -f compose.apis.yml build api_4
# применить конфигурацию Traefik (если уже работает — просто up)
docker compose -f compose.base.yml up -d traefik
# запустить новый api
docker compose -f compose.apis.yml up -d api_4
```

6. Проверьте доступ из VPN
```bash
curl -i http://<WG_IP_CLIENTA>/api/new/healthz
```

Итого: каждый новый API — своя папка (`api_N`), Dockerfile с прослушиванием `0.0.0.0:<порт>`, подключение к `wg_vpn` через `network_mode: "service:wg_vpn"`, запись в `traefik/dynamic/apis.yml` (router+service [+ stripPrefix при необходимости]) и запуск через compose.
