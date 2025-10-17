#!/bin/bash
# Скрипт для полного запуска проекта с исправлениями

set -e

echo "🚀 Запуск проекта WG_HUB с исправлениями..."

# 1. Очистка Docker
echo "🧹 Очистка Docker..."
docker system prune -f
docker volume prune -f
docker network prune -f

# 2. Создание сетей
echo "🌐 Создание сетей..."
docker network create host-api-service_apinet || true
docker network create host-api-service_backnet || true
docker network create host-api-service_dbnet || true
docker network create monitoring || true

# 3. Запуск инфраструктуры
echo "🏗️ Запуск инфраструктуры..."
cd /Users/ii/Documents/code/WG_HUB/wg_client
docker compose -f HOST_API_SERVICE_INFRASTRUCTURE.yml up -d

# 4. Ожидание готовности БД
echo "⏳ Ожидание готовности БД..."
sleep 10

# 5. Применение миграций
echo "📊 Применение миграций БД..."
docker exec host-api-service-api_4_db-1 psql -U api4_user -d api4_battles -f /docker-entrypoint-initdb.d/V1__create_tables_complete.sql || {
    echo "Копируем миграцию в контейнер..."
    docker cp /Users/ii/Documents/code/WG_HUB/wg_client/api_4/migrations/V1__create_tables_complete.sql host-api-service-api_4_db-1:/tmp/
    docker exec host-api-service-api_4_db-1 psql -U api4_user -d api4_battles -f /tmp/V1__create_tables_complete.sql
}

# 6. Запуск API сервисов
echo "🔧 Запуск API сервисов..."
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d

# 7. Запуск мониторинга
echo "📊 Запуск мониторинга..."
docker compose -f HOST_API_SERVICE_MONITORING.yml up -d

# 8. Ожидание готовности сервисов
echo "⏳ Ожидание готовности сервисов..."
sleep 15

# 9. Проверка статуса
echo "✅ Проверка статуса сервисов..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 10. Тест API
echo "🧪 Тестирование API..."
curl -s http://127.0.0.1:1010/api/battles/list | jq . || echo "API 4 не готов"

echo "🎉 Проект запущен! Доступные сервисы:"
echo "  - API 4: http://127.0.0.1:1010/api/battles/list"
echo "  - API Mother: http://127.0.0.1:1010/api/mother/list"
echo "  - Portainer: http://127.0.0.1:9100"
echo "  - Netdata: http://127.0.0.1:19999"
echo "  - PgAdmin: http://127.0.0.1:5050"
echo "  - Swagger UI: http://127.0.0.1:8080"









