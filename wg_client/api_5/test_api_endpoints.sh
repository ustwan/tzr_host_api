#!/usr/bin/env bash
# Тестирование всех API endpoints API 5

echo "🧪 API 5 - Тестирование всех endpoints"
echo "========================================"
echo ""

API_URL="http://localhost:8085"

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${method} ${endpoint}${NC}"
    echo -e "${YELLOW}${description}${NC}"
    echo ""
    
    if [ "$method" = "GET" ]; then
        echo "$ curl ${API_URL}${endpoint}"
        echo ""
        curl -s "${API_URL}${endpoint}" | python3 -m json.tool 2>/dev/null || curl -s "${API_URL}${endpoint}"
    else
        echo "$ curl -X ${method} ${API_URL}${endpoint}"
        echo ""
        curl -s -X "${method}" "${API_URL}${endpoint}" ${data} | python3 -m json.tool 2>/dev/null || curl -s -X "${method}" "${API_URL}${endpoint}" ${data}
    fi
    
    echo ""
    echo ""
}

# Проверка что API запущен
echo "🔍 Проверка доступности API..."
if ! curl -s "${API_URL}/healthz" > /dev/null 2>&1; then
    echo "❌ API не запущен на ${API_URL}"
    echo ""
    echo "Запустите API:"
    echo "  cd /Users/ii/Documents/code/WG_HUB/wg_client/api_5"
    echo "  python app/main.py"
    echo ""
    exit 1
fi

echo "✅ API доступен"
echo ""

# ========== HEALTH ENDPOINTS ==========
echo "═══════════════════════════════════════════════════════"
echo "🏥 HEALTH & SERVICE ENDPOINTS (3 шт)"
echo "═══════════════════════════════════════════════════════"
echo ""

test_endpoint "GET" "/healthz" \
    "Проверка работоспособности сервиса"

test_endpoint "GET" "/shop/health" \
    "Проверка работоспособности модуля магазина"

test_endpoint "GET" "/db/health" \
    "Проверка подключения к БД"

# ========== ITEMS ENDPOINTS ==========
echo "═══════════════════════════════════════════════════════"
echo "📦 ITEMS ENDPOINTS (3 шт)"
echo "═══════════════════════════════════════════════════════"
echo ""

test_endpoint "GET" "/items/list?limit=5" \
    "Список товаров (первые 5)"

test_endpoint "GET" "/items/list?shop_code=moscow&limit=3" \
    "Список товаров магазина Moscow (3 шт)"

test_endpoint "GET" "/items/79469641" \
    "Детали товара по ID (если есть в БД)"

# ========== SNAPSHOTS ENDPOINTS ==========
echo "═══════════════════════════════════════════════════════"
echo "📸 SNAPSHOTS ENDPOINTS (2 шт)"
echo "═══════════════════════════════════════════════════════"
echo ""

test_endpoint "GET" "/snapshots/list" \
    "Список всех снимков"

test_endpoint "GET" "/snapshots/latest?shop_code=moscow" \
    "Последний снимок магазина Moscow"

# ========== ADMIN ENDPOINTS ==========
echo "═══════════════════════════════════════════════════════"
echo "👑 ADMIN ENDPOINTS (2 шт)"
echo "═══════════════════════════════════════════════════════"
echo ""

test_endpoint "GET" "/admin/bots/status" \
    "Статус всех ботов-парсеров"

test_endpoint "POST" "/admin/snapshot/trigger?shop_code=moscow" \
    "Запустить создание снимка вручную (Moscow)"

# ========== SWAGGER ==========
echo "═══════════════════════════════════════════════════════"
echo "📚 SWAGGER UI"
echo "═══════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}GET /docs${NC}"
echo -e "${YELLOW}Интерактивная документация API (Swagger UI)${NC}"
echo ""
echo "Открыть в браузере:"
echo "  open ${API_URL}/docs"
echo ""

# ========== ИТОГИ ==========
echo "═══════════════════════════════════════════════════════"
echo "✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Протестировано endpoints: 10"
echo ""
echo "Категории:"
echo "  🏥 Health & Service: 3"
echo "  📦 Items: 3"
echo "  📸 Snapshots: 2"
echo "  👑 Admin: 2"
echo ""







