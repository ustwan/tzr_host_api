#!/bin/bash
set -e

echo "🔧 Миграция централизованного хранилища логов"
echo "=============================================="
echo ""

# Шаг 1: Создание структуры
echo "📁 Создание структуры директорий..."
mkdir -p /Users/ii/srv/btl/raw
mkdir -p /Users/ii/srv/btl/gz

echo "✅ Структура создана"
echo ""

# Шаг 2: Останов контейнеров
echo "🛑 Останов контейнеров..."
cd /Users/ii/Documents/code/WG_HUB/wg_client

docker compose -f HOST_API_SERVICE_XML_WORKERS.yml down || true
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml down api_mother || true
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml down api_4 || true

echo "✅ Контейнеры остановлены"
echo ""

# Шаг 3: Перенос существующих файлов (если есть)
echo "📦 Проверка старых файлов..."

if [ -d "/Users/ii/srv/btl_raw" ]; then
    echo "Перенос из /Users/ii/srv/btl_raw..."
    rsync -av /Users/ii/srv/btl_raw/ /Users/ii/srv/btl/raw/ || true
fi

if [ -d "./xml/gz" ]; then
    echo "Перенос из ./xml/gz..."
    rsync -av ./xml/gz/ /Users/ii/srv/btl/gz/ || true
fi

echo "✅ Файлы перенесены"
echo ""

# Шаг 4: Пересборка контейнеров
echo "🔨 Пересборка контейнеров..."
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml build
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml build api_mother

echo "✅ Контейнеры пересобраны"
echo ""

# Шаг 5: Запуск контейнеров
echo "🚀 Запуск контейнеров..."
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml up -d
sleep 5
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d api_mother
sleep 5
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d api_4

echo "✅ Контейнеры запущены"
echo ""

# Шаг 6: Проверка
echo "🔍 Проверка структуры:"
echo ""
echo "Raw файлы:"
ls -lah /Users/ii/srv/btl/raw/ | head -10 || echo "  (пусто)"
echo ""
echo "GZ файлы:"
ls -lah /Users/ii/srv/btl/gz/ | head -10 || echo "  (пусто)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Миграция завершена!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Централизованное хранилище:"
echo "   /Users/ii/srv/btl/raw  - сырые .tzb файлы"
echo "   /Users/ii/srv/btl/gz   - сжатые .gz файлы"
echo ""
echo "🔗 Маунты:"
echo "   XML Workers → /srv/btl/raw"
echo "   api_mother  → /srv/btl (raw + gz)"
echo "   API_4       → /srv/btl (read-only)"
echo ""






