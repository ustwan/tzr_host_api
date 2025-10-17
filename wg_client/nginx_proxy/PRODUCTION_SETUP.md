# 🚀 Production Setup - Доступ к API для сайта

> Полная инструкция как дать публичный доступ к API регистрации и статуса сервера

---

## 🎯 Цель

Дать **публичному сайту** (хостинг) доступ к API, которое находится **внутри VPN** на HOST_SERVER.

### Схема:

```
┌─────────────────────────┐
│  Сайт на хостинге       │  (например: yourwebsite.com)
│  (публичный интернет)   │
└───────────┬─────────────┘
            │ HTTPS + API Key
            │
            ↓
┌───────────────────────────────────────────────────────────┐
│ HOST_SERVER (ваш сервер с публичным IP)                   │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Nginx (публичный) :443                              │ │
│  │ • SSL/TLS (Let's Encrypt)                           │ │
│  │ • API Key validation                                │ │
│  │ • Rate limiting                                     │ │
│  │ • CORS для вашего домена                            │ │
│  └─────────────────┬───────────────────────────────────┘ │
│                    │                                      │
│                    ↓                                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ WireGuard VPN (10.8.0.x)                            │ │
│  │ └─ Traefik → API_2, API_1                           │ │
│  └─────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

---

## 📋 Пошаговая инструкция

### Шаг 1: Подключитесь к HOST_SERVER

```bash
ssh root@YOUR_HOST_SERVER_IP
```

---

### Шаг 2: Установите Nginx и Certbot

```bash
# Обновление системы
sudo apt update
sudo apt upgrade -y

# Установка Nginx
sudo apt install nginx -y

# Установка Certbot для SSL
sudo apt install certbot python3-certbot-nginx -y

# Проверка установки
nginx -v
certbot --version
```

---

### Шаг 3: Узнайте IP вашего WG_CLIENT в VPN

```bash
# На HOST_SERVER проверьте WireGuard конфигурацию
sudo wg show wg0

# Найдите peer с вашим WG_CLIENT и его AllowedIPs
# Например: AllowedIPs: 10.8.0.2/32
```

**Или проверьте напрямую:**

```bash
# Если Traefik на хосте слушает :1010
curl http://localhost:1010/api/register/health
# {"status": "ok"}

# Значит используйте: server 127.0.0.1:1010;
```

---

### Шаг 4: Сгенерируйте Production API ключ

```bash
# Генерация случайного секретного ключа (32 байта)
PROD_API_KEY=$(openssl rand -base64 32)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔑 ВАШ PRODUCTION API КЛЮЧ:"
echo "$PROD_API_KEY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️ СОХРАНИТЕ ЕГО! Он понадобится для настройки сайта"

# Сохраните в файл для безопасности
sudo mkdir -p /root/.api_keys
echo "$PROD_API_KEY" | sudo tee /root/.api_keys/registration_api_key
sudo chmod 600 /root/.api_keys/registration_api_key

echo "✅ Ключ сохранен в /root/.api_keys/registration_api_key"
```

---

### Шаг 5: Создайте Nginx конфигурацию

```bash
# Скопируйте продакшн конфиг с локальной машины
# (или создайте вручную)

sudo nano /etc/nginx/sites-available/api-proxy
```

**Вставьте конфиг из `nginx_proxy/nginx.prod.conf` и ЗАМЕНИТЕ:**

1. **`api.yourdomain.com`** → ваш реальный домен (например: `api.tzr.com`)

2. **`REPLACE_WITH_YOUR_SECRET_API_KEY_HERE`** → ваш PROD API ключ из Шага 4

3. **`https://yourwebsite.com`** → домен вашего сайта (например: `https://tzr.com`)

4. **`server 10.8.0.2:80;`** → ваш реальный IP из Шага 3
   - Если Traefik на хосте (:1010): `server 127.0.0.1:1010;`
   - Если через VPN: `server 10.8.0.X:80;`

**Пример замен:**

