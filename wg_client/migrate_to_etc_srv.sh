#!/bin/bash
set -e

echo "🔄 Миграция хранилища логов в /etc/srv/btl"
echo "=============================================="
echo ""

# 1. Создаём директории
echo "📂 Шаг 1: Создаём директории в /etc/srv/btl..."
sudo mkdir -p /etc/srv/btl/raw /etc/srv/btl/gz
sudo chown -R $(whoami):staff /etc/srv/btl

echo "✅ Директории созданы"
ls -ld /etc/srv/btl /etc/srv/btl/raw /etc/srv/btl/gz

echo ""
echo "📋 Шаг 2: Копируем существующие логи..."
echo "   Источник: /Users/ii/srv/btl/"
echo "   Назначение: /etc/srv/btl/"
echo ""

if [ -d "/Users/ii/srv/btl/raw" ]; then
    FILE_COUNT=$(find /Users/ii/srv/btl/raw -name "*.tzb" -type f | wc -l | tr -d ' ')
    echo "   Найдено файлов в raw: $FILE_COUNT"
    
    if [ $FILE_COUNT -gt 0 ]; then
        echo "   Копируем..."
        sudo rsync -av --progress /Users/ii/srv/btl/raw/ /etc/srv/btl/raw/
        echo "   ✅ raw скопирован"
    fi
fi

if [ -d "/Users/ii/srv/btl/gz" ]; then
    GZ_COUNT=$(find /Users/ii/srv/btl/gz -name "*.gz" -type f | wc -l | tr -d ' ')
    echo "   Найдено файлов в gz: $GZ_COUNT"
    
    if [ $GZ_COUNT -gt 0 ]; then
        echo "   Копируем..."
        sudo rsync -av --progress /Users/ii/srv/btl/gz/ /etc/srv/btl/gz/
        echo "   ✅ gz скопирован"
    fi
fi

echo ""
echo "🔧 Шаг 3: Обновляем docker-compose файлы..."

# Изменяем маунты в файлах
sed -i '' 's|/Users/ii/srv/btl|/etc/srv/btl|g' HOST_API_SERVICE_HEAVY_WEIGHT_API.yml
sed -i '' 's|/Users/ii/srv/btl|/etc/srv/btl|g' HOST_API_SERVICE_LIGHT_WEIGHT_API.yml
sed -i '' 's|/Users/ii/srv/btl|/etc/srv/btl|g' HOST_API_SERVICE_XML_WORKERS.yml

echo "✅ Docker-compose файлы обновлены"

echo ""
echo "🔍 Шаг 4: Проверяем изменения..."
grep "srv/btl" HOST_API_SERVICE*.yml | head -10

echo ""
echo "🛑 Шаг 5: Останавливаем контейнеры..."
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml down
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml down
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml down

echo ""
echo "🚀 Шаг 6: Запускаем контейнеры с новыми маунтами..."
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml up -d
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d

echo ""
echo "⏳ Ждём запуска контейнеров (15 секунд)..."
sleep 15

echo ""
echo "✅ Шаг 7: Проверяем здоровье сервисов..."
curl -s http://localhost:9001/health | jq -c '{worker_1: .status}' || echo "Worker 1: не отвечает"
curl -s http://localhost:8083/healthz | jq -c '{api_mother: .status}' || echo "api_mother: не отвечает"
curl -s http://localhost:8084/healthz || echo "API_4: не отвечает"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 МИГРАЦИЯ ЗАВЕРШЕНА!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📂 Логи теперь хранятся в:"
echo "   - /etc/srv/btl/raw (несжатые)"
echo "   - /etc/srv/btl/gz (сжатые)"
echo ""
echo "🔍 Проверка:"
echo "   ls -l /etc/srv/btl/raw"
echo "   ls -l /etc/srv/btl/gz"
echo ""
echo "🧪 Тест загрузки боя:"
echo "   curl -X POST 'http://localhost:8084/admin/xml-sync/fetch-old?count=10&from_battle_id=3780000'"
echo ""





