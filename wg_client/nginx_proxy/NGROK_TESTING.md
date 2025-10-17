# 🌐 Тестирование API с Ngrok

> Как тестировать API с сайтом на ngrok (или другом публичном хостинге)

---

## 🎯 Проблема

Ваш сайт находится на **ngrok** (или другом хостинге с публичным URL), а API на **localhost**. 

Браузер блокирует запросы из-за CORS, потому что:
```
https://your-site.ngrok.io → http://localhost:8090
         ❌ CORS ERROR
```

---

## ✅ Решение: Ngrok туннель для API

Нужно **также** выставить API через ngrok.

---

## 📋 Шаг 1: Запустите ngrok для API

### Вариант A: Отдельный терминал

```bash
# В новом терминале
ngrok http 8090
```

### Вариант B: Используйте готовый скрипт

```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client/nginx_proxy
./START_NGROK_API.sh
```

---

## 📝 Шаг 2: Сохраните ngrok URL

После запуска ngrok вы увидите:

```
ngrok                                                          

Session Status                online
Account                       your_account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123xyz.ngrok-free.app -> http://localhost:8090

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Важно:** Сохраните `Forwarding` URL:
```
https://abc123xyz.ngrok-free.app
```

---

## 🔧 Шаг 3: Обновите настройки сайта

### В коде сайта замените:

**БЫЛО:**
```javascript
const API_CONFIG = {
    baseUrl: 'http://localhost:8090',
    apiKey: 'dev_api_key_12345'
};
```

**СТАЛО:**
```javascript
const API_CONFIG = {
    baseUrl: 'https://abc123xyz.ngrok-free.app',  // ← Ваш ngrok URL!
    apiKey: 'dev_api_key_12345'
};
```

---

## ✅ Шаг 4: Тестируйте

### Проверка прямо из браузера:

1. Откройте ваш сайт на ngrok: `https://your-site.ngrok.io`

2. Откройте DevTools → Console

3. Выполните:

```javascript
// Тест статуса сервера
fetch('https://abc123xyz.ngrok-free.app/api/server/status')
    .then(res => res.json())
    .then(data => console.log(data));

// Тест регистрации
fetch('https://abc123xyz.ngrok-free.app/api/register', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'dev_api_key_12345'
    },
    body: JSON.stringify({
        login: 'TestUser',
        password: 'test123',
        gender: 1,
        telegram_id: 123456789
    })
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## 🚨 Ngrok Free Plan Ограничения

### Ngrok бесплатный план имеет:

- ✅ **1 туннель одновременно** (нужно 2 процесса ngrok)
- ⚠️ **URL меняется** при каждом перезапуске
- ⚠️ **Warning страница** при первом заходе

### Решения:

#### 1. Используйте 2 ngrok процесса

```bash
# Терминал 1: ngrok для сайта
ngrok http 3000

# Терминал 2: ngrok для API
ngrok http 8090
```

#### 2. Или используйте ngrok config с authtoken

```bash
# Получите authtoken на https://dashboard.ngrok.com/get-started/your-authtoken

# Сохраните
ngrok config add-authtoken YOUR_TOKEN

# Создайте конфиг
cat > ~/.ngrok2/ngrok.yml << 'EOF'
version: "2"
authtoken: YOUR_TOKEN
tunnels:
  site:
    proto: http
    addr: 3000
  api:
    proto: http
    addr: 8090
EOF

# Запустите оба туннеля
ngrok start --all
```

#### 3. Или используйте фиксированные URL (Ngrok Paid)

Платный план ngrok позволяет фиксированные URL:
```
https://your-api.ngrok.app
```

---

## 🔄 Альтернатива: Localtunnel (бесплатный)

Если ngrok не подходит, используйте **localtunnel**:

```bash
# Установка
npm install -g localtunnel

# Для API
lt --port 8090 --subdomain my-api
# URL: https://my-api.loca.lt

# Для сайта
lt --port 3000 --subdomain my-site
# URL: https://my-site.loca.lt
```

**Плюсы:**
- ✅ Бесплатно
- ✅ Можно выбрать subdomain (если свободен)
- ✅ Несколько туннелей одновременно

**Минусы:**
- ⚠️ Менее стабильно чем ngrok
- ⚠️ Иногда требует подтверждение в браузере

---

## 🧪 Проверка CORS

### Если все равно CORS ошибка:

1. **Проверьте ngrok URL в ответе:**

```bash
# На компьютере
curl -I https://your-ngrok.ngrok-free.app/api/server/status
```

Должны быть заголовки:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, OPTIONS
Access-Control-Allow-Headers: Content-Type, X-Request-Id
```

