#!/bin/bash
set -e

echo "🔧 Пересборка API_4 с критическими исправлениями"
echo "=================================================="
echo ""
echo "📋 Что исправлено:"
echo "  1. ✅ Round-robin распределение батчей между воркерами"
echo "  2. ✅ storage_key: /srv/btl/raw вместо /tmp/tmpXXX.tzb"
echo "  3. ✅ Увеличен лимит count до 1,000,000"
echo ""

cd /Users/ii/Documents/code/WG_HUB/wg_client

echo "🛑 Останавливаю API_4..."
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml down api_4

echo ""
echo "🔨 Пересборка API_4 (без кэша)..."
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml build --no-cache api_4

echo ""
echo "🚀 Запуск API_4..."
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d api_4

echo ""
echo "⏳ Ожидание запуска (15 секунд)..."
sleep 15

echo ""
echo "🔍 Проверка здоровья API_4:"
curl -s http://localhost:8084/health | jq -c '.' || echo "❌ API_4 не отвечает"

echo ""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Пересборка завершена!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 БЫСТРЫЙ ТЕСТ (600 боёв = все 6 воркеров):"
echo ""
echo "curl -X POST 'http://localhost:8084/admin/xml-sync/fetch-old?count=600&from_battle_id=3770000'"
echo ""
echo "📊 МОНИТОРИНГ (в другом терминале):"
echo ""
echo "watch -n 1 'for i in {1..6}; do echo -n \"Worker \$i: \"; docker logs xml_worker_\$i 2>&1 | grep \"✓\" | tail -1; done'"
echo ""
echo "🎯 ДЛЯ 100K БОЁВ:"
echo ""
echo "curl -X POST 'http://localhost:8084/admin/xml-sync/fetch-old?count=100000&from_battle_id=3770000&auto_parse=true&max_parallel=10'"
echo ""
echo "🔍 ПРОВЕРКА storage_key после теста:"
echo ""
echo "curl -s 'http://localhost:8084/battle/3770000' | jq '{battle_id, storage_key, sha256}'"
echo ""


