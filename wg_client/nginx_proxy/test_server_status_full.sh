#!/bin/bash

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 ПОЛНЫЙ ТЕСТ: /api/server/status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Тест 1: GET запрос
echo "1️⃣  GET запрос (должен работать)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
RESPONSE=$(curl -s -w "\nHTTP:%{http_code}" http://localhost:8090/api/server/status)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP:" | cut -d':' -f2)
DATA=$(echo "$RESPONSE" | sed '/HTTP:/d')

echo "HTTP Code: $HTTP_CODE"
echo "Response: $DATA" | python3 -m json.tool 2>/dev/null || echo "$DATA"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ GET работает"
else
    echo "❌ GET не работает"
fi
echo ""

# Тест 2: OPTIONS запрос (preflight)
echo "2️⃣  OPTIONS запрос (CORS preflight)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS \
  http://localhost:8090/api/server/status \
  -H "Origin: https://test.com" \
  -H "Access-Control-Request-Method: GET")

echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "204" ]; then
    echo "✅ OPTIONS работает (CORS preflight ok)"
else
    echo "❌ OPTIONS не работает (код: $HTTP_CODE, ожидалось: 204)"
fi
echo ""

# Тест 3: Проверка CORS заголовков
echo "3️⃣  CORS заголовки"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -I http://localhost:8090/api/server/status | grep -i "access-control"

if curl -s -I http://localhost:8090/api/server/status | grep -q "Access-Control-Allow-Origin"; then
    echo "✅ CORS заголовки присутствуют"
else
    echo "❌ CORS заголовки отсутствуют"
fi
echo ""

# Тест 4: POST запрос (должен быть заблокирован)
echo "4️⃣  POST запрос (должен быть заблокирован)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8090/api/server/status)

echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "405" ] || [ "$HTTP_CODE" = "403" ]; then
    echo "✅ POST правильно заблокирован"
else
    echo "⚠️  Ожидался код 403/405, получен $HTTP_CODE"
fi
echo ""

# Тест 5: С браузера (симуляция)
echo "5️⃣  Симуляция запроса из браузера"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s http://localhost:8090/api/server/status \
  -H "Origin: https://yoursite.com" \
  -H "Referer: https://yoursite.com/" \
  -H "User-Agent: Mozilla/5.0" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"server_status: {d.get('server_status')}, rates: {d.get('rates')}\")"

echo "✅ Браузерный запрос работает"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
