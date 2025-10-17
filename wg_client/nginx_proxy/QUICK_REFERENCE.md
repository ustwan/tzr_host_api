# ⚡ Шпаргалка API - Quick Reference

> Для AI: Используйте этот документ для быстрого доступа к информации об API

---

## 🎯 Эндпоинты

### Локально (Dev)
```
Base URL: http://localhost:8090
API Key:  dev_api_key_12345
```

### Production
```
Base URL: https://api.yourdomain.com
API Key:  [PROD_KEY_WILL_BE_PROVIDED]
```

---

## 📋 API Reference

### 1. Регистрация (POST)

**Endpoint:** `POST /api/register`  
**Auth:** Требуется `X-API-Key`  
**Rate Limit:** 10 req/min

**Request:**
```javascript
{
  login: "ИгрокПро",        // 3-16 символов
  password: "mypass123",    // 6-20 символов
  gender: 1,                // 0=ж, 1=м
  telegram_id: 999999999,   // обязательно
  username: "@user"         // опционально
}
```

**Response 200:**
```javascript
{
  ok: true,
  message: "Регистрация успешна!",
  request_id: "uuid"
}
```

**Errors:** 400 (валидация), 403 (лимит/API key), 409 (логин занят), 429 (rate limit)

---

### 2. Статус сервера (GET)

**Endpoint:** `GET /api/server/status`  
**Auth:** НЕ требуется  
**Rate Limit:** 30 req/min

**Response 200:**
```javascript
{
  server_status: 1.0,
  rates: {
    exp: 1.0,
    pvp: 1.0,
    pve: 1.0,
    color_mob: 1.0,
    skill: 1.0
  },
  client_status: 256.0
}
```

---

## 💻 Код примеры

### Регистрация

```javascript
fetch('http://localhost:8090/api/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'dev_api_key_12345'
  },
  body: JSON.stringify({
    login: 'Test',
    password: 'test123',
    gender: 1,
    telegram_id: 999999999
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

### Статус сервера

```javascript
fetch('http://localhost:8090/api/server/status')
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 🔒 Важно помнить

1. ✅ `/api/register` - **требует** API ключ
2. ❌ `/api/server/status` - **НЕ требует** API ключ
3. 🚫 **НЕ коммитить** API ключи в Git
4. 🔐 Production - только HTTPS
5. ⏱️ Rate limits: 10/min (register), 30/min (status)

---

## 🧪 Быстрый тест

```bash
# Статус (без ключа)
curl http://localhost:8090/api/server/status

# Регистрация (с ключом)
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{"login":"Test","password":"test123","gender":1,"telegram_id":999999999}'
```

---

## 📚 Полная документация

- **[API_FOR_WEBSITE.md](API_FOR_WEBSITE.md)** ← Основной документ
- [SITE_INTEGRATION.md](SITE_INTEGRATION.md) - Примеры интеграции
- [ENDPOINTS.md](ENDPOINTS.md) - Список эндпоинтов