```nginx
# БЫЛО:
server_name api.yourdomain.com;
if ($http_x_api_key = "REPLACE_WITH_YOUR_SECRET_API_KEY_HERE") {
add_header 'Access-Control-Allow-Origin' 'https://yourwebsite.com' always;
server 10.8.0.2:80;

# СТАЛО:
server_name api.tzr.com;
if ($http_x_api_key = "Kq8xN7vZ+mP5jR2wT9yL3cV6bH4nM1sF8aG0dE7uI2o=") {
add_header 'Access-Control-Allow-Origin' 'https://tzr.com' always;
server 127.0.0.1:1010;
```

---

### Шаг 6: Временный конфиг для получения SSL

**Важно:** Сначала создадим упрощенный конфиг для Let's Encrypt ACME challenge:

```bash
sudo nano /etc/nginx/sites-available/api-proxy-temp
```

**Вставьте:**

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;  # Замените на ваш домен!

    location / {
        root /var/www/html;
    }
}
```

**Активируйте:**

```bash
# Удалите дефолтный конфиг
sudo rm /etc/nginx/sites-enabled/default

# Активируйте временный
sudo ln -s /etc/nginx/sites-available/api-proxy-temp /etc/nginx/sites-enabled/

# Тест и перезапуск
sudo nginx -t
sudo systemctl restart nginx
```

---

### Шаг 7: Настройте DNS

**На вашем DNS провайдере (например: Cloudflare, GoDaddy):**

Создайте **A запись:**

```
Тип: A
Имя: api
Значение: PUBLIC_IP_HOST_SERVER
TTL: Auto (или 300)
```

**Пример:**
```
api.tzr.com → 185.xxx.xxx.xxx
```

**Проверка DNS:**

```bash
# С любой машины
nslookup api.tzr.com
# Должен вернуть ваш публичный IP

# Или
dig api.tzr.com +short
```

---

### Шаг 8: Получите SSL сертификат

```bash
# Запросите сертификат от Let's Encrypt
sudo certbot --nginx -d api.yourdomain.com

# Certbot спросит email и согласие с ToS
# Введите ваш email для уведомлений

# Certbot автоматически:
# 1. Получит сертификат
# 2. Обновит nginx конфиг
# 3. Настроит автообновление
```

**Ожидаемый вывод:**

```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/api.yourdomain.com/privkey.pem
```

---

### Шаг 9: Замените на финальный конфиг

```bash
# Удалите временный
sudo rm /etc/nginx/sites-enabled/api-proxy-temp

# Скопируйте финальный (из Шага 5)
sudo cp /etc/nginx/sites-available/api-proxy /etc/nginx/sites-enabled/

# Проверка
sudo nginx -t

# Если ошибок нет:
sudo systemctl reload nginx
```

---

### Шаг 10: Проверьте что работает

**С HOST_SERVER:**

```bash
# Health check
curl https://api.yourdomain.com/health
# {"status": "ok"}

# Server status (без API ключа)
curl https://api.yourdomain.com/api/server/status
# {...}

# Регистрация (с API ключом)
curl -X POST https://api.yourdomain.com/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ВАШ_PROD_API_КЛЮЧ" \
  -d '{
    "login": "Test",
    "password": "test123",
    "gender": 1,
    "telegram_id": 999999999
  }'
```

**С публичного интернета:**

```bash
# С вашего компьютера или с хостинга сайта
curl https://api.yourdomain.com/api/server/status
```

---

## 🌐 Настройка сайта (Production)

### На вашем сайте измените конфигурацию:

**JavaScript:**

```javascript
// Production конфигурация
const API_CONFIG = {
    baseUrl: 'https://api.tzr.com',  // Замените на ваш домен
    apiKey: 'Kq8xN7vZ+mP5jR2wT9yL3cV6bH4nM1sF8aG0dE7uI2o='  // Ваш PROD ключ
};

// Получение статуса (БЕЗ API ключа)
fetch(`${API_CONFIG.baseUrl}/api/server/status`)
    .then(res => res.json())
    .then(data => console.log(data));

