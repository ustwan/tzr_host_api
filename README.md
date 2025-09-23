### WG Hub + Traefik: пошаговое руководство для новичков

Это инструкция как запустить:
- VPN-хаб WireGuard (wg-easy) на HOST_1 (Linux) в режиме host (UDP/51820)
- Traefik как единый вход по HTTPS (80/443) для ваших локальных сервисов (бот, ML API и т.д.)
- Ограничение доступа по IP для API и webhook через Traefik middleware

Поддержка двух сценариев запуска:
- Очень простой «одним файлом» — `scripts/quick_setup.sh`
- Раздельные compose-стеки — при необходимости

---

#### 0) Предпосылки
- HOST_1: Linux сервер с Docker + Docker Compose (plugin), доступен `/dev/net/tun`
- Открыт порт UDP/51820 извне к HOST_1 (для WireGuard)
- Для Traefik с Let’s Encrypt: домен указывает на IP HOST_1 (A-запись), порты 80/443 открыты

Проверка Docker:
```bash
docker --version
docker compose version
```

---

#### 1) Супер-быстрый запуск одним скриптом
Скрипт включит ip_forward, создаст сеть, поднимет wg-easy и Traefik с TLS и whitelist’ами.

Замените значения на свои и запустите:
```bash
WG_HOST=<PUBLIC_IP_OR_DNS_OF_HOST1> \
DOMAIN=api.example.com \
EMAIL=admin@example.com \
API_ALLOW_CIDRS='["1.2.3.4/32","5.6.7.0/24"]' \
WEBHOOK_ALLOW_CIDRS='["149.154.160.0/20","91.108.4.0/22"]' \
bash scripts/quick_setup.sh
```
Где:
- WG_HOST — публичный IP или DNS HOST_1 (куда подключаются WG‑клиенты)
- DOMAIN — домен для HTTPS (указывает на HOST_1)
- EMAIL — почта для Let’s Encrypt
- API_ALLOW_CIDRS — список сетей с доступом к API (nn2/toxicity/apanc)
- WEBHOOK_ALLOW_CIDRS — сети Telegram для webhook

Проверка, что контейнеры работают:
```bash
docker ps
```
Должны быть: `wg-easy` и `traefik-vpn-external`.

UI wg-easy (51821/tcp) — ограничьте в фаерволе (не открывайте в Интернет), используйте VPN/админ-сеть.

---

#### 2) Создание пиров (клиентов) WireGuard
Откройте UI wg-easy (порт 51821) с доверенной сети или через SSH‑туннель и создайте клиентов HOST_2, HOST_3...
- Подсеть VPN: 10.8.0.0/24
- Серверный адрес: 10.8.0.1
- Клиентам назначайте 10.8.0.2/10.8.0.3 и т.д.

Проверьте из клиента пинг до хаба:
```bash
ping 10.8.0.1
```

---

#### 3) Подключение сервисов к Traefik (бот/ML API)
Traefik уже поднят (порты 80/443) и подключен к внешней сети `edge_net`.
Ваши контейнеры нужно:
1) Подключить к сети `edge_net`
2) Добавить traefik‑лейблы (роуты по домену и пути), указать `loadbalancer.server.port`
3) Для API задать middleware `api-allow@file`, для webhook — `webhook-allow@file`

Пример для сервиса, слушающего 8002 внутри контейнера (nn2):
```yaml
services:
  nn2:
    image: your/nn2:latest
    networks: [edge_net]
    labels:
      - traefik.enable=true
      - traefik.http.routers.nn2.rule=Host(`$DOMAIN`) && PathPrefix(`/score2`)
      - traefik.http.routers.nn2.entrypoints=websecure
      - traefik.http.routers.nn2.tls.certresolver=le
      - traefik.http.routers.nn2.middlewares=api-allow@file
      - traefik.http.services.nn2.loadbalancer.server.port=8002
networks:
  edge_net:
    external: true
```
Аналогично для:
- бот (порт 8080) с маршрутом `/$WEBHOOK_PATH` и middleware `webhook-allow@file`
- toxicity (порт 8000) — PathPrefix(`/score`), middleware `api-allow@file`
- apanc (порт 8001) — PathPrefix(`/score_apanc`), middleware `api-allow@file`

После добавления лейблов перезапустите ваш проект:
```bash
docker compose up -d
```

Проверка:
```bash
curl -I https://$DOMAIN/score2/healthz
```
Должно работать только из разрешённых IP (API_ALLOW_CIDRS).

---

#### 4) Что делает скрипт `quick_setup.sh`
- Включает форвардинг IP на хосте
- Создаёт внешнюю сеть `edge_net`
- Поднимает `wg-easy` в host‑режиме (порт UDP/51820, UI 51821/tcp)
- Поднимает Traefik (80/443) с Let’s Encrypt (HTTP‑01) и динамическими middleware:
  - Файл: `/opt/edge-proxy/dynamic/middlewares.yml`
  - `api-allow` и `webhook-allow` берут CIDR из переменных окружения

Логи:
```bash
docker logs -f traefik-vpn-external
```
Сертификаты: `/opt/edge-proxy/letsencrypt/acme.json` (права 600)

---

#### 5) Фаервол (очень кратко)
- Разрешить UDP/51820 (извне) → HOST_1
- Разрешить TCP/80 и TCP/443 (извне) → HOST_1 (для выдачи/обновления сертификатов и доступа к API)
- Ограничить доступ к UI wg-easy (51821/tcp) только из доверенных сетей
- При необходимости ограничить 443 по wg0/10.8.0.0/24 — если хотите доступ только из VPN

---

#### 6) Частые проверки/проблемы
- DNS домена должен указывать на HOST_1 (иначе Let’s Encrypt не выдаст сертификат)
- Порты 80/443 должны быть доступны снаружи для HTTP‑01
- Для Telegram webhook используйте IPv4 whitelist: `149.154.160.0/20`, `91.108.4.0/22`
- Если wg‑интерфейс не поднимается: убедитесь, что `/dev/net/tun` доступен и модуль wireguard загружен (`sudo modprobe wireguard`)

---

#### 7) Альтернатива: раздельные compose (необязательно)
- `wg-easy/docker-compose.yml` — поднимет только VPN хаб
- `docker-compose.traefik.yml` — внешний Traefik с ACME и file provider
- `scripts/setup_host1.sh` — включает ip_forward и поднимает оба стека по отдельности

Для новичков рекомендован `scripts/quick_setup.sh`.
