#!/bin/bash

echo "🧪 ПРОВЕРКА ВСЕХ ЭНДПОИНТОВ API_4"
echo "=================================="
echo ""

BASE_URL="http://localhost:8084"

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local expected_status=${4:-200}
    
    printf "%-50s" "$description..."
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" -H "Content-Type: application/json" 2>/dev/null)
    fi
    
    status=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}✅ OK${NC} ($status)"
    else
        echo -e "${RED}❌ FAIL${NC} (got $status, expected $expected_status)"
        echo "   Response: $(echo $body | head -c 100)"
    fi
}

echo "🏥 Health Checks:"
test_endpoint "GET" "/healthz" "Health check"
test_endpoint "GET" "/docs" "Swagger UI" "200"
echo ""

echo "📊 Analytics Endpoints:"
test_endpoint "GET" "/analytics/stats" "Global stats"
test_endpoint "GET" "/analytics/battles/player/TestPlayer?limit=10" "Player battles" "200"
test_endpoint "GET" "/analytics/meta/balance?days=30" "Meta balance"
test_endpoint "GET" "/analytics/meta/professions?days=30" "Professions stats"
test_endpoint "GET" "/analytics/players/top?limit=10" "Top players"
test_endpoint "GET" "/players/by-profession?profession=корсар&limit=10" "Players by profession"
echo ""

echo "🔍 Battle Endpoints:"
test_endpoint "GET" "/battle/3770049" "Battle metadata"
test_endpoint "GET" "/battle/3770049/raw" "Battle raw XML"
echo ""

echo "🎯 Search Endpoints:"
test_endpoint "POST" "/battle/search" "Battle search"
echo ""

echo "⏱️ Time Analytics:"
test_endpoint "GET" "/analytics/time/activity-heatmap?days=7" "Activity heatmap"
test_endpoint "GET" "/analytics/time/peak-hours?days=7" "Peak hours"
echo ""

echo "🗺️ Map Analytics:"
test_endpoint "GET" "/analytics/map/heatmap?days=7" "Map heatmap"
echo ""

echo "=================================="
echo "✅ Проверка завершена"




