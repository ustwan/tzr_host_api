#!/bin/bash

echo "=== 🔍 БЫСТРАЯ ПРОВЕРКА ВСЕХ API ==="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

test_endpoint() {
    local name=$1
    local url=$2
    echo -n "Testing $name... "
    response=$(curl -s -w "\n%{http_code}" "$url")
    code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$code" = "200" ]; then
        echo -e "${GREEN}✅ $code${NC}"
        echo "  Response: $body" | head -c 100
        echo ""
    else
        echo -e "${RED}❌ $code${NC}"
        echo "  Error: $body"
    fi
    echo ""
}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}1. API SERVICES${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

test_endpoint "API 1 (Server Status)" "http://localhost:1010/api/healthz"
test_endpoint "API 2 (Registration)" "http://localhost:1010/api/register/health"
test_endpoint "API Father (Main)" "http://localhost:1010/api/info/internal/health"
test_endpoint "API 4 (Analytics)" "http://localhost:1010/api/battle/health"
test_endpoint "API Mother (Files)" "http://localhost:1010/api/mother/healthz"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}2. FUNCTIONAL ENDPOINTS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -n "API Mother - File list... "
count=$(curl -s http://localhost:1010/api/mother/list | jq -r '.count')
echo -e "${GREEN}✅ $count файлов${NC}"
echo ""

echo -n "API Father - Constants... "
constants=$(curl -s http://localhost:1010/api/info/internal/constants 2>/dev/null)
if echo "$constants" | jq -e '.constants' >/dev/null 2>&1; then
    const_count=$(echo "$constants" | jq '.constants | length')
    echo -e "${GREEN}✅ $const_count констант${NC}"
else
    echo -e "${YELLOW}⚠️  Endpoint доступен, но данных нет${NC}"
fi
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}3. INFRASTRUCTURE${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

test_endpoint "Traefik Gateway" "http://localhost:1010/api/healthz"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}4. MONITORING DASHBOARDS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Доступны по адресам:"
echo "  • Portainer:    http://localhost:9100"
echo "  • Netdata:      http://localhost:9101"
echo "  • Dozzle:       http://localhost:9102"
echo "  • Uptime Kuma:  http://localhost:9103"
echo "  • Homarr:       http://localhost:9104"
echo "  • pgAdmin:      http://localhost:9105"
echo "  • Swagger UI:   http://localhost:9107"
echo "  • Filebrowser:  http://localhost:9108"
echo "  • ttyd:         http://localhost:9109"

echo ""
echo "=== ✅ ПРОВЕРКА ЗАВЕРШЕНА ==="