2. **Проверьте что nginx конфиг загружен:**

```bash
# Проверить логи контейнера
docker logs nginx_api_proxy

# Должно быть:
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

3. **Проверьте preflight (OPTIONS):**

```bash
curl -X OPTIONS https://your-ngrok.ngrok-free.app/api/server/status \
  -H "Origin: https://your-site.ngrok.io" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

Должен вернуть `HTTP/1.1 204 No Content`

---

## 📊 Итоговая схема тестирования

### Локальная разработка (без ngrok):

```
┌─────────────────┐
│ Сайт            │
│ localhost:3000  │
└────────┬────────┘
         │
         ↓
┌────────────────────────┐
│ Nginx Proxy            │
│ localhost:8090         │
│ (demo_site.html)       │
└────────┬───────────────┘
         │
         ↓
┌────────────────────────┐
│ Traefik → API          │
│ localhost:1010         │
└────────────────────────┘
```

### С ngrok (тестирование с публичным URL):

```
┌──────────────────────────┐
│ Сайт на ngrok            │
│ https://site.ngrok.io    │
└────────────┬─────────────┘
             │ HTTPS
             ↓
┌──────────────────────────────────┐
│ API на ngrok                     │
│ https://api.ngrok.io             │
│ ↓ туннель к localhost:8090       │
└────────────┬─────────────────────┘
             │
             ↓
┌────────────────────────────────┐
│ Nginx Proxy                    │
│ localhost:8090                 │
└────────────┬───────────────────┘
             │
             ↓
┌────────────────────────────────┐
│ Traefik → API                  │
│ localhost:1010                 │
└────────────────────────────────┘
```

### Production:

```
┌──────────────────────────┐
│ Сайт на хостинге         │
│ https://yoursite.com     │
└────────────┬─────────────┘
             │ HTTPS + API Key
             ↓
┌──────────────────────────────────┐
│ HOST_SERVER                      │
│ ┌──────────────────────────────┐ │
│ │ Nginx (публичный) :443       │ │
│ │ SSL + Rate Limit + CORS      │ │
│ └────────────┬─────────────────┘ │
│              ↓                    │
│ ┌──────────────────────────────┐ │
│ │ WireGuard VPN                │ │
│ │ └─ Traefik → API             │ │
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
```

---

## 🛠 Troubleshooting

### Проблема 1: "tunnel not found"

**Причина:** ngrok процесс не запущен или упал

**Решение:**
```bash
# Проверьте процессы
ps aux | grep ngrok

# Перезапустите
ngrok http 8090
```

---

### Проблема 2: "ERR_NGROK_3200"

**Причина:** Лимит туннелей (Free plan = 1 туннель)

**Решение:**
```bash
# Вариант 1: Используйте authtoken и config (смотрите выше)
# Вариант 2: Используйте localtunnel
# Вариант 3: Купите ngrok Pro ($8/месяц)
```

---

### Проблема 3: "This site is protected by ngrok"

**Причина:** Ngrok warning page для бесплатного плана

**Решение:**
- Нажмите "Visit Site"
- Или используйте localtunnel
- Или купите ngrok Pro

---

### Проблема 4: CORS все равно блокирует

**Причина:** Nginx конфиг не применился

**Решение:**
```bash
# Перезапустите контейнер
cd /Users/ii/Documents/code/WG_HUB/wg_client/nginx_proxy
docker-compose restart

# Проверьте что запущен
docker ps | grep nginx_api_proxy

# Проверьте логи
docker logs nginx_api_proxy
```

---

## 📞 Quick Reference

### Команды:

```bash
# Запуск ngrok для API
ngrok http 8090

# Проверка туннелей
curl http://127.0.0.1:4040/api/tunnels

# Тест API через ngrok
curl https://YOUR-NGROK-URL.ngrok-free.app/api/server/status

# Перезапуск Nginx proxy
docker-compose restart
```

### URLs:

| Сервис | Локально | Ngrok |
|--------|----------|-------|
| **Сайт** | `http://localhost:3000` | `https://YOUR-SITE.ngrok.io` |
| **API** | `http://localhost:8090` | `https://YOUR-API.ngrok.io` |
| **Ngrok Dashboard** | `http://127.0.0.1:4040` | - |

### API Keys:

| Эндпоинт | API Key Required? |
|----------|-------------------|
| `/api/server/status` | ❌ Нет |
| `/api/register` | ✅ Да: `dev_api_key_12345` |

---

**📚 Документация:**
- [Локальная разработка](QUICKSTART.md)
- [Production Setup](PRODUCTION_SETUP.md)
- [Интеграция с сайтом](API_FOR_WEBSITE.md)



