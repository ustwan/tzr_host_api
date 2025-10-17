#!/bin/bash
set -e

echo "=== 🧪 E2E TEST: Полный поток данных ==="
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}ℹ️  INFO${NC}: $1"; }

# 1. Проверка mock_btl_rsyncd
info "Тест 1: mock_btl_rsyncd (HOST_SERVER)"
rsync rsync://localhost:873/ | grep -q "btl" && pass "Rsync сервер доступен" || fail "Rsync сервер недоступен"

FILE_COUNT=$(docker exec wg_client-mock_btl_rsyncd-1 find /srv/export/btl -name "*.tzb" -type f | wc -l | tr -d ' ')
[ "$FILE_COUNT" -gt 100 ] && pass "Логов на сервере: $FILE_COUNT" || fail "Недостаточно логов: $FILE_COUNT"

# 2. Проверка btl_syncer
info "Тест 2: btl_syncer (синхронизация)"
MIRROR_COUNT=$(find xml/mirror -name "*.tzb" -type f 2>/dev/null | wc -l | tr -d ' ')
[ "$MIRROR_COUNT" -gt 100 ] && pass "Файлов в зеркале: $MIRROR_COUNT" || fail "Зеркало пустое: $MIRROR_COUNT"

# 3. Проверка btl_compressor
info "Тест 3: btl_compressor (сжатие + шардирование)"
GZ_COUNT=$(find xml/gz -name "*.gz" -type f 2>/dev/null | wc -l | tr -d ' ')
[ "$GZ_COUNT" -gt 100 ] && pass "Сжатых файлов: $GZ_COUNT" || fail "Недостаточно сжатых файлов: $GZ_COUNT"

SHARD_DIRS=$(find xml/gz -mindepth 2 -type d 2>/dev/null | wc -l | tr -d ' ')
[ "$SHARD_DIRS" -gt 0 ] && pass "Шардированных директорий: $SHARD_DIRS" || fail "Шардирование не работает"

# 4. Проверка api_mother
info "Тест 4: api_mother (HTTP API)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:1010/api/mother/healthz)
[ "$HTTP_CODE" = "200" ] && pass "API Mother healthcheck: $HTTP_CODE" || fail "API Mother недоступен: $HTTP_CODE"

# 5. Проверка api_4
info "Тест 5: api_4 (Analytics API)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:1010/api/battle/health)
[ "$HTTP_CODE" = "200" ] && pass "API 4 healthcheck: $HTTP_CODE" || fail "API 4 недоступен: $HTTP_CODE"

# 6. Проверка Traefik
info "Тест 6: Traefik (Gateway)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:1010/api/healthz)
[ "$HTTP_CODE" = "200" ] && pass "Traefik работает: $HTTP_CODE" || fail "Traefik недоступен: $HTTP_CODE"

echo ""
echo "=== 🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ ==="
echo ""
echo "📊 Статистика:"
echo "  • Mock сервер: ✅ $FILE_COUNT файлов"
echo "  • Синхронизация: ✅ $MIRROR_COUNT файлов"  
echo "  • Сжатие: ✅ $GZ_COUNT файлов"
echo "  • Шардирование: ✅ $SHARD_DIRS директорий"
echo "  • API Mother: ✅ доступен"
echo "  • API 4: ✅ доступен"
echo "  • Traefik: ✅ работает"
