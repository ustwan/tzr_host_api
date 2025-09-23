### WireGuard Hub in Docker (HOST_1)

Минимальный и безопасный WG-хаб на Docker для сети 10.8.0.0/24.

- **WG-хаб (HOST_1)**: 10.8.0.1/24
- **Клиент HOST_2**: 10.8.0.2/32
- **Порт**: UDP/51820 открыт снаружи
- **Конфиги/ключи**: /opt/wg-hub/config (вне образа, root-only)

#### Состав
- `opt/wg-hub/docker-compose.yml`
- `opt/wg-hub/config/wg0.conf` (шаблон)
- `scripts/install_host1.sh` (опциональная установка на HOST_1)

#### Требования (HOST_1 / Linux)
- /dev/net/tun доступен
- Открыт UDP/51820 на внешнем фаерволе/у провайдера
- Docker Engine + docker compose plugin

#### Быстрый старт (вручную)
1) Директории и права:
```bash
sudo mkdir -p /opt/wg-hub/config
sudo chown root:root /opt/wg-hub /opt/wg-hub/config
sudo chmod 700 /opt/wg-hub/config
```
2) Генерация ключей сервера:
```bash
cd /opt/wg-hub/config
umask 077
wg genkey | tee server.key | wg pubkey > server.pub
```
3) Скопируйте `opt/wg-hub/docker-compose.yml` → `/opt/wg-hub/` и `opt/wg-hub/config/wg0.conf` → `/opt/wg-hub/config/`.
4) Отредактируйте `/opt/wg-hub/config/wg0.conf`:
   - `PrivateKey = <HOST1_PRIVATE_KEY>` → содержимое `/opt/wg-hub/config/server.key`
   - `PublicKey = <HOST2_PUBLIC_KEY>` → публичный ключ HOST_2
5) Разрешите 51820/udp (если UFW):
```bash
if command -v ufw >/dev/null 2>&1; then sudo ufw allow 51820/udp && sudo ufw reload; fi
```
6) Запуск:
```bash
cd /opt/wg-hub
sudo docker compose up -d
sudo docker exec -it wg-hub wg show
```

#### NAT (опционально)
Чтобы клиенты выходили в интернет через HOST_1, раскомментируйте MASQUERADE в `wg0.conf` и укажите внешний интерфейс (например, `eth0`).

#### Клиент HOST_2
Используйте `/opt/wg-hub/config/server.pub` как `PublicKey` сервера на HOST_2. На обеих сторонах задавайте `AllowedIPs` максимально узко.
