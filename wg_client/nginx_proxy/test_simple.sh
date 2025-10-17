#!/bin/bash
# Простой тест регистрации

API_URL="http://localhost:8090"
API_KEY="dev_api_key_12345"

echo "🧪 Тестируем регистрацию через nginx proxy..."
echo ""

# Генерируем уникальный логин
LOGIN="User_$(date +%s)"

echo "Логин: $LOGIN"
echo "API URL: $API_URL/api/register"
echo ""

curl -X POST "${API_URL}/api/register" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Request-Id: $(uuidgen 2>/dev/null || echo 'req_123')" \
  -d "{
    \"login\": \"${LOGIN}\",
    \"password\": \"test123456\",
    \"gender\": 1,
    \"telegram_id\": 999999999,
    \"username\": \"telegram_test\"
  }" | python3 -m json.tool

echo ""

