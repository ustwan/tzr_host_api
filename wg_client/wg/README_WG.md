# WireGuard в контейнере (wg_vpn)

Положите клиентский `wg0.conf` в этот каталог. Он будет смонтирован в контейнер `/config/wg0.conf` и поднят образцом linuxserver/wireguard.

Пример `wg0.conf`:
```
[Interface]
Address = 10.8.0.4/32
PrivateKey = <CLIENT_PRIVATE_KEY>
DNS = 1.1.1.1

[Peer]
PublicKey = <SERVER_PUBLIC_KEY>
PresharedKey = <PRESHARED_KEY>
Endpoint = 178.209.119.86:51820
AllowedIPs = 10.8.0.0/24
PersistentKeepalive = 25
```

Запуск стека:
```bash
cd HOST_API_SERVICE
bash tools/ctl.sh up    # или up-testdb
```

Примечания:
- Требуется Linux‑хост (Docker с доступом к `/dev/net/tun`). На macOS поднять wg внутри контейнера не получится (используйте внешний WG‑клиент на хосте или разворачивайте на Linux).
- API и Traefik продолжают работать через `network_mode: "service:wg_vpn"` и `http://wg_vpn:<порт>`.
