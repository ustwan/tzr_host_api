#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; }
info() { echo -e "${YELLOW}ℹ️${NC} $1"; }
header() { echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${YELLOW}$1${NC}"; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

echo ""
header "🧪 ПОЛНОЕ ТЕСТИРОВАНИЕ ВСЕХ API"
echo ""

# API 1 - Server Status
header "1️⃣  API 1 - Server Status"
echo ""

info "GET /api/healthz"
RESPONSE=$(curl -s http://localhost:1010/api/healthz)
echo "$RESPONSE" | grep -q "ok" && pass "Health check работает" || fail "Health check не работает"

info "GET /api/server/status"
STATUS=$(curl -s http://localhost:1010/api/server/status)
echo "$STATUS" | jq -e '.server_status' >/dev/null 2>&1 && pass "Получен server_status" || fail "Нет server_status"
echo "$STATUS" | jq -e '.rates.exp' >/dev/null 2>&1 && pass "Получены rates" || fail "Нет rates"

SERVER_STATUS=$(echo "$STATUS" | jq -r '.server_status')
echo "  • Server Status: $SERVER_STATUS"
echo "  • Rate Exp: $(echo "$STATUS" | jq -r '.rates.exp')"
echo "  • Rate PVP: $(echo "$STATUS" | jq -r '.rates.pvp')"
echo ""

# API 2 - Registration
header "2️⃣  API 2 - Registration"
echo ""

info "GET /api/register/health"
RESPONSE=$(curl -s http://localhost:1010/api/register/health)
echo "$RESPONSE" | grep -q "ok" && pass "Health check работает" || fail "Health check не работает"

info "POST /api/register (проверка валидации)"
RESPONSE=$(curl -s -X POST http://localhost:1010/api/register \
  -H "Content-Type: application/json" \
  -d '{"login":"ab"}')
echo "$RESPONSE" | jq -e '.fields.login' >/dev/null 2>&1 && pass "Валидация login работает" || fail "Валидация не работает"
echo ""

# API Father - Main
header "3️⃣  API Father - Main Aggregator"
echo ""

info "GET /api/info/internal/health"
RESPONSE=$(curl -s http://localhost:1010/api/info/internal/health)
echo "$RESPONSE" | grep -q "ok" && pass "Health check работает" || fail "Health check не работает"
REDIS_STATUS=$(echo "$RESPONSE" | jq -r '.details.redis')
echo "  • Redis: $REDIS_STATUS"

info "GET /api/info/internal/constants"
CONSTANTS=$(curl -s http://localhost:1010/api/info/internal/constants)
COUNT=$(echo "$CONSTANTS" | jq 'length')
[ "$COUNT" -ge 5 ] && pass "Получено $COUNT констант" || fail "Недостаточно констант: $COUNT"
echo ""

# API 4 - Analytics
header "4️⃣  API 4 - Battle Analytics"
echo ""

info "GET /api/battle/health"
RESPONSE=$(curl -s http://localhost:1010/api/battle/health)
echo "$RESPONSE" | grep -q "ok" && pass "Health check работает" || fail "Health check не работает"

info "GET /api/analytics/health"
RESPONSE=$(curl -s http://localhost:1010/api/analytics/health)
echo "$RESPONSE" | grep -q "ok" && pass "Analytics health работает" || fail "Analytics health не работает"
echo ""

# API Mother - File Handler
header "5️⃣  API Mother - File Handler"
echo ""

info "GET /api/mother/healthz"
RESPONSE=$(curl -s http://localhost:1010/api/mother/healthz)
echo "$RESPONSE" | grep -q "ok" && pass "Health check работает" || fail "Health check не работает"

info "GET /api/mother/list"
FILES=$(curl -s http://localhost:1010/api/mother/list)
COUNT=$(echo "$FILES" | jq -r '.count')
[ "$COUNT" -gt 100 ] && pass "Файлов доступно: $COUNT" || fail "Мало файлов: $COUNT"

info "GET /api/mother/gz/{path} (скачивание файла)"
curl -s http://localhost:1010/api/mother/gz/30/1500000.tzb -o /tmp/test_download.gz
if [ -f /tmp/test_download.gz ]; then
    SIZE=$(stat -f%z /tmp/test_download.gz 2>/dev/null || stat -c%s /tmp/test_download.gz)
    if [ "$SIZE" -gt 100 ]; then
        gunzip -t /tmp/test_download.gz 2>/dev/null && pass "Файл скачан ($SIZE байт) и валиден" || fail "Файл поврежден"
    else
        fail "Файл слишком маленький: $SIZE байт"
    fi
else
    fail "Файл не скачан"
fi

info "POST /api/mother/sync"
RESPONSE=$(curl -s -X POST http://localhost:1010/api/mother/sync)
echo "$RESPONSE" | grep -q "sync scheduled" && pass "Sync endpoint работает" || fail "Sync не работает"
echo ""

# Infrastructure
header "6️⃣  Infrastructure"
echo ""

info "Traefik Gateway"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:1010/api/healthz)
[ "$HTTP_CODE" = "200" ] && pass "Traefik работает: $HTTP_CODE" || fail "Traefik недоступен: $HTTP_CODE"
echo ""

# Summary
header "📊 ИТОГОВАЯ СТАТИСТИКА"
echo ""
echo "API Сервисов: 5"
echo "Константов в БД: $COUNT"
echo "Файлов доступно: $(echo "$FILES" | jq -r '.count')"
echo "Server Status: $SERVER_STATUS"
echo "Redis: $REDIS_STATUS"
echo ""
echo "=== 🎉 ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ ==="
echo ""
