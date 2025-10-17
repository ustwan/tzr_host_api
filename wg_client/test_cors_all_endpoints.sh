#!/bin/bash

echo "🔍 ПОЛНАЯ ПРОВЕРКА CORS ДЛЯ ВСЕХ ЭНДПОИНТОВ"
echo "============================================="
echo ""

BASE_URL="http://localhost:8084"
ORIGIN="http://localhost:9107"

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_cors() {
    local endpoint=$1
    local description=$2
    
    printf "%-60s" "$description..."
    
    # Проверяем CORS preflight (OPTIONS)
    preflight=$(curl -s -X OPTIONS "$BASE_URL$endpoint" \
        -H "Origin: $ORIGIN" \
        -H "Access-Control-Request-Method: GET" \
        -w "\n%{http_code}" 2>/dev/null)
    
    preflight_status=$(echo "$preflight" | tail -n1)
    preflight_cors=$(echo "$preflight" | grep -i "access-control-allow-origin" | head -1)
    
    # Проверяем GET запрос
    get_response=$(curl -s -X GET "$BASE_URL$endpoint" \
        -H "Origin: $ORIGIN" \
        -H "Accept: application/json" \
        -w "\n%{http_code}" 2>/dev/null)
    
    get_status=$(echo "$get_response" | tail -n1)
    get_cors=$(echo "$get_response" | grep -i "access-control-allow-origin" | head -1)
    
    # Анализ результатов
    if [ "$preflight_status" = "200" ] && [ "$get_status" = "200" ]; then
        echo -e "${GREEN}✅ OK${NC} (GET: $get_status, OPTIONS: $preflight_status)"
    elif [ "$get_status" = "200" ]; then
        echo -e "${YELLOW}⚠️  OK${NC} (GET: $get_status, OPTIONS: $preflight_status)"
    else
        echo -e "${RED}❌ FAIL${NC} (GET: $get_status, OPTIONS: $preflight_status)"
    fi
}

echo "📊 Базовые эндпоинты:"
test_cors "/healthz" "Health check"
test_cors "/docs" "Swagger UI"
test_cors "/openapi.json" "OpenAPI Schema"
echo ""

echo "📊 Analytics эндпоинты:"
test_cors "/analytics/stats" "Global stats"
test_cors "/analytics/battles/player/TestPlayer?limit=10" "Player battles"
test_cors "/analytics/meta/balance?days=30" "Meta balance"
test_cors "/analytics/meta/professions?days=30" "Professions stats"
test_cors "/analytics/players/top?limit=10" "Top players"
test_cors "/analytics/time/activity-heatmap?days=7" "Activity heatmap"
test_cors "/analytics/time/peak-hours?days=7" "Peak hours"
test_cors "/analytics/map/heatmap?days=7" "Map heatmap"
echo ""

echo "🔍 Battle эндпоинты:"
test_cors "/battle/3330200" "Battle metadata"
test_cors "/battle/3330200/raw" "Battle raw XML"
echo ""

echo "👥 Player эндпоинты:"
test_cors "/players/by-profession?profession=корсар&limit=10" "Players by profession"
echo ""

echo "============================================="
echo ""

# Проверка CORS заголовков
echo "🔍 Проверка CORS заголовков:"
response=$(curl -v -X GET "$BASE_URL/healthz" -H "Origin: $ORIGIN" 2>&1)

echo "$response" | grep -i "access-control-allow-origin" | head -1 | sed 's/^/   /'
echo "$response" | grep -i "access-control-allow-credentials" | head -1 | sed 's/^/   /'
echo "$response" | grep -i "access-control-allow-methods" | head -1 | sed 's/^/   /'

echo ""
echo "✅ Проверка завершена"




