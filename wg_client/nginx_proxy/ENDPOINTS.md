# 🌐 Публичные эндпоинты через Nginx Proxy

## 📋 Доступные эндпоинты

### 1. 🔐 Регистрация (защищен API ключом)

**Endpoint:** `POST /api/register`

**Требования:**
- ✅ Обязателен заголовок `X-API-Key`
- ✅ Rate limit: 10 запросов/минуту + 3 burst
- ✅ Только POST запросы

**Локальный URL:** `http://localhost:8090/api/register`  
**Production URL:** `https://api.yourdomain.com/api/register`

**API Keys:**
- Dev: `dev_api_key_12345`
- Prod: генерируется через `openssl rand -base64 32`

**Пример:**
```javascript
fetch('http://localhost:8090/api/register', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'dev_api_key_12345'
    },
    body: JSON.stringify({
        login: 'ИгрокПро',
        password: 'mypass123',
        gender: 1,
        telegram_id: 999999999
    })
});
```

---

### 2. 🌐 Server Status (публичный)

**Endpoint:** `GET /api/server/status`

**Требования:**
- ❌ API ключ НЕ требуется (публичный)
- ✅ Rate limit: 30 запросов/минуту + 20 burst
- ✅ Только GET запросы
- ✅ CORS разрешен

**Локальный URL:** `http://localhost:8090/api/server/status`  
**Production URL:** `https://api.yourdomain.com/api/server/status`

**Пример:**
```javascript
// Без API ключа!
fetch('http://localhost:8090/api/server/status')
    .then(res => res.json())
    .then(data => console.log(data));
```

**Ожидаемый ответ:**
```json
{
    "online_players": 42,
    "max_players": 1000,
    "server_version": "1.2.3",
    "uptime_seconds": 86400
}
```

---

### 3. ❤️ Health Check

**Endpoint:** `GET /api/register/health`

**Требования:**
- ❌ API ключ НЕ требуется
- ✅ Rate limit: 30 запросов/минуту
- ✅ Только GET запросы

**Локальный URL:** `http://localhost:8090/api/register/health`  
**Production URL:** `https://api.yourdomain.com/health`

**Пример:**
```bash
curl http://localhost:8090/api/register/health
# {"status": "ok"}
```

---

## 🔒 Безопасность

### Rate Limiting

| Эндпоинт | Лимит | Burst | Применение |
|----------|-------|-------|------------|
| `/api/register` | 10/мин | 3 | Защита от спама регистраций |
| `/api/server/status` | 30/мин | 20 | Публичный, частый доступ |
| `/health` | 30/мин | 10 | Мониторинг |

### CORS

**Локальная разработка:**
```nginx
Access-Control-Allow-Origin: *
```

**Production:**
```nginx
Access-Control-Allow-Origin: https://yourwebsite.com
```

### API Key Protection

- `/api/register` - **требует** API ключ
- `/api/server/status` - **НЕ требует** API ключ (публичный)
- `/health` - **НЕ требует** API ключ

---

## 🧪 Тестирование

### Локальное тестирование

**1. Регистрация (с API ключом):**
```bash
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{
    "login": "Test123",
    "password": "test123456",
    "gender": 1,
    "telegram_id": 999999999
  }'
```

**2. Server Status (без API ключа):**
```bash
curl http://localhost:8090/api/server/status
```

**3. Health Check:**
```bash
curl http://localhost:8090/api/register/health
```

### Тестовые скрипты

```bash
# Полный набор тестов
./nginx_proxy/test_api.sh

# Тест регистрации
./nginx_proxy/test_simple.sh

# Тест server status
./nginx_proxy/test_server_status.sh
```

---

## 🚀 Production URLs

После деплоя на HOST_SERVER:

- Регистрация: `https://api.yourdomain.com/api/register`
- Server Status: `https://api.yourdomain.com/api/server/status`
- Health Check: `https://api.yourdomain.com/health`

---

## 📚 Дополнительная документация

- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт
- [SITE_INTEGRATION.md](SITE_INTEGRATION.md) - Интеграция с сайтом
- [README.md](README.md) - Полная документация



