#!/bin/bash
set -e

echo "🔧 Пересборка XML Workers с новыми путями"
echo "==========================================="
echo ""

cd /Users/ii/Documents/code/WG_HUB/wg_client

# Шаг 1: Создание структуры
echo "📁 Создание структуры директорий..."
mkdir -p /Users/ii/srv/btl/raw
mkdir -p /Users/ii/srv/btl/gz
echo "✅ Структура создана"
echo ""

# Шаг 2: Останов всех воркеров и api_mother
echo "🛑 Останов контейнеров..."
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml down
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml down api_mother
echo "✅ Контейнеры остановлены"
echo ""

# Шаг 3: Пересборка воркеров (БЕЗ кэша!)
echo "🔨 Пересборка XML Workers (может занять 2-3 минуты)..."
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml build --no-cache
echo "✅ Воркеры пересобраны"
echo ""

# Шаг 4: Пересборка api_mother
echo "🔨 Пересборка api_mother..."
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml build --no-cache api_mother
echo "✅ api_mother пересобран"
echo ""

# Шаг 5: Запуск
echo "🚀 Запуск контейнеров..."
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml up -d
sleep 5
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d api_mother
echo "✅ Контейнеры запущены"
echo ""

# Шаг 6: Проверка health
echo "🔍 Проверка здоровья воркеров..."
sleep 10
for i in {1..6}; do
    status=$(curl -s http://localhost:900$i/health 2>/dev/null || echo "error")
    if [[ "$status" == *"ok"* ]]; then
        echo "  ✅ Worker $i: OK"
    else
        echo "  ❌ Worker $i: FAILED"
    fi
done
echo ""

# Шаг 7: Проверка маунтов внутри контейнеров
echo "🔍 Проверка путей внутри контейнеров:"
echo ""
echo "Worker 1:"
docker exec xml_worker_1 ls -la /srv/btl/ 2>/dev/null || echo "  ❌ /srv/btl не существует"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Пересборка завершена!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Структура хранилища:"
echo "   /Users/ii/srv/btl/raw  → /srv/btl/raw  (в контейнерах)"
echo "   /Users/ii/srv/btl/gz   → /srv/btl/gz   (в контейнерах)"
echo ""
echo "🚀 Теперь можно запускать:"
echo "   curl -X POST 'http://localhost:8084/admin/xml-sync/fetch-old?count=100000&from_battle_id=3770000'"
echo ""






