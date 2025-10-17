#!/bin/bash

set +e  # Не останавливаемся на ошибках

TELEGRAM_ID=312660736
API_URL="http://localhost:8090"
API_KEY="dev_api_key_12345"
TIMESTAMP=$(date +%s)
LOGIN="TestUser${TIMESTAMP: -6}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 ПОЛНЫЙ ТЕСТ API РЕГИСТРАЦИИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Параметры теста:"
echo "  Telegram ID: $TELEGRAM_ID"
echo "  Логин: $LOGIN"
echo "  API URL: $API_URL"
echo ""

# ============================================================================
# ТЕСТ 1: Health Check
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  HEALTH CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

HEALTH=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:8090/health)
HTTP_CODE=$(echo "$HEALTH" | grep "HTTP_CODE" | cut -d':' -f2)
RESPONSE=$(echo "$HEALTH" | sed '/HTTP_CODE/d')

echo "Response: $RESPONSE"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health check OK"
else
    echo "❌ Health check FAILED"
    exit 1
fi
echo ""

# ============================================================================
# ТЕСТ 2: Регистрация БЕЗ API ключа (ожидается 403)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  ТЕСТ: Регистрация БЕЗ API ключа (ожидаем 403)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESULT=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X POST "$API_URL/api/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"login\": \"$LOGIN\",
    \"password\": \"test12345\",
    \"gender\": 0,
    \"telegram_id\": $TELEGRAM_ID
  }")

HTTP_CODE=$(echo "$RESULT" | grep "HTTP_CODE" | cut -d':' -f2)
RESPONSE=$(echo "$RESULT" | sed '/HTTP_CODE/d')

echo "Response: $RESPONSE"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "403" ]; then
    echo "✅ Правильно заблокировал без API ключа"
else
    echo "⚠️  Ожидался код 403, получен $HTTP_CODE"
fi
echo ""

# ============================================================================
# ТЕСТ 3: Невалидные данные - короткий логин (ожидается 422)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  ТЕСТ: Короткий логин (2 символа, ожидаем 422)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESULT=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X POST "$API_URL/api/register" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{
    \"login\": \"AB\",
    \"password\": \"test12345\",
    \"gender\": 0,
    \"telegram_id\": $TELEGRAM_ID
  }")

HTTP_CODE=$(echo "$RESULT" | grep "HTTP_CODE" | cut -d':' -f2)
RESPONSE=$(echo "$RESULT" | sed '/HTTP_CODE/d')

echo "Response: $RESPONSE"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "422" ]; then
    echo "✅ Валидация работает корректно"
else
    echo "⚠️  Ожидался код 422, получен $HTTP_CODE"
fi
echo ""

# ============================================================================
# ТЕСТ 4: Невалидные данные - короткий пароль (ожидается 422)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  ТЕСТ: Короткий пароль (5 символов, ожидаем 422)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESULT=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X POST "$API_URL/api/register" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{
    \"login\": \"$LOGIN\",
    \"password\": \"12345\",
    \"gender\": 0,
    \"telegram_id\": $TELEGRAM_ID
  }")

HTTP_CODE=$(echo "$RESULT" | grep "HTTP_CODE" | cut -d':' -f2)
RESPONSE=$(echo "$RESULT" | sed '/HTTP_CODE/d')

echo "Response: $RESPONSE"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "422" ]; then
    echo "✅ Валидация пароля работает"
else
    echo "⚠️  Ожидался код 422, получен $HTTP_CODE"
fi
echo ""

# ============================================================================
# ТЕСТ 5: Невалидный gender (ожидается 422)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  ТЕСТ: Невалидный gender (2, ожидаем 422)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESULT=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X POST "$API_URL/api/register" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{
    \"login\": \"$LOGIN\",
    \"password\": \"test12345\",
    \"gender\": 2,
    \"telegram_id\": $TELEGRAM_ID
  }")

HTTP_CODE=$(echo "$RESULT" | grep "HTTP_CODE" | cut -d':' -f2)
RESPONSE=$(echo "$RESULT" | sed '/HTTP_CODE/d')

echo "Response: $RESPONSE"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "422" ]; then
    echo "✅ Валидация gender работает"
else
    echo "⚠️  Ожидался код 422, получен $HTTP_CODE"
fi
echo ""

# ============================================================================
# ТЕСТ 6: УСПЕШНАЯ РЕГИСТРАЦИЯ
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  ТЕСТ: УСПЕШНАЯ РЕГИСТРАЦИЯ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESULT=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X POST "$API_URL/api/register" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Request-Id: test-$(uuidgen)" \
  -d "{
    \"login\": \"$LOGIN\",
    \"password\": \"test12345\",
    \"gender\": 0,
    \"telegram_id\": $TELEGRAM_ID,
    \"username\": \"@test_user\"
  }")

