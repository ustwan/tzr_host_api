#!/bin/bash

echo "🧪 Быстрый тест дашбордов WG_HUB Visualization"
echo "================================================"
echo ""

echo "✅ 1. Проверка контейнера..."
docker ps | grep wg_visualization && echo "   Контейнер запущен ✅" || echo "   ❌ Контейнер не запущен!"
echo ""

echo "✅ 2. Проверка API4..."
curl -s -o /dev/null -w "   HTTP %{http_code}" http://localhost:8084/analytics/map/heatmap
echo " → API4 доступен ✅"
echo ""

echo "✅ 3. Проверка прокси..."
curl -s -o /dev/null -w "   HTTP %{http_code}" http://localhost:14488/api/analytics/map/heatmap
echo " → Прокси работает ✅"
echo ""

echo "✅ 4. Тест endpoints:"
echo ""
echo "   Analytics Heatmap:      $(curl -s http://localhost:14488/api/analytics/map/heatmap | jq 'length') точек"
echo "   Clan Control:           $(curl -s http://localhost:14488/api/analytics/map/clan-control | jq 'length') кланов"
echo "   Churn Prediction:       $(curl -s http://localhost:14488/api/analytics/predictions/churn | jq 'length') игроков"
echo "   PvE Top Locations:      $(curl -s http://localhost:14488/api/analytics/pve/top-locations | jq 'length') локаций"
echo "   PvP Hotspots:           $(curl -s http://localhost:14488/api/analytics/map/pvp-hotspots | jq 'length') точек"
echo ""

echo "================================================"
echo "🌐 Откройте в браузере:"
echo ""
echo "   http://localhost:14488"
echo ""
echo "✅ Рекомендованные дашборды для теста:"
echo ""
echo "   1. Analytics Heatmap:"
echo "      http://localhost:14488/analytics-heatmap.html"
echo ""
echo "   2. Clan Control:"
echo "      http://localhost:14488/analytics-clan-control.html"
echo ""
echo "   3. Churn Prediction:"
echo "      http://localhost:14488/analytics-churn.html"
echo ""
echo "================================================"
echo "✨ Готово к использованию! 🚀"
echo ""
