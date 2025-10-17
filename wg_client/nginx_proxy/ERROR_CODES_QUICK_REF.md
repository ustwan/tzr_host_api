# ⚡ API Регистрации - Краткий справочник

## 📥 Запрос

```http
POST /api/register
Content-Type: application/json
X-API-Key: dev_api_key_12345

{
  "login": "string (3-16 chars)",
  "password": "string (6-20 chars)",
  "gender": 0 | 1,
  "telegram_id": integer,
  "username": "string (optional)"
}
```

## ✅ Успех (200)

```json
{
  "ok": true,
  "message": "Регистрация успешна!",
  "request_id": "..."
}
```

## ❌ Ошибки

| Код | detail | Причина | Решение |
|-----|--------|---------|---------|
| **400** | `Bad Request` | Невалидный JSON | Проверьте JSON |
| **400** | `bad_request` | Ошибка валидации | Проверьте поля |
| **403** | `invalid_api_key` | Неверный/отсутствует API ключ | Передайте `X-API-Key` |
| **403** | `limit_exceeded` | Уже 5 аккаунтов на этот Telegram ID | Используйте другой Telegram |
| **403** | `not_in_telegram_group` | Не состоите в группе | Вступите в группу |
| **409** | `login_taken` | Логин занят | Выберите другой логин |
| **422** | `Validation Error` | Неверный формат поля | См. детали в `detail[]` |
| **429** | `Too Many Requests` | > 10 запросов/мин | Подождите минуту |
| **500** | `internal_error` | Ошибка сервера | Обратитесь к админу |
| **502** | `game_server error...` | Game server недоступен | Обратитесь к админу |
| **503** | `service unavailable` | Сервис недоступен | Попробуйте позже |

## 📋 Валидация полей

| Поле | Правило |
|------|---------|
| `login` | 3-16 символов, уникальный |
| `password` | 6-20 символов |
| `gender` | Только `0` (М) или `1` (Ж) |
| `telegram_id` | Целое число, макс 5 аккаунтов |
| `username` | Опционально, любая строка |

## 🔑 Лимиты

- **Rate limit:** 10 запросов/минуту с IP
- **Аккаунты:** Максимум 5 на Telegram ID
- **Telegram группа:** Проверяется (если включено)

## 🧪 Быстрый тест

```bash
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{
    "login": "Test1",
    "password": "pass123",
    "gender": 0,
    "telegram_id": 123456789
  }'
```

## 📚 Подробнее

- [Полная спецификация](REGISTRATION_API_SPEC.md)
- [Интеграция с сайтом](API_FOR_WEBSITE.md)
- [Все эндпоинты](ENDPOINTS.md)
