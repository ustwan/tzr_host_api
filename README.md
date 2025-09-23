### WG Hub + Traefik: пошаговое руководство для новичков

Это инструкция как запустить:
- VPN-хаб WireGuard (wg-easy) на HOST_1 (Linux) в режиме host (UDP/51820)
- Traefik как единый вход по HTTPS (80/443) для ваших локальных сервисов (бот, ML API и т.д.)
- Ограничение доступа по IP для API и webhook через Traefik middleware

Поддержка двух сценариев запуска:
- Очень простой «одним файлом» — `scripts/quick_setup.sh`
- Раздельные compose-стеки — при необходимости

---

#### 0) Скачивание репозитория
Выберите любой вариант:
```bash
# HTTPS (проще)
git clone https://github.com/ustwan/WG_HOST.git
cd WG_HOST

# или SSH (если настроен ключ на GitHub)
# git clone git@github.com:ustwan/WG_HOST.git
# cd WG_HOST
```

#### 1) Предпосылки
- HOST_1: Linux сервер с Docker + Docker Compose (plugin), доступен `/dev/net/tun`
- Открыт порт UDP/51820 извне к HOST_1 (для WireGuard) — у вас БЕЛЫЙ статичный IP и проброшен 51820/udp
- Если хотите внешние HTTPS‑входы через Traefik (вместо tuna): домен указывает на HOST_1, порты 80/443 открыты

Проверка Docker:
```bash
docker --version
docker compose version
```

Быстрая проверка порта 51820/udp:
```bash
# на HOST_1: убедитесь, что WireGuard слушает
sudo ss -ulpn | grep 51820 || true
# с внешнего хоста: индикативная проверка
nmap -sU -p 51820 <ваш_публичный_IP>
# попытка подключения тестовым клиентом — лучший способ (появится handshake в `sudo wg show`)
```

WG_HOST — адрес, по которому клиенты WG подключаются к хабу:
- Рекомендуется: ваш домен (динамический DNS тоже подойдёт)
- Допустимо: ваш статичный публичный IP

---

#### 2) Выберите режим
- Режим A: Оставить tuna снаружи (внешний HTTPS), Traefik использовать ТОЛЬКО внутри VPN
  - Запуск: `bash scripts/setup_host1.sh`
  - Итог: внешка как была в tuna; VPN‑клиенты получают доступ к внутренним API через 10.8.0.1:443 (Traefik‑vpn)
  - DOMAIN не нужен. Нужен только WG_HOST (публичный IP/домен для WG)

- Режим B: Полностью Traefik снаружи (заменяет tuna), Let’s Encrypt, 80/443
  - Запуск: `bash scripts/quick_setup.sh` (см. ниже)
  - Итог: единый внешний вход на 80/443, TLS, IP‑whitelist на маршрутах

Примечание: `quick_setup.sh` поднимает внешний Traefik на 80/443 и может конфликтовать с tuna. Если оставляете tuna, используйте режим A.

---

#### 3A) Режим A — VPN‑вход (tuna остаётся снаружи)
```bash
# Только VPN‑хаб + внутренний Traefik на 10.8.0.1:443
bash scripts/setup_host1.sh
```
Проверка:
```bash
sudo docker compose -f traefik/docker-compose.yml ps
sudo docker ps | grep wg-easy
```
Подключите клиентов WG к `WG_HOST:51820`. Внутренние сервисы публикуйте в Traefik (entrypoint `vpn`) по PathPrefix, доступ из VPN по https://10.8.0.1/<path>.

Пример лейблов для внутреннего сервиса:
```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.api_a.entrypoints=vpn
  - traefik.http.routers.api_a.rule=PathPrefix(`/api-a`)
  - traefik.http.services.api_a.loadbalancer.server.port=8080
```
Фаервол: разрешите 443/tcp только с интерфейса wg0 или подсети 10.8.0.0/24; UI wg-easy (51821/tcp) ограничьте для админ‑сетей/VPN.

---

#### 3B) Режим B — быстрый запуск одним скриптом (Traefik снаружи)
Скрипт включит ip_forward, создаст сеть, поднимет wg-easy и Traefik с TLS и whitelist’ами.
```bash
WG_HOST=<PUBLIC_IP_OR_DNS_OF_HOST1> \
DOMAIN=api.example.com \
EMAIL=admin@example.com \
API_ALLOW_CIDRS='["1.2.3.4/32","5.6.7.0/24"]' \
WEBHOOK_ALLOW_CIDRS='["149.154.160.0/20","91.108.4.0/22"]' \
bash scripts/quick_setup.sh
```
Проверка, что контейнеры работают:
```bash
docker ps
```
Должны быть: `wg-easy` и `traefik-vpn-external`.

---

#### 4) Создание пиров (клиентов) WireGuard
Откройте UI wg-easy (порт 51821) с доверенной сети или через SSH‑туннель и создайте клиентов HOST_2, HOST_3...
- Подсеть VPN: 10.8.0.0/24, сервер: 10.8.0.1
- Клиентам назначайте 10.8.0.2/10.8.0.3 и т.д.

Проверьте из клиента пинг до хаба:
```bash
ping 10.8.0.1
```
Handshake на сервере:
```bash
sudo docker exec -it wg-easy wg show || sudo wg show
```

---

#### 5) Подключение сервисов к Traefik
- В режиме A: внутренние маршруты по `PathPrefix` доступны из VPN на 10.8.0.1:443
- В режиме B: внешние маршруты по домену + пути, с TLS и IP‑whitelist

Пример nn2 (порт 8002) для режима B:
```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.nn2.rule=Host(`$DOMAIN`) && PathPrefix(`/score2`)
  - traefik.http.routers.nn2.entrypoints=websecure
  - traefik.http.routers.nn2.tls.certresolver=le
  - traefik.http.routers.nn2.middlewares=api-allow@file
  - traefik.http.services.nn2.loadbalancer.server.port=8002
```

---

#### 6) Фаервол (кратко)
- UDP/51820 — извне к HOST_1 (у вас уже проброшен)
- Режим A: ограничить TCP/443 только по wg0/10.8.0.0/24
- Режим B: открыть TCP/80 и TCP/443 извне (для ACME и доступа)
- UI wg-easy 51821/tcp — ограничить по IP/сетям админов

---

#### 7) Частые проверки/проблемы
- Если нет handshake: проверьте проброс 51820/udp и Endpoint в клиентском конфиге (`Endpoint = <WG_HOST>:51820`)
- Для Telegram webhook используйте IPv4 whitelist: `149.154.160.0/20`, `91.108.4.0/22`
- Если wg‑интерфейс не поднимается: убедитесь, что `/dev/net/tun` доступен и модуль wireguard загружен (`sudo modprobe wireguard`)

---

#### 8) Альтернатива: раздельные compose (необязательно)
- `wg-easy/docker-compose.yml` — поднимет только VPN хаб (host‑mode)
- `traefik/docker-compose.yml` — внутренний Traefik (10.8.0.1:443)
- `docker-compose.traefik.yml` — внешний Traefik (80/443, ACME)
- `scripts/setup_host1.sh` — режим A; `scripts/quick_setup.sh` — режим B
