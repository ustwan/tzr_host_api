#!/bin/bash
# ============================================================================
# Скрипт для тестирования API регистрации через nginx proxy
# ============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
API_URL="${API_URL:-http://localhost:8090}"
API_KEY="${API_KEY:-dev_api_key_12345}"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}    Тестирование API регистрации через nginx proxy${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "API URL: ${YELLOW}${API_URL}${NC}"
echo -e "API Key: ${YELLOW}${API_KEY}${NC}"
echo ""

# ============================================================================
# ТЕСТ 1: Health Check (без API ключа)
# ============================================================================
echo -e "${BLUE}ТЕСТ 1:${NC} Health Check (без API ключа)"
echo -e "GET ${API_URL}/api/register/health"
echo ""

response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${API_URL}/api/register/health")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Health check успешен${NC}"
    echo "Ответ: $body"
else
    echo -e "${RED}✗ Health check провален (код: $http_code)${NC}"
    echo "Ответ: $body"
fi
echo ""

# ============================================================================
# ТЕСТ 2: Запрос без API ключа (должен вернуть 403)
# ============================================================================
echo -e "${BLUE}ТЕСТ 2:${NC} Запрос без API ключа (ожидается 403)"
echo -e "POST ${API_URL}/api/register"
echo ""

response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "${API_URL}/api/register" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "ТестИгрок",
        "password": "test123",
        "gender": 1,
        "telegram_id": 999999999
    }')

http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" = "403" ]; then
    echo -e "${GREEN}✓ Корректно блокирован запрос без API ключа${NC}"
    echo "Ответ: $body"
else
    echo -e "${RED}✗ Неожиданный код ответа: $http_code (ожидался 403)${NC}"
    echo "Ответ: $body"
fi
echo ""

# ============================================================================
# ТЕСТ 3: Запрос с неверным API ключом (должен вернуть 403)
# ============================================================================
echo -e "${BLUE}ТЕСТ 3:${NC} Запрос с неверным API ключом (ожидается 403)"
echo -e "POST ${API_URL}/api/register"
echo ""

response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "${API_URL}/api/register" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: wrong_key_12345" \
    -d '{
        "login": "ТестИгрок",
        "password": "test123",
        "gender": 1,
        "telegram_id": 999999999
    }')

http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" = "403" ]; then
    echo -e "${GREEN}✓ Корректно блокирован запрос с неверным API ключом${NC}"
    echo "Ответ: $body"
else
    echo -e "${RED}✗ Неожиданный код ответа: $http_code (ожидался 403)${NC}"
    echo "Ответ: $body"
fi
echo ""

# ============================================================================
# ТЕСТ 4: Запрос с правильным API ключом (регистрация)
# ============================================================================
echo -e "${BLUE}ТЕСТ 4:${NC} Запрос с правильным API ключом"
echo -e "POST ${API_URL}/api/register"
echo ""

# Генерируем уникальный логин
RANDOM_LOGIN="TestUser_$(date +%s)"
REQUEST_ID=$(uuidgen 2>/dev/null || echo "req_$(date +%s)")

echo -e "Login: ${YELLOW}${RANDOM_LOGIN}${NC}"
echo -e "Request-Id: ${YELLOW}${REQUEST_ID}${NC}"
echo ""

response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "${API_URL}/api/register" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: ${API_KEY}" \
    -H "X-Request-Id: ${REQUEST_ID}" \
    -d "{
        \"login\": \"${RANDOM_LOGIN}\",
        \"password\": \"test123456\",
        \"gender\": 1,
        \"telegram_id\": 999999999,
        \"username\": \"test_user\"
    }")

http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Регистрация успешна!${NC}"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
elif [ "$http_code" = "502" ]; then
    echo -e "${YELLOW}⚠ API недоступен (502 Bad Gateway)${NC}"
    echo "Убедитесь, что WG_CLIENT API запущен на порту 1010"
    echo "$body"
elif [ "$http_code" = "403" ]; then
    echo -e "${YELLOW}⚠ Ошибка авторизации (403)${NC}"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
else
    echo -e "${RED}✗ Ошибка регистрации (код: $http_code)${NC}"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
fi
echo ""

# ============================================================================
# ТЕСТ 5: Rate Limiting (должен заблокировать после лимита)
# ============================================================================
echo -e "${BLUE}ТЕСТ 5:${NC} Rate Limiting (10 запросов/мин + 3 burst)"
echo "Отправляем 15 запросов подряд..."
echo ""

success_count=0
rate_limited_count=0

for i in {1..15}; do
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST "${API_URL}/api/register" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: ${API_KEY}" \
        -d '{
            "login": "RateTest",
            "password": "test123",
            "gender": 1,
            "telegram_id": 888888888
        }')
    
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    
    if [ "$http_code" = "429" ]; then
        rate_limited_count=$((rate_limited_count + 1))
        echo -e "${YELLOW}Запрос #${i}: 429 Too Many Requests ⚠${NC}"
    elif [ "$http_code" = "200" ] || [ "$http_code" = "400" ] || [ "$http_code" = "409" ]; then
        success_count=$((success_count + 1))
        echo -e "${GREEN}Запрос #${i}: ${http_code} ✓${NC}"
    else
        echo -e "${BLUE}Запрос #${i}: ${http_code}${NC}"
    fi
    
    # Небольшая задержка между запросами
    sleep 0.1
done

echo ""
echo -e "Успешно обработано: ${GREEN}${success_count}${NC}"
echo -e "Заблокировано (429): ${YELLOW}${rate_limited_count}${NC}"

if [ "$rate_limited_count" -gt 0 ]; then
    echo -e "${GREEN}✓ Rate limiting работает корректно${NC}"
else
    echo -e "${RED}✗ Rate limiting не сработал${NC}"
fi
echo ""

# ============================================================================
# ТЕСТ 6: GET запрос (должен вернуть 405 Method Not Allowed)
# ============================================================================
echo -e "${BLUE}ТЕСТ 6:${NC} GET запрос (ожидается 405 Method Not Allowed)"
echo -e "GET ${API_URL}/api/register"
echo ""

response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X GET "${API_URL}/api/register" \
    -H "X-API-Key: ${API_KEY}")

http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" = "405" ]; then
    echo -e "${GREEN}✓ GET запрос корректно отклонен${NC}"
else
    echo -e "${YELLOW}⚠ Код ответа: $http_code (ожидался 405)${NC}"
fi
echo "Ответ: $body"
echo ""

# ============================================================================
# Итоги
# ============================================================================
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Тестирование завершено!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