// Регистрация (С API ключом)
fetch(`${API_CONFIG.baseUrl}/api/register`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_CONFIG.apiKey
    },
    body: JSON.stringify({
        login: 'Player',
        password: 'pass123',
        gender: 1,
        telegram_id: 123456789
    })
})
.then(res => res.json())
.then(data => console.log(data));
```

### ⚠️ ВАЖНО: Не коммитьте API ключ в Git!

**Используйте переменные окружения:**

```javascript
// .env.production
REACT_APP_API_URL=https://api.tzr.com
REACT_APP_API_KEY=ваш_секретный_ключ

// В коде
const API_CONFIG = {
    baseUrl: process.env.REACT_APP_API_URL,
    apiKey: process.env.REACT_APP_API_KEY
};
```

---

## 🔒 Безопасность Production

### 1. Firewall

```bash
# Разрешить только 80 и 443
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Rate Limiting (уже настроен в nginx)

```nginx
/api/register:       10 req/min
/api/server/status:  30 req/min
```

### 3. Fail2ban (опционально, для защиты от брутфорса)

```bash
sudo apt install fail2ban -y

# Создать фильтр
sudo nano /etc/fail2ban/filter.d/nginx-api.conf
```

```ini
[Definition]
failregex = ^<HOST> .* "(POST|GET) /api/register.*" (403|429)
ignoreregex =
```

```bash
# Настроить jail
sudo nano /etc/fail2ban/jail.local
```

```ini
[nginx-api]
enabled = true
filter = nginx-api
logpath = /var/log/nginx/api-access.log
maxretry = 20
findtime = 300
bantime = 3600
```

```bash
sudo systemctl restart fail2ban
```

### 4. Мониторинг логов

```bash
# Real-time логи
sudo tail -f /var/log/nginx/api-access.log

# Ошибки
sudo tail -f /var/log/nginx/api-error.log

# Статистика
sudo awk '{print $9}' /var/log/nginx/api-access.log | sort | uniq -c | sort -rn
```

---

## 🧪 Тестирование Production

### 1. С HOST_SERVER (локально)

```bash
# Health check
curl https://api.yourdomain.com/health

# Server status
curl https://api.yourdomain.com/api/server/status

# Регистрация
curl -X POST https://api.yourdomain.com/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ВАШ_PROD_КЛЮЧ" \
  -d '{
    "login": "Test",
    "password": "test123",
    "gender": 1,
    "telegram_id": 123456789
  }'
```

### 2. С хостинга сайта (или любого публичного сервера)

```bash
# Тест доступности
curl https://api.yourdomain.com/api/server/status

# Если работает - значит все ок!
```

### 3. С браузера

Откройте: `https://api.yourdomain.com/api/server/status`

Должен вернуть JSON с данными сервера.

---

## 🔧 Автообновление SSL

```bash
# Certbot автоматически настраивает cron для обновления
# Проверить:
sudo certbot renew --dry-run

# Если все ок:
Successfully simulated renewal of certificate
```

**Автообновление настроено через systemd timer:**

```bash
sudo systemctl list-timers | grep certbot
```

---

## 📊 Итоговая конфигурация

### Локальная разработка:

| Параметр | Значение |
|----------|----------|
| **URL** | `http://localhost:8090` |
| **API Key (для /register)** | `dev_api_key_12345` |
| **SSL** | ❌ Нет |
| **CORS** | `*` (все домены) |

### Production:

| Параметр | Значение |
|----------|----------|
| **URL** | `https://api.yourdomain.com` |
| **API Key (для /register)** | Сгенерированный через `openssl rand -base64 32` |
| **SSL** | ✅ Let's Encrypt (автообновление) |
| **CORS** | Только домен вашего сайта |

---

## 🌐 Использование на сайте

### Автоматическое определение окружения

```javascript
// Определяем dev или prod
const isDev = window.location.hostname === 'localhost' 
           || window.location.hostname === '127.0.0.1';

const API_CONFIG = isDev 
    ? {
        baseUrl: 'http://localhost:8090',
        apiKey: 'dev_api_key_12345'
      }
    : {
        baseUrl: 'https://api.tzr.com',  // Ваш prod домен
        apiKey: 'ВАШ_PROD_API_КЛЮЧ'     // Из переменных окружения!
      };

// Теперь используйте API_CONFIG.baseUrl и API_CONFIG.apiKey
```

