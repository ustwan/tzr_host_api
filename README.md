# WireGuard Hub + Traefik

Два проверенных сценария:
- Mode A — внешний вход остаётся на tuna; Traefik используется только внутри VPN (10.8.0.1:443)
- Mode B — внешний вход через Traefik (80/443) с Let’s Encrypt и IP‑ограничениями

## 0. Получение проекта
```bash
git clone https://github.com/ustwan/WG_HOST.git
cd WG_HOST
```

## 1. Предпосылки
- Linux, Docker, Docker Compose plugin
- UDP/51820 открыт или проброшен на HOST_1
- /dev/net/tun доступен
- Для Mode B: домен (A‑запись → HOST_1), порты 80/443 открыты

Быстрые проверки:
```bash
docker --version && docker compose version
sudo ss -ulpn | grep 51820 || true
```

## 2. Выберите сценарий
### Mode A — VPN‑вход; tuna снаружи без изменений
- WG_HOST — публичный IP или домен для WG‑клиентов (Endpoint)
```bash
WG_HOST=<PUBLIC_IP_OR_DNS_OF_HOST1> bash scripts/install_mode_a.sh
```
Что произойдёт:
- Включится ip_forward
- Поднимется wg‑easy в host‑режиме (UDP/51820, UI 51821/tcp)
- Поднимется внутренний Traefik на 10.8.0.1:443 (для доступа из VPN)

Проверка:
```bash
docker ps | egrep "wg-easy|traefik"
```

Публикация внутренних API (доступ только из VPN):
```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.api_a.entrypoints=vpn
  - traefik.http.routers.api_a.rule=PathPrefix(`/api-a`)
  - traefik.http.services.api_a.loadbalancer.server.port=8080
```
Доступ: https://10.8.0.1/api-a из любой WG‑машины.

### Mode B — внешний Traefik (80/443) с Let’s Encrypt
- WG_HOST, DOMAIN, EMAIL, CIDR‑списки для IP‑ограничений
```bash
WG_HOST=<PUBLIC_IP_OR_DNS_OF_HOST1> \
DOMAIN=api.example.com \
EMAIL=admin@example.com \
API_ALLOW_CIDRS='["1.2.3.4/32","5.6.7.0/24"]' \
WEBHOOK_ALLOW_CIDRS='["149.154.160.0/20","91.108.4.0/22"]' \
bash scripts/install_mode_b.sh
```
Что произойдёт:
- Включится ip_forward, создастся сеть edge_net
- Поднимется wg‑easy (UDP/51820)
- Поднимется Traefik на 80/443, ACME HTTP‑01, dynamic middleware (`/opt/edge-proxy/dynamic/middlewares.yml`)

Публикация сервисов (пример nn2:8002):
```yaml
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

## 3. WireGuard: клиенты и проверка
- Откройте UI wg‑easy (51821/tcp) из доверенной сети; создайте клиентов 10.8.0.2/10.8.0.3...
- Handshake на сервере:
```bash
sudo docker exec -it wg-easy wg show || sudo wg show
```
- С клиента: `ping 10.8.0.1`

## 4. Фаервол
- UDP/51820 → HOST_1 (внешний)
- Mode A: TCP/443 ограничить wg0/10.8.0.0/24
- Mode B: TCP/80, TCP/443 открыть извне (ACME, доступ)
- UI wg‑easy 51821/tcp — ограничить по IP/сетям админов

## 5. Отладка
```bash
docker logs -f wg-easy
docker logs -f traefik-vpn-external  # Mode B
sudo tcpdump -ni any udp port 51820  # проверка входящего WG
```

## 6. Примечания
- WG_HOST может быть доменом с динамическим DNS или статичным IP
- При CGNAT нужен VPS/relay для входящего 51820/udp
- Для webhook Telegram используйте IPv4 whitelist: 149.154.160.0/20, 91.108.4.0/22
