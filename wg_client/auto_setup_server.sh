#!/usr/bin/env bash
# Автоматическая настройка и запуск TZR Host API на сервере
set -euo pipefail

echo "═══════════════════════════════════════════════════"
echo "  TZR Host API - Автоматическая установка"
echo "═══════════════════════════════════════════════════"
echo

# Проверка что мы в правильной директории
if [[ ! -f "tools/ctl.sh" ]]; then
    echo "❌ Ошибка: запустите из директории wg_client/"
    exit 1
fi

echo "✅ Шаг 1: Обновление с GitHub..."
cd ..
git pull origin main
cd wg_client

echo
echo "✅ Шаг 2: Настройка IP forwarding (для VPN)..."
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv4.conf.all.forwarding=1
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf 2>/dev/null || true

echo
echo "✅ Шаг 3: Настройка iptables (VPN → API)..."
iptables -A INPUT -i wg0 -j ACCEPT 2>/dev/null || true
iptables -A FORWARD -i wg0 -j ACCEPT 2>/dev/null || true
iptables -A FORWARD -o wg0 -j ACCEPT 2>/dev/null || true

# Сохранить правила (если установлен iptables-persistent)
if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save
fi

echo
echo "✅ Шаг 4: Остановка старых контейнеров..."
bash tools/ctl.sh stop-all 2>/dev/null || true

echo
echo "✅ Шаг 5: Пересборка образов..."
bash tools/ctl.sh rebuild

echo
echo "✅ Шаг 6: Запуск всех сервисов..."
bash tools/ctl.sh start-all

echo
echo "✅ Шаг 7: Ожидание запуска (10 секунд)..."
sleep 10

echo
echo "✅ Шаг 8: Проверка статуса..."
bash tools/ctl.sh status

echo
echo "═══════════════════════════════════════════════════"
echo "  ✅ УСТАНОВКА ЗАВЕРШЕНА!"
echo "═══════════════════════════════════════════════════"
echo
echo "📊 Доступные админки:"
echo "  http://$(hostname -I | awk '{print $1}'):9100  - Portainer (Docker)"
echo "  http://$(hostname -I | awk '{print $1}'):9102  - Dozzle (Логи)"
echo "  http://$(hostname -I | awk '{print $1}'):9107  - Swagger (API)"
echo "  http://$(hostname -I | awk '{print $1}'):2019  - WG-Easy (VPN)"
echo
echo "🌐 Из VPN (после подключения):"
echo "  http://10.8.0.1:9100  - Portainer"
echo "  http://10.8.0.1:9107  - Swagger"
echo "  http://10.8.0.1:8082  - API_2"
echo
echo "📋 Полезные команды:"
echo "  sudo bash tools/ctl.sh status       - статус"
echo "  sudo bash tools/ctl.sh logs         - логи"
echo "  sudo bash tools/ctl.sh update       - обновить"
echo

