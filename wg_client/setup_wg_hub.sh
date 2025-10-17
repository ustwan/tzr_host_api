#!/usr/bin/env bash
# Быстрая установка WG-Easy (VPN админка)
set -euo pipefail

echo "═══════════════════════════════════════════════════"
echo "  Установка WG-Easy (VPN веб-админка)"
echo "═══════════════════════════════════════════════════"
echo

# Определяем IP сервера
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "✅ Определен IP сервера: $SERVER_IP"

# Создаем структуру
echo "✅ Создание структуры WG_HUB..."
cd ..
mkdir -p WG_HUB_/wg-easy
cd WG_HUB_/wg-easy

# Создаем docker-compose.yml
echo "✅ Создание docker-compose.yml..."
cat > docker-compose.yml <<'EOF'
version: '3.8'

services:
  wg-easy:
    image: ghcr.io/wg-easy/wg-easy:latest
    container_name: wg-easy
    restart: unless-stopped
    
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1
    
    ports:
      - "51820:51820/udp"  # WireGuard VPN
      - "0.0.0.0:2019:51821/tcp"  # Веб-админка (доступна из LAN и VPN)
    
    environment:
      - WG_HOST=${WG_HOST}
      - PASSWORD_HASH='$2a$10$hBCoTLey1dPWk4DvWgdW/edRFhY20lKkjFdQGHA/6M2CvOFp.yP3u'
      - WG_PORT=51820
      - WG_DEFAULT_ADDRESS=10.8.0.x
      - WG_DEFAULT_DNS=1.1.1.1,8.8.8.8
      - WG_ALLOWED_IPS=10.8.0.0/24
      - WG_MTU=1420
      - WG_PERSISTENT_KEEPALIVE=25
    
    volumes:
      - wg-easy-data:/etc/wireguard
    
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  wg-easy-data:
EOF

# Создаем .env
echo "✅ Создание .env..."

cat > .env <<'EOF'
# IP сервера (для клиентов WireGuard)
WG_HOST=172.16.16.117

# Bcrypt хеш пароля "admin" (уже в кавычках!)
WG_PASSWORD_HASH='$2a$10$hBCoTLey1dPWk4DvWgdW/edRFhY20lKkjFdQGHA/6M2CvOFp.yP3u'
EOF

echo
echo "✅ Настройка IP forwarding..."
sysctl -w net.ipv4.ip_forward=1

echo
echo "✅ Запуск WG-Easy..."
docker compose up -d

echo
echo "✅ Ожидание запуска (5 секунд)..."
sleep 5

echo
echo "✅ Проверка статуса..."
docker ps | grep wg-easy

echo
echo "═══════════════════════════════════════════════════"
echo "  ✅ WG-EASY УСТАНОВЛЕН!"
echo "═══════════════════════════════════════════════════"
echo
echo "🌐 Веб-админка VPN:"
echo "  http://${SERVER_IP}:2019"
echo
echo "🔑 Пароль: admin"
echo
echo "⚠️  Для изменения пароля:"
echo "   1. Сгенерировать новый хеш:"
echo "      docker run -it ghcr.io/wg-easy/wg-easy wgpw 'ваш_пароль'"
echo "   2. Заменить в файле: WG_HUB_/wg-easy/.env"
echo "      WG_PASSWORD_HASH='новый_хеш'"
echo "   3. Перезапустить: docker restart wg-easy"
echo
echo "📋 Команды управления:"
echo "  cd wg_client"
echo "  sudo bash tools/ctl.sh wg-hub-status   # Статус"
echo "  sudo bash tools/ctl.sh wg-hub-logs     # Логи"
echo "  sudo bash tools/ctl.sh wg-hub-ui       # URL админки"
echo

