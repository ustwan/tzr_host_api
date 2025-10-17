#!/usr/bin/env bash
# Скрипт для настройки мониторов в Uptime Kuma
set -euo pipefail

KUMA_URL=${KUMA_URL:-http://localhost:9103}
KUMA_USER=${KUMA_USER:-admin}
KUMA_PASS=${KUMA_PASS:-admin123}

echo "=== Настройка Uptime Kuma ==="
echo "URL: $KUMA_URL"
echo ""

# Примечание: Uptime Kuma требует ручной настройки через веб-интерфейс
# или использования неофициального API
# Этот скрипт создает конфигурационный файл для справки

cat > /tmp/uptime_kuma_monitors.json <<'EOF'
{
  "monitors": [
    {
      "name": "API 1 - Server Status",
      "type": "http",
      "url": "http://api_1:8081/healthz",
      "interval": 60,
      "maxretries": 3,
      "retryInterval": 60
    },
    {
      "name": "API 2 - Registration",
      "type": "http",
      "url": "http://api_2:8082/healthz",
      "interval": 60,
      "maxretries": 3,
      "retryInterval": 60
    },
    {
      "name": "API Father - Main",
      "type": "http",
      "url": "http://api_father:9000/healthz",
      "interval": 60,
      "maxretries": 3,
      "retryInterval": 60
    },
    {
      "name": "API 4 - Analytics",
      "type": "http",
      "url": "http://api_4:8084/healthz",
      "interval": 60,
      "maxretries": 3,
      "retryInterval": 60
    },
    {
      "name": "API Mother - File Handler",
      "type": "http",
      "url": "http://api_mother:8083/healthz",
      "interval": 60,
      "maxretries": 3,
      "retryInterval": 60
    },
    {
      "name": "Traefik - API Gateway",
      "type": "http",
      "url": "http://traefik:1010/api/healthz",
      "interval": 60,
      "maxretries": 3,
      "retryInterval": 60
    },
    {
      "name": "MySQL - Game DB",
      "type": "mysql",
      "hostname": "db",
      "port": 3306,
      "database": "gamedb",
      "interval": 120
    },
    {
      "name": "PostgreSQL - API 4 DB",
      "type": "postgres",
      "hostname": "api_4_db",
      "port": 5432,
      "database": "api4_battles",
      "interval": 120
    },
    {
      "name": "Redis - Father Cache",
      "type": "redis",
      "hostname": "api_father_redis",
      "port": 6379,
      "interval": 120
    },
    {
      "name": "Mock DB Bridge",
      "type": "port",
      "hostname": "mock_db_bridge",
      "port": 3307,
      "interval": 120
    },
    {
      "name": "Mock Rsync Server",
      "type": "port",
      "hostname": "mock_btl_rsyncd",
      "port": 873,
      "interval": 120
    }
  ]
}
EOF

echo "✅ Конфигурация мониторов создана: /tmp/uptime_kuma_monitors.json"
echo ""
echo "📋 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ:"
echo ""
echo "1. Откройте Uptime Kuma: http://localhost:9103"
echo "2. Создайте аккаунт администратора (если первый запуск)"
echo "3. Добавьте мониторы вручную со следующими параметрами:"
echo ""
echo "   📊 API сервисы (HTTP):"
echo "   • API 1: http://host-api-service-api_1-1:8081/healthz"
echo "   • API 2: http://host-api-service-api_2-1:8082/healthz"
echo "   • API Father: http://host-api-service-api_father-1:9000/healthz"
echo "   • API 4: http://host-api-service-api_4-1:8084/healthz"
echo "   • API Mother: http://host-api-service-api_mother-1:8083/healthz"
echo "   • Traefik: http://host-api-service-traefik-1:1010/api/healthz"
echo ""
echo "   🗄️  Базы данных:"
echo "   • MySQL: host-api-service-db-1:3306"
echo "   • PostgreSQL: host-api-service-api_4_db-1:5432"
echo "   • Redis: host-api-service-api_father_redis-1:6379"
echo ""
echo "   🔧 Mock сервисы (TCP Port):"
echo "   • DB Bridge: wg_client-mock_db_bridge-1:3307"
echo "   • Rsync: wg_client-mock_btl_rsyncd-1:873"
echo ""
echo "4. Настройте уведомления (Discord, Telegram, Email)"
echo "5. Создайте Status Page для публичного отображения"
echo ""

cat /tmp/uptime_kuma_monitors.json











