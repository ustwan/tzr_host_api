#!/bin/bash

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🔍 ПРОВЕРКА ВСЕХ ENDPOINT API 4${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

BASE_URL="http://localhost"

# Счетчики
TOTAL=0
SUCCESS=0
FAILED=0

# Функция для проверки endpoint
check_endpoint() {
    local method=$1
    local path=$2
    local description=$3
    local data=$4
    
    TOTAL=$((TOTAL + 1))
    
    echo -e "${YELLOW}[$TOTAL] ${description}${NC}"
    echo -e "${BLUE}   ${method} ${path}${NC}"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "${BASE_URL}${path}")
    else
        response=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}${path}" \
            -H "Content-Type: application/json" \
            -d "${data}")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}   ✅ OK (${http_code})${NC}"
        echo -e "${GREEN}   Response: ${body:0:100}...${NC}\n"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "${RED}   ❌ FAILED (${http_code})${NC}"
        echo -e "${RED}   Response: ${body:0:200}${NC}\n"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  1️⃣ HEALTH CHECK${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

check_endpoint "GET" "/api/battle/healthz" "Health check"

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  2️⃣ БОЕВЫЕ ЛОГИ (3 endpoint)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

check_endpoint "GET" "/api/battle/1" "Детали боя по ID"
check_endpoint "GET" "/api/battle/list?page=1&limit=5" "Список боев (пагинация)"
check_endpoint "GET" "/api/battle/search?player=Test&limit=5" "Поиск боев по игроку"

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  3️⃣ СИНХРОНИЗАЦИЯ (2 endpoint)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

check_endpoint "POST" "/api/sync" "Синхронизация новых файлов"
check_endpoint "POST" "/api/sync/reprocess" "Повторная обработка ошибок"

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  4️⃣ АНАЛИТИКА (7 endpoint)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

check_endpoint "GET" "/api/analytics/player/TestPlayer?days=30" "Аналитика игрока"
check_endpoint "GET" "/api/analytics/players/top?metric=battles_count&limit=10" "Топ игроков"
check_endpoint "GET" "/api/analytics/clan/TestClan?days=30" "Аналитика клана"
check_endpoint "GET" "/api/analytics/resource/Gold?days=30" "Аналитика ресурса"
check_endpoint "GET" "/api/analytics/monster/Goblin?days=30" "Аналитика монстра"
check_endpoint "GET" "/api/analytics/anomalies?days=7" "Аномалии в ресурсах"
check_endpoint "GET" "/api/analytics/stats?days=30" "Общая статистика"

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  5️⃣ АДМИНИСТРИРОВАНИЕ (2 endpoint)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

check_endpoint "GET" "/api/admin/loading-stats" "Статистика загрузки (требует токен)"
check_endpoint "POST" "/api/admin/cleanup?days_old=30" "Очистка старых записей (требует токен)"

echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  📊 ИТОГИ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

echo -e "Всего endpoint: ${TOTAL}"
echo -e "${GREEN}✅ Успешно: ${SUCCESS}${NC}"
echo -e "${RED}❌ Ошибок: ${FAILED}${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 Все endpoint работают!${NC}\n"
else
    echo -e "\n${YELLOW}⚠️ Некоторые endpoint не работают (возможно БД пустая)${NC}\n"
fi
