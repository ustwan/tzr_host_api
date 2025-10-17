#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}ℹ️  INFO${NC}: $1"; }

echo "=== 🧪 E2E TEST: API Mother Endpoints ==="
echo ""

# Тест 1: /api/mother/list
info "Тест 1: GET /api/mother/list"
COUNT=$(curl -s http://localhost:1010/api/mother/list | jq -r '.count')
[ "$COUNT" -gt 100 ] && pass "Список файлов: $COUNT файлов" || fail "Список пустой: $COUNT"

# Тест 2: /api/mother/gz/{path}
info "Тест 2: GET /api/mother/gz/{path}"
curl -s http://localhost:1010/api/mother/gz/30/1500000.tzb -o /tmp/test_api_mother.gz
[ -f /tmp/test_api_mother.gz ] && pass "Файл скачан" || fail "Файл не скачан"

gunzip -t /tmp/test_api_mother.gz 2>/dev/null && pass "Файл корректный gzip" || fail "Файл поврежден"

SIZE=$(stat -f%z /tmp/test_api_mother.gz 2>/dev/null || stat -c%s /tmp/test_api_mother.gz)
[ "$SIZE" -gt 100 ] && pass "Размер файла: $SIZE байт" || fail "Файл слишком маленький: $SIZE"

# Тест 3: /api/mother/sync
info "Тест 3: POST /api/mother/sync"
RESPONSE=$(curl -s -X POST http://localhost:1010/api/mother/sync)
echo "$RESPONSE" | grep -q "sync scheduled" && pass "Sync endpoint работает" || fail "Sync endpoint не работает"

# Тест 4: /api/mother/healthz
info "Тест 4: GET /api/mother/healthz"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:1010/api/mother/healthz)
[ "$HTTP_CODE" = "200" ] && pass "Health check: $HTTP_CODE" || fail "Health check failed: $HTTP_CODE"

echo ""
echo "=== 🎉 ВСЕ ТЕСТЫ API MOTHER ПРОЙДЕНЫ ==="