### Пример с переменными окружения

**React/Next.js:**

```javascript
// .env.development
NEXT_PUBLIC_API_URL=http://localhost:8090
NEXT_PUBLIC_API_KEY=dev_api_key_12345

// .env.production
NEXT_PUBLIC_API_URL=https://api.tzr.com
NEXT_PUBLIC_API_KEY=ваш_prod_ключ

// В коде
const API_CONFIG = {
    baseUrl: process.env.NEXT_PUBLIC_API_URL,
    apiKey: process.env.NEXT_PUBLIC_API_KEY
};
```

**PHP:**

```php
// config.php
$config = [
    'api_url' => getenv('API_URL') ?: 'https://api.tzr.com',
    'api_key' => getenv('API_KEY') ?: 'prod_key_here'
];

// Использование
$api = new RegistrationAPI($config['api_url'], $config['api_key']);
```

---

## 🚨 Troubleshooting

### Проблема 1: SSL сертификат не получается

**Причина:** DNS не настроен или порт 80 закрыт

**Решение:**
```bash
# Проверьте DNS
nslookup api.yourdomain.com

# Проверьте порт 80
sudo netstat -tlnp | grep :80

# Проверьте firewall
sudo ufw status
```

### Проблема 2: 502 Bad Gateway

**Причина:** Nginx не может подключиться к Traefik/API

**Решение:**
```bash
# Проверьте что API доступен локально
curl http://localhost:1010/api/register/health
# или
curl http://10.8.0.2/api/register/health

# Проверьте upstream в nginx
sudo grep "server.*:.*;" /etc/nginx/sites-available/api-proxy
```

### Проблема 3: CORS ошибки

**Причина:** Домен сайта не совпадает с CORS в nginx

**Решение:**
```bash
# Проверьте CORS в конфиге
sudo grep "Access-Control-Allow-Origin" /etc/nginx/sites-available/api-proxy

# Должно быть:
add_header 'Access-Control-Allow-Origin' 'https://ВАШ_САЙТ.com' always;
```

### Проблема 4: API ключ не работает

**Решение:**
```bash
# Проверьте что ключ правильно вставлен в конфиг
sudo grep "http_x_api_key" /etc/nginx/sites-available/api-proxy

# Проверьте что передаете ключ в заголовке
curl -v -H "X-API-Key: YOUR_KEY" https://api.yourdomain.com/api/register
```

---

## ✅ Чеклист Production Setup

- [ ] SSH доступ к HOST_SERVER
- [ ] Nginx установлен
- [ ] Certbot установлен
- [ ] DNS A-запись создана (`api.yourdomain.com`)
- [ ] PROD API ключ сгенерирован и сохранен
- [ ] Nginx конфиг создан (`/etc/nginx/sites-available/api-proxy`)
- [ ] В конфиге заменены все плейсхолдеры:
  - [ ] Домен (`api.yourdomain.com`)
  - [ ] API ключ
  - [ ] CORS origin (`https://yourwebsite.com`)
  - [ ] Upstream сервер (`127.0.0.1:1010` или `10.8.0.X:80`)
- [ ] SSL сертификат получен (`certbot --nginx`)
- [ ] Nginx перезапущен
- [ ] Firewall настроен (порты 80, 443)
- [ ] Тест с HOST_SERVER пройден
- [ ] Тест с публичного IP пройден
- [ ] Тест с хостинга сайта пройден
- [ ] PROD API ключ добавлен на сайт (через .env)
- [ ] Логи проверены

---

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте логи: `sudo tail -f /var/log/nginx/api-error.log`
2. Проверьте что API доступен: `curl http://localhost:1010/api/register/health`
3. Проверьте DNS: `nslookup api.yourdomain.com`
4. Проверьте SSL: `curl -I https://api.yourdomain.com`

---

**Документация:**
- [Локальная разработка](QUICKSTART.md)
- [Интеграция с сайтом](API_FOR_WEBSITE.md)
- [Полная документация](README.md)



