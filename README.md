# WireGuard Hub + Traefik

Два проверенных сценария:
- Mode A — внешний вход остаётся на tuna; Traefik используется только внутри VPN (HTTP без TLS на 10.8.0.1:8081)
- Mode B — внешний вход через Traefik (80/443) с Let’s Encrypt и IP‑ограничениями

## 0. Получение проекта
```bash
git clone https://github.com/ustwan/WG_HOST.git
cd WG_HOST
```

## 1. Общая сеть apinet
`apinet` — внешняя docker‑сеть (bridge) для связи Traefik и ваших сервисов из других стеков.
- Создать один раз:
```bash
docker network create apinet
```
- Traefik (внутренний Mode A) должен быть в `apinet` и запущен с `--providers.docker.network=apinet`.
- Любой сервис, который должен быть виден Traefik, подключайте к `apinet` и добавляйте traefik‑лейблы.
- Пример в compose сервисов:
```yaml
networks:
  apinet:
    external: true
```

## 2. Предпосылки
- Linux, Docker, Docker Compose plugin
- UDP/51820 открыт или проброшен на HOST_1
- /dev/net/tun доступен
- Для Mode B: домен (A‑запись → HOST_1), порты 80/443 открыты

Быстрые проверки:
```bash
docker --version && docker compose version
sudo ss -ulpn | grep 51820 || true
```

## 3. Переменные окружения
Скопируйте `env.example` → `.env` и отредактируйте под себя. Пример подключения:
```bash
cp env.example .env
set -a; source ./.env; set +a
```
Ключевые переменные:
- `WG_HOST` — публичный IP/домен для клиентов WG
- `VPN_CIDR` — подсеть VPN (по умолчанию 10.8.0.0/24)
- `ENABLE_VPN_DASH`, `VPN_DASH_PORT` — открыть панель Traefik на 10.8.0.1:PORT
- `ENABLE_LAN_DASH`, `LAN_HOST_IP`, `LAN_DASH_PORT` — открыть панель Traefik на LAN‑IP:PORT
- (Mode B) `DOMAIN`, `EMAIL`, `API_ALLOW_CIDRS`, `WEBHOOK_ALLOW_CIDRS`

## 4. Выберите сценарий
### Mode A — VPN‑вход; tuna снаружи (HTTP внутри VPN)
```bash
set -a; source ./.env; set +a
bash scripts/install_mode_a.sh
```
Что произойдёт:
- Включится ip_forward, создастся сеть `apinet` при необходимости
- Поднимется wg‑easy (UDP/51820)
- Поднимется Traefik с entrypoint `vpn` на 10.8.0.1:8081 (HTTP, без TLS внутри VPN)
- При включенных флагах — Dashboard на 10.8.0.1:${VPN_DASH_PORT} и/или ${LAN_HOST_IP}:${LAN_DASH_PORT}

Публикация внутренних API (доступ только из VPN):
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.api_a.entrypoints=vpn"
  - "traefik.http.routers.api_a.rule=PathPrefix(`/api-a`)"
  - "traefik.http.services.api_a.loadbalancer.server.port=8080"
```
Доступ: http://10.8.0.1:8081/api-a из WG‑машин.

### Mode B — внешний Traefik (80/443) с Let’s Encrypt
```bash
set -a; source ./.env; set +a
bash scripts/install_mode_b.sh
```
Что произойдёт:
- Включится ip_forward, создастся `edge_net`
- Поднимется wg‑easy (UDP/51820) и Traefik на 80/443 с ACME

## 5. WireGuard: клиенты и проверка
```bash
sudo docker exec -it wg-easy wg show || sudo wg show
ping 10.8.0.1
```

## 6. Публикация сервисов
- Mode A: внутренние маршруты по PathPrefix, доступны из VPN на http://10.8.0.1:8081
- Mode B: внешние маршруты по домену + пути, TLS и whitelist

## 7. Фаервол и отладка
- UDP/51820 извне
- Mode A: TCP/8081 разрешить только для wg0/10.8.0.0/24; Dashboard порт 9001 открывать только для VPN/ЛВС
- Mode B: TCP/80/443 открыть извне (ACME, доступ)
- Логи: `docker logs -f wg-easy`, `docker logs -f traefik-vpn-external`

## Пример: добавить tzr-moder-nn2-1 в Traefik

Контейнер `tzr-moder-nn2-1` слушает внутри на 8002. Публикация через Traefik не требует проброса 8602 наружу — важен внутренний порт сервиса.

- Mode A (только из VPN, вход 10.8.0.1:8081):
```yaml
services:
  tzr-moder-nn2:
    image: tzr-moder-nn2
    networks: [apinet]
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.nn2.entrypoints=vpn"
      - "traefik.http.routers.nn2.rule=PathPrefix(`/score2`)"
      - "traefik.http.services.nn2.loadbalancer.server.port=8002"
networks:
  apinet:
    external: true
```
Доступ из VPN: http://10.8.0.1:8081/score2

- Mode B (внешний доступ по домену с TLS):
```yaml
services:
  tzr-moder-nn2:
    image: tzr-moder-nn2
    networks: [edge_net]
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.nn2.rule=Host(`$DOMAIN`) && PathPrefix(`/score2`)"
      - "traefik.http.routers.nn2.entrypoints=websecure"
      - "traefik.http.routers.nn2.tls.certresolver=le"
      - "traefik.http.routers.nn2.middlewares=api-allow@file"
      - "traefik.http.services.nn2.loadbalancer.server.port=8002"
networks:
  edge_net:
    external: true
```
Проверка: `curl -I https://$DOMAIN/score2/healthz` (доступ только из `API_ALLOW_CIDRS`).

## Перезапуск контейнеров

wg-easy (host-mode):
```bash
docker restart wg-easy
```

Traefik (внутренний, Mode A):
```bash
# без override
docker compose -f traefik/docker-compose.yml restart
# с override (если включали панель)
docker compose -f traefik/docker-compose.yml -f traefik/docker-compose.override.yml restart
```

Traefik (внешний, Mode B):
```bash
docker compose -f docker-compose.traefik.yml --project-name ${PROJECT_NAME_TRAEFIK:-proxy} restart
```

Полное пересоздание (применить изменения конфигов):
```bash
# внутренний Traefik
docker compose -f traefik/docker-compose.yml up -d
# с override
docker compose -f traefik/docker-compose.yml -f traefik/docker-compose.override.yml up -d
# внешний Traefik
docker compose -f docker-compose.traefik.yml --project-name ${PROJECT_NAME_TRAEFIK:-proxy} up -d
```

Логи для отладки:
```bash
docker logs -f wg-easy
# внутренний Traefik
docker logs -f traefik
# внешний Traefik
docker logs -f traefik-vpn-external
```
