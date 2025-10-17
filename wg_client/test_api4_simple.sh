#!/bin/bash

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🔍 ПРОВЕРКА API 4${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

BASE="http://localhost"

# 1. Health
echo -e "${YELLOW}1. Health check${NC}"
curl -s "$BASE/api/battle/healthz" | jq -C . 2>/dev/null || curl -s "$BASE/api/battle/healthz"
echo -e "\n"

# 2. List battles (может быть пустой)
echo -e "${YELLOW}2. Список боев${NC}"
curl -s "$BASE/api/battle/list?page=1&limit=5" | jq -C . 2>/dev/null || curl -s "$BASE/api/battle/list?page=1&limit=5"
echo -e "\n"

# 3. Search (может быть пустой)
echo -e "${YELLOW}3. Поиск боев${NC}"
curl -s "$BASE/api/battle/search?limit=5" | jq -C . 2>/dev/null || curl -s "$BASE/api/battle/search?limit=5"
echo -e "\n"

# 4. Sync (запустит синхронизацию)
echo -e "${YELLOW}4. Синхронизация${NC}"
curl -s -X POST "$BASE/api/sync" | jq -C . 2>/dev/null || curl -s -X POST "$BASE/api/sync"
echo -e "\n"

# 5. Stats
echo -e "${YELLOW}5. Общая статистика${NC}"
curl -s "$BASE/api/analytics/stats?days=30" | jq -C . 2>/dev/null || curl -s "$BASE/api/analytics/stats?days=30"
echo -e "\n"

# 6. Anomalies
echo -e "${YELLOW}6. Аномалии${NC}"
curl -s "$BASE/api/analytics/anomalies?days=7" | jq -C . 2>/dev/null || curl -s "$BASE/api/analytics/anomalies?days=7"
echo -e "\n"

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Проверка завершена${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"