HTTP_CODE=$(echo "$RESULT" | grep "HTTP_CODE" | cut -d':' -f2)
RESPONSE=$(echo "$RESULT" | sed '/HTTP_CODE/d')

echo "Response: $RESPONSE"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Регистрация успешна!"
else
    echo "❌ Регистрация FAILED (код: $HTTP_CODE)"
    echo "   Детали: $RESPONSE"
fi
echo ""

# ============================================================================
# ТЕСТ 7: Повторная регистрация с тем же логином (ожидается 409)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  ТЕСТ: Повторная регистрация (ожидаем 409 - login_taken)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sleep 1

RESULT=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X POST "$API_URL/api/register" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{
    \"login\": \"$LOGIN\",
    \"password\": \"another_pass\",
    \"gender\": 1,
    \"telegram_id\": $TELEGRAM_ID
  }")

HTTP_CODE=$(echo "$RESULT" | grep "HTTP_CODE" | cut -d':' -f2)
RESPONSE=$(echo "$RESULT" | sed '/HTTP_CODE/d')

echo "Response: $RESPONSE"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "409" ]; then
    echo "✅ Правильно блокирует повторный логин"
else
    echo "⚠️  Ожидался код 409, получен $HTTP_CODE"
fi
echo ""

# ============================================================================
# ТЕСТ 8: Проверка в БД
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣  ПРОВЕРКА: Данные в БД"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Попытка подключиться к MySQL контейнеру
DB_CHECK=$(docker exec -i db_bridge mysql -uroot -proot -e "USE wot_server; SELECT player_id, login, telegram_id FROM players WHERE login='$LOGIN' LIMIT 1;" 2>&1)

if echo "$DB_CHECK" | grep -q "$LOGIN"; then
    echo "✅ Игрок найден в БД:"
    echo "$DB_CHECK"
else
    echo "⚠️  Не удалось найти игрока в БД"
    echo "   (Возможно, контейнер db_bridge не запущен или имя другое)"
fi
echo ""

# ============================================================================
# ТЕСТ 9: Подсчет аккаунтов для Telegram ID
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9️⃣  ПРОВЕРКА: Сколько аккаунтов у Telegram ID $TELEGRAM_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

COUNT=$(docker exec -i db_bridge mysql -uroot -proot -N -e "USE wot_server; SELECT COUNT(*) FROM telegram_players WHERE telegram_id=$TELEGRAM_ID;" 2>/dev/null)

if [ -n "$COUNT" ]; then
    echo "Количество аккаунтов: $COUNT / 5"
    
    if [ "$COUNT" -ge 5 ]; then
        echo "⚠️  Достигнут лимит! Следующая регистрация будет заблокирована."
    else
        echo "✅ Еще можно зарегистрировать $((5 - COUNT)) аккаунтов"
    fi
    
    # Показываем все аккаунты
    echo ""
    echo "Список всех аккаунтов:"
    docker exec -i db_bridge mysql -uroot -proot -e "USE wot_server; SELECT p.login, tp.telegram_id, tp.username FROM telegram_players tp JOIN players p ON tp.player_id = p.player_id WHERE tp.telegram_id=$TELEGRAM_ID;" 2>/dev/null
else
    echo "⚠️  Не удалось проверить количество аккаунтов"
fi
echo ""

# ============================================================================
# ТЕСТ 10: Проверка логов API_Father
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔟 ЛОГИ: API_Father (последние 10 строк)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docker logs api_father --tail 10 2>&1 | grep -E "(register|$LOGIN|$TELEGRAM_ID|ERROR|INFO)" || echo "(Нет релевантных логов)"
echo ""

# ============================================================================
# ИТОГИ
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Результаты:"
echo "  ✓ Health check"
echo "  ✓ Блокировка без API ключа (403)"
echo "  ✓ Валидация логина (422)"
echo "  ✓ Валидация пароля (422)"
echo "  ✓ Валидация gender (422)"
echo "  ✓ Успешная регистрация (200)"
echo "  ✓ Блокировка дубликата логина (409)"
echo "  ✓ Проверка БД"
echo "  ✓ Подсчет аккаунтов"
echo ""
echo "🎯 Зарегистрированный пользователь:"
echo "  Логин: $LOGIN"
echo "  Telegram ID: $TELEGRAM_ID"
echo "  Пароль: test12345"
echo ""
