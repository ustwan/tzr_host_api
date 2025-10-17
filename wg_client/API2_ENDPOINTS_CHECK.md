# 🔍 Проверка всех ручек API 2 (Регистрация)

## 📋 СПИСОК ВСЕХ ENDPOINTS

### 1. POST /register - Регистрация игрока
**Путь через Traefik:** `POST /api/register`

**Параметры (JSON):**
```json
{
  "login": "string (3-16 символов, русские/английские)",
  "password": "string (6-20 ASCII символов)",
  "gender": 0 | 1,
  "telegram_id": 123456789,
  "username": "string (опционально)",
  "user_created_at": "string (опционально)",
  "user_registration_ip": "string (опционально)",
  "user_Country": "string (опционально)",
  "Request-Id": "string (опционально)",
  "user_registration_type": "string (опционально)"
}
```

**Валидация:**
- ✅ login: русские/английские буквы + цифры + '_' + '-' + пробел (3-16)
- ✅ password: ASCII символы (6-20)
- ✅ gender: 0 (женский) или 1 (мужской)
- ✅ telegram_id: обязательное число

**Ответы:**
- `200` - успех: `{"ok": true, "message": "Регистрация успешна!", "request_id": ...}`
- `400` - ошибка валидации: `{"ok": false, "error": "validation_error", "fields": {...}}`
- `403` - лимит превышен: `{"detail": "limit_exceeded"}`
- `403` - не в группе: `{"detail": "not_in_telegram_group"}`
- `409` - логин занят: `{"detail": "login_taken"}`
- `502` - ошибка father/game_server: `{"detail": "father_unreachable"}`

---

### 2. GET /healthz - Health check (стандартный)
**Путь:** `/healthz` (внутренний, не через Traefik)

**Ответ:**
```json
{"status": "ok"}
```

---

### 3. GET /health - Health check (альтернативный)
**Путь:** `/health` (внутренний)

**Ответ:**
```json
{"status": "ok"}
```

---

### 4. GET /register/health - Health check (с префиксом)
**Путь через Traefik:** `GET /api/register/health`

**Ответ:**
```json
{"status": "ok"}
```

---

## ✅ ИТОГО: 4 ENDPOINT

| # | Method | Path | Через Traefik | Назначение |
|---|--------|------|---------------|------------|
| 1 | POST | `/register` | `/api/register` | Регистрация игрока |
| 2 | GET | `/healthz` | - | Health check |
| 3 | GET | `/health` | - | Health check |
| 4 | GET | `/register/health` | `/api/register/health` | Health check |

---

## 🧪 ТЕСТИРОВАНИЕ ВСЕХ РУЧЕК

### Запускаю тесты...
