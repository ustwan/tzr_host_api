#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_URL="http://localhost:1010/api/register"
DELAY=1  # 1 секунда между запросами

echo -e "${YELLOW}🧪 Тест с задержками 1 сек между запросами${NC}\n"

test_with_delay() {
    local name="$1"
    local data="$2"
    
    echo -e "${YELLOW}📝 ${name}${NC}"
    response=$(curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d "$data")
    echo -e "${GREEN}Ответ: ${response}${NC}"
    sleep $DELAY
    echo ""
}

# Тест 1: Русские логины
test_with_delay "Тест 1: Русский логин" '{"login":"Игрок111","password":"pass111","gender":1,"telegram_id":111111,"username":"ru1"}'
test_with_delay "Тест 2: Русский с пробелом" '{"login":"Игрок Два","password":"pass222","gender":0,"telegram_id":222222,"username":"ru2"}'
test_with_delay "Тест 3: Русский с цифрами" '{"login":"Игрок333","password":"pass333","gender":1,"telegram_id":333333,"username":"ru3"}'

# Тест 2: Лимит 5 аккаунтов
echo -e "${YELLOW}═══ Тест лимита 5 аккаунтов ═══${NC}\n"
TG_ID=999000111

for i in {1..5}; do
    test_with_delay "Аккаунт ${i}/5" "{\"login\":\"Limit${i}\",\"password\":\"pass${i}\",\"gender\":$((i % 2)),\"telegram_id\":${TG_ID},\"username\":\"lim${i}\"}"
done

# Проверяем 6-й (должен быть отклонен)
echo -e "${YELLOW}Проверка 6-го аккаунта (должен быть отклонен):${NC}"
response=$(curl -s -X POST "$API_URL" -H "Content-Type: application/json" \
  -d "{\"login\":\"Limit6\",\"password\":\"pass6\",\"gender\":0,\"telegram_id\":${TG_ID},\"username\":\"lim6\"}")
echo -e "${GREEN}Ответ: ${response}${NC}"

if echo "$response" | grep -q "limit_exceeded"; then
    echo -e "${GREEN}✅ Лимит работает корректно!${NC}\n"
else
    echo -e "${RED}❌ Лимит НЕ работает!${NC}\n"
fi

# Проверяем БД
echo -e "${YELLOW}═══ Проверка БД ═══${NC}\n"
docker exec wg_client-db-1 mysql -utzuser -ptzpass tzserver \
  -e "SELECT telegram_id, username, login FROM tgplayers ORDER BY telegram_id;" 2>/dev/null

echo ""
echo -e "${GREEN}✅ Тестирование завершено${NC}"
