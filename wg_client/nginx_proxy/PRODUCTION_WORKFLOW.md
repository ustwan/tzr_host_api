# 🚀 Production Workflow - Полная архитектура

> Как работает вся система на production сервере

---

## 🌐 Архитектура на HOST_SERVER (Production)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ПУБЛИЧНЫЙ ИНТЕРНЕТ                                                      │
│ • Пользователи с сайта                                                  │
│ • Мобильные приложения                                                  │
│ • Браузеры                                                              │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ HTTPS (443)
                             │ api.yourdomain.com
                             ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ HOST_SERVER (Публичный IP: например 185.xxx.xxx.xxx)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ NGINX (ПУБЛИЧНЫЙ REVERSE PROXY) - Порт 443 (HTTPS)                │ │
│  │                                                                    │ │
│  │ • SSL/TLS (Let's Encrypt)                                          │ │
│  │ • API Key validation (для /api/register)                          │ │
│  │ • Rate limiting (10 req/min register, 30 req/min status)          │ │
│  │ • CORS (только домен вашего сайта)                                │ │
│  │ • Логирование запросов                                             │ │
│  │ • Fail2ban защита                                                  │ │
│  └────────────────┬───────────────────────────────────────────────────┘ │
│                   │                                                      │
│                   │ Маршруты:                                            │
│                   │ • /api/register → WireGuard VPN                      │
│                   │ • /api/server/status → WireGuard VPN                 │
│                   │                                                      │
│                   ↓                                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ WIREGUARD VPN (wg0)                                                │ │
│  │                                                                    │ │
│  │ • Туннель: HOST_SERVER ↔ WG_CLIENT                                │ │
│  │ • IP сеть: 10.8.0.x/24                                             │ │
│  │ • Шифрование трафика                                               │ │
│  │                                                                    │ │
│  │ HOST_SERVER: 10.8.0.1                                              │ │
│  │ WG_CLIENT:   10.8.0.2                                              │ │
│  └────────────────┬───────────────────────────────────────────────────┘ │
│                   │                                                      │
│                   │ Внутри VPN (10.8.0.2)                                │
│                   ↓                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                    │
      VPN туннель   │
                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ WG_CLIENT (Ваш VPS/сервер, IP в VPN: 10.8.0.2)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ TRAEFIK (Reverse Proxy внутри VPN) - Порт 1010                    │ │
│  │                                                                    │ │
│  │ • Маршрутизация по доменам/путям                                   │ │
│  │ • Load balancing                                                   │ │
│  │ • Health checks                                                    │ │
│  │                                                                    │ │
│  │ Маршруты:                                                          │ │
│  │ • /api/register → API_Father:8080                                  │ │
│  │ • /server/status → API_1:8081                                      │ │
│  └────────────────┬───────────────────────────────────────────────────┘ │
│                   │                                                      │
│                   ├──────────────────┬───────────────────────────────┐   │
│                   ↓                  ↓                               ↓   │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐│
│  │ API_Father :8080    │  │ API_1 :8081         │  │ API_4 :8084      ││
│  │                     │  │                     │  │                  ││
│  │ • Регистрация       │  │ • Статус сервера    │  │ • ML модели      ││
│  │ • Валидация         │  │ • Константы         │  │ • Статистика     ││
│  │ • Telegram check    │  │ • Game server       │  │ • Аналитика      ││
│  │ • Game server sync  │  │                     │  │                  ││
│  └──────────┬──────────┘  └──────────┬──────────┘  └────────┬─────────┘│
│             │                        │                       │          │
│             ├────────────────────────┴───────────────────────┤          │
│             ↓                                                ↓          │
│  ┌─────────────────────┐                          ┌──────────────────┐ │
│  │ MySQL :3306         │                          │ PostgreSQL :5432 │ │
│  │                     │                          │                  │ │
│  │ • Пользователи      │                          │ • Логи боев      │ │
│  │ • Telegram связи    │                          │ • Статистика     │ │
│  │ • Константы         │                          │                  │ │
│  └─────────────────────┘                          └──────────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Game Server Mock/Real :5190                                     │   │
│  │ • Создание аккаунтов                                            │   │
│  │ • Игровая логика                                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Workflow для каждого эндпоинта

### 1️⃣ `/api/register` - Регистрация пользователя

```
┌──────────────┐
│ Сайт         │ POST /api/register
│ yoursite.com │ + JSON body
└──────┬───────┘ + X-API-Key: prod_secret_key
       │
       │ HTTPS
       ↓
┌────────────────────────────────────────────────────┐
│ HOST_SERVER:443 (Nginx публичный)                  │
│                                                    │
│ 1. SSL termination (расшифровка HTTPS)            │
│ 2. Проверка X-API-Key                             │
│    ✓ Ключ валидный → продолжить                   │
│    ✗ Ключ неверный → 403 Forbidden                │
│                                                    │
│ 3. Rate limiting (10 req/min на IP)               │
│    ✓ Лимит не превышен → продолжить               │
│    ✗ Превышен → 429 Too Many Requests             │
│                                                    │
│ 4. CORS (только yoursite.com)                     │
│    ✓ Origin разрешен → добавить заголовки         │
│    ✗ Origin не разрешен → блокировать             │
└────────┬───────────────────────────────────────────┘
         │
         │ HTTP (внутри VPN, зашифровано WireGuard)
         ↓
┌────────────────────────────────────────────────────┐
│ WG_CLIENT:1010 (Traefik)                           │
│                                                    │
│ 5. Маршрутизация по пути                          │
│    /api/register → API_Father:8080                 │
└────────┬───────────────────────────────────────────┘
         │
         │ HTTP (внутренняя Docker сеть)
         ↓
┌────────────────────────────────────────────────────┐
│ API_Father:8080 (FastAPI)                          │
│                                                    │
│ 6. Валидация JSON (Pydantic)                      │
│    • login: 3-16 символов                         │
│    • password: 6-20 символов                      │
│    • gender: 0 или 1                              │
│    • telegram_id: integer                         │
│                                                    │
│ 7. Бизнес-логика:                                 │
│    a) Проверка Telegram группы (если включено)    │
│       ✓ В группе → продолжить                     │
│       ✗ Не в группе → 403 not_in_telegram_group   │
│                                                    │
│    b) Проверка лимита (< 5 аккаунтов)            │
│       ✓ < 5 → продолжить                          │
│       ✗ >= 5 → 403 limit_exceeded                 │
│                                                    │
│    c) Проверка уникальности логина                │
│       ✓ Свободен → продолжить                     │
│       ✗ Занят → 409 login_taken                   │
│                                                    │
│ 8. Создание в БД (MySQL)                          │
│    • INSERT в players                             │
│    • INSERT в telegram_players                    │
└────────┬───────────────────────────────────────────┘
         │
         │ Socket (TCP)
         ↓
┌────────────────────────────────────────────────────┐
│ Game Server:5190                                   │
│                                                    │
│ 9. Создание игрового аккаунта                     │
│    • Отправка команды регистрации                 │
│    • Получение подтверждения                      │
└────────┬───────────────────────────────────────────┘
         │
         │ Ответ обратно
         ↓
┌────────────────────────────────────────────────────┐
│ API_Father                                         │
│                                                    │
│ 10. Формирование ответа                           │
│     {"ok": true, "message": "Регистрация успешна!"}│
└────────┬───────────────────────────────────────────┘
         │
         ↓ (через Traefik → VPN → Nginx)
┌────────────────────────────────────────────────────┐
│ Сайт получает:                                     │
│ HTTP 200 OK                                        │
│ {"ok": true, "message": "Регистрация успешна!"}    │
└────────────────────────────────────────────────────┘
```

**Время выполнения:** ~500ms - 2s (зависит от Game Server)

---

### 2️⃣ `/api/server/status` - Статус сервера

```
┌──────────────┐
│ Сайт         │ GET /api/server/status
│ yoursite.com │ (БЕЗ API ключа!)
└──────┬───────┘
       │
       │ HTTPS
       ↓
┌────────────────────────────────────────────────────┐
│ HOST_SERVER:443 (Nginx публичный)                  │
│                                                    │
│ 1. SSL termination                                │
│ 2. Rate limiting (30 req/min на IP)               │
│ 3. CORS (только yoursite.com)                     │
└────────┬───────────────────────────────────────────┘
         │
         │ HTTP (внутри VPN)
         ↓
┌────────────────────────────────────────────────────┐
│ WG_CLIENT:8081 (API_1) - НАПРЯМУЮ!                │
│                                                    │
│ 4. Получение констант из MySQL                    │
│    • server_status                                │
│    • rates (exp, pvp, pve...)                     │
│    • client_status                                │
│                                                    │
│ 5. Формирование JSON ответа                       │
└────────┬───────────────────────────────────────────┘
         │
         ↓ (через VPN → Nginx)
┌────────────────────────────────────────────────────┐
│ Сайт получает:                                     │
│ HTTP 200 OK                                        │
│ {                                                  │
│   "server_status": 1.0,                           │
│   "rates": {...},                                 │
│   "client_status": 256.0                          │
│ }                                                  │
└────────────────────────────────────────────────────┘
```

**Время выполнения:** ~50ms - 200ms (быстро, т.к. только БД запрос)

---

## 🔐 Безопасность Production

### Уровень 1: Nginx (Публичный)

```nginx
# SSL/TLS
ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;

# API Key для /api/register
if ($http_x_api_key != "YOUR_PROD_SECRET_KEY") {
    return 403;
}

# Rate Limiting
limit_req_zone $binary_remote_addr zone=register:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=status:10m rate=30r/m;

# CORS (только ваш домен!)
add_header 'Access-Control-Allow-Origin' 'https://yoursite.com' always;

# Логирование
access_log /var/log/nginx/api-access.log api_log;
error_log /var/log/nginx/api-error.log warn;
```

### Уровень 2: WireGuard VPN

```
• Шифрование: ChaCha20-Poly1305
• Аутентификация: Curve25519
• Только разрешенные IP могут подключиться
• Туннель HOST_SERVER ↔ WG_CLIENT
```

### Уровень 3: API (Внутри VPN)

```python
# Валидация полей (Pydantic)
class RegisterRequest(BaseModel):
    login: constr(min_length=3, max_length=16)
    password: constr(min_length=6, max_length=20)
    gender: int = Field(ge=0, le=1)
    telegram_id: int

# Бизнес-логика
if count_accounts(telegram_id) >= 5:
    raise HTTPException(403, "limit_exceeded")

if is_login_taken(login):
    raise HTTPException(409, "login_taken")
```

### Уровень 4: Database

```sql
-- Уникальные индексы
CREATE UNIQUE INDEX idx_login ON players(login);
CREATE INDEX idx_telegram_id ON telegram_players(telegram_id);

-- Ограничения на уровне БД
ALTER TABLE players ADD CONSTRAINT check_login_length 
    CHECK (CHAR_LENGTH(login) >= 3 AND CHAR_LENGTH(login) <= 16);
```

---

## 📊 Мониторинг Production

### 1. Nginx Metrics

```bash
# Доступ к статистике
curl https://api.yourdomain.com/nginx_status

# Анализ логов
tail -f /var/log/nginx/api-access.log | grep "status=403"

# Топ IP адресов
awk '{print $1}' /var/log/nginx/api-access.log | sort | uniq -c | sort -rn | head -20
```

### 2. API Health Checks

```bash
# Проверка доступности
curl https://api.yourdomain.com/health
# {"status": "ok"}

# Мониторинг через cron (каждую минуту)
* * * * * curl -s https://api.yourdomain.com/health || send_alert
```

### 3. Database Monitoring

```sql
-- Количество регистраций за последний час
SELECT COUNT(*) FROM telegram_players 
WHERE created_at > NOW() - INTERVAL 1 HOUR;

-- Топ пользователей по количеству аккаунтов
SELECT telegram_id, username, COUNT(*) as accounts 
FROM telegram_players 
GROUP BY telegram_id 
ORDER BY accounts DESC 
LIMIT 10;
```

### 4. Fail2ban (защита от брутфорса)

```ini
# /etc/fail2ban/jail.local
[nginx-api]
enabled = true
filter = nginx-api
logpath = /var/log/nginx/api-access.log
maxretry = 20
findtime = 300
bantime = 3600
```

---

## 🚀 Deployment Production

### Шаг 1: Настройка HOST_SERVER

```bash
# 1. Обновление системы
sudo apt update && sudo apt upgrade -y

# 2. Установка Nginx
sudo apt install nginx certbot python3-certbot-nginx -y

# 3. Настройка DNS
# A запись: api.yourdomain.com → PUBLIC_IP_HOST_SERVER

# 4. Получение SSL
sudo certbot --nginx -d api.yourdomain.com

# 5. Копирование prod конфига
sudo cp nginx.prod.conf /etc/nginx/sites-available/api-proxy
sudo ln -s /etc/nginx/sites-available/api-proxy /etc/nginx/sites-enabled/

# 6. Замена плейсхолдеров
sudo nano /etc/nginx/sites-available/api-proxy
# Заменить: api.yourdomain.com, YOUR_SECRET_KEY, https://yoursite.com, 10.8.0.2

# 7. Перезапуск Nginx
sudo nginx -t && sudo systemctl reload nginx

# 8. Настройка Firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Шаг 2: Настройка WG_CLIENT

```bash
# 1. Проверка что все сервисы запущены
docker ps

# 2. Проверка подключения к HOST_SERVER через VPN
ping 10.8.0.1

# 3. Тест эндпоинтов изнутри
curl http://localhost:8080/internal/health
curl http://localhost:8081/server/status
```

### Шаг 3: Обновление .env на сайте

```javascript
// Production конфиг
const API_CONFIG = {
  baseUrl: 'https://api.yourdomain.com',  // Публичный URL
  apiKey: process.env.NEXT_PUBLIC_API_KEY  // Из переменных окружения!
};
```

---

## 🔄 Автоматическое обновление

### SSL автообновление (Let's Encrypt)

```bash
# Certbot автоматически создает cron job
sudo certbot renew --dry-run  # Тест

# Проверка таймера
sudo systemctl list-timers | grep certbot
```

### API автозапуск (systemd)

```bash
# Docker services стартуют автоматически с флагом restart: unless-stopped
```

---

## 🧪 Тестирование Production

### Из браузера

```
https://api.yourdomain.com/api/server/status
```

### С хостинга сайта

```bash
curl https://api.yourdomain.com/api/server/status

curl -X POST https://api.yourdomain.com/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_PROD_KEY" \
  -d '{...}'
```

### Проверка SSL

```bash
# SSL Labs
https://www.ssllabs.com/ssltest/analyze.html?d=api.yourdomain.com

# OpenSSL
openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com
```

---

## 📈 Масштабирование

### Вертикальное (больше ресурсов)

```yaml
# docker-compose.yml
services:
  api_father:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

### Горизонтальное (больше инстансов)

```yaml
services:
  api_father:
    deploy:
      replicas: 3  # 3 инстанса API_Father
```

```nginx
# Nginx load balancing
upstream wg_api {
    server 10.8.0.2:1010;
    server 10.8.0.3:1010;  # Второй WG_CLIENT
    server 10.8.0.4:1010;  # Третий WG_CLIENT
}
```

---

## ⚠️ Важные моменты Production

### 1. API Ключ

```bash
# Генерация безопасного ключа
openssl rand -base64 32

# НЕ коммитить в Git!
# Использовать переменные окружения
```

### 2. CORS

```nginx
# PROD: ТОЛЬКО ваш домен!
add_header 'Access-Control-Allow-Origin' 'https://yoursite.com' always;

# DEV: Можно *
add_header 'Access-Control-Allow-Origin' '*' always;
```

### 3. Rate Limiting

```nginx
# Настройте под вашу нагрузку
limit_req_zone ... rate=10r/m;  # Для регистрации
limit_req_zone ... rate=30r/m;  # Для статуса сервера
```

### 4. Логи

```bash
# Ротация логов
sudo nano /etc/logrotate.d/nginx-api

/var/log/nginx/api-*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        systemctl reload nginx > /dev/null
    endscript
}
```

---

## 📚 Документация

- [Production Setup](PRODUCTION_SETUP.md) - Детальная инструкция
- [API Spec](REGISTRATION_API_SPEC.md) - Спецификация API
- [Error Messages](ERROR_MESSAGES_FOR_SITE.md) - Обработка ошибок
- [Ngrok Testing](NGROK_TESTING.md) - Тестирование

---

## ✅ Чеклист Production

- [ ] DNS настроен (A запись)
- [ ] SSL сертификат получен (Let's Encrypt)
- [ ] Nginx конфиг настроен и проверен
- [ ] API ключ сгенерирован и сохранен
- [ ] CORS настроен на конкретный домен
- [ ] Rate limiting настроен
- [ ] Firewall настроен (только 80, 443)
- [ ] Fail2ban настроен
- [ ] Логирование настроено
- [ ] Мониторинг настроен
- [ ] SSL автообновление работает
- [ ] Протестировано с публичного интернета
- [ ] Backup БД настроен
- [ ] Документация обновлена

---

**Готово к production!** 🚀



