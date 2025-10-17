#!/bin/bash
# Тест эндпоинта /api/server/status

API_URL="http://localhost:8090"

echo "🌐 Тестируем эндпоинт /api/server/status..."
echo ""
echo "URL: ${API_URL}/api/server/status"
echo ""

curl -s "${API_URL}/api/server/status" | python3 -m json.tool 2>/dev/null || curl -s "${API_URL}/api/server/status"

echo ""



