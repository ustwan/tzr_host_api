# 🔐 Nginx Reverse Proxy для API Регистрации

Reverse proxy с **API Key authentication** и **rate limiting** для защищенного доступа к API регистрации извне VPN.

---

## 📋 Содержание

1. [Архитектура](#архитектура)
2. [Локальная разработка](#локальная-разработка)
3. [Production деплой](#production-деплой)
4. [API Key Management](#api-key-management)
5. [Тестирование](#тестирование)
6. [Мониторинг](#мониторинг)
7. [Безопасность](#безопасность)

---

## 🏗️ Архитектура

```
┌─────────────────────┐
│  ВНЕШНИЙ КЛИЕНТ     │  (Сайт, приложение)
│  (публичный)        │
└──────────┬──────────┘
           │ HTTPS + API Key
           │ X-API-Key: secret_key_here
           ↓
┌──────────────────────────────────────────────────┐
│ NGINX REVERSE PROXY                              │
├──────────────────────────────────────────────────┤
│ ✓ SSL/TLS терминация                             │
│ ✓ API Key validation                             │
│ ✓ Rate limiting (10 req/min)                     │
│ ✓ CORS headers                                   │
│ ✓ Security headers                               │
└──────────┬───────────────────────────────────────┘
           │ HTTP (внутри VPN)
           ↓
┌──────────────────────────────────────────────────┐
│ WG_CLIENT API                                    │
│ (Traefik → API_2 → API_FATHER)                  │
└──────────────────────────────────────────────────┘
```

---

## 🧪 Локальная разработка

### 1. Структура файлов

```
nginx_proxy/
├── docker-compose.yml          # Docker Compose для локального nginx
├── nginx.dev.fixed.conf        # Конфиг для разработки (HTTP)
├── nginx.prod.conf             # Конфиг для продакшн (HTTPS)
├── test_api.sh                 # Полный набор тестов
├── test_simple.sh              # Простой тест регистрации
├── logs/                       # Логи nginx (создается автоматически)
└── README.md                   # Эта документация
```

### 2. Запуск локального proxy

**Шаг 1: Убедитесь, что WG_CLIENT API запущен**

```bash
# В основной директории wg_client
cd /Users/ii/Documents/code/WG_HUB/wg_client

# Traefik должен слушать на :1010
curl -s http://localhost:1010/api/register/health | jq
# Ответ: {"status": "ok"}
```

**Шаг 2: Запустите nginx proxy**

```bash
# Из директории wg_client
docker compose -f nginx_proxy/docker-compose.yml up -d

# Проверить статус
docker compose -f nginx_proxy/docker-compose.yml ps

# Проверить логи
docker compose -f nginx_proxy/docker-compose.yml logs -f nginx_proxy
```

**Шаг 3: Проверить доступность**

```bash
# Health check (без API ключа)
curl http://localhost:8080/api/register/health
# {"status": "ok"}

# Nginx status
curl http://localhost:8080/nginx_status
```

### 3. Тестирование

**Полный набор тестов:**

```bash
chmod +x nginx_proxy/test_api.sh
./nginx_proxy/test_api.sh
```

**Быстрый тест регистрации:**

```bash
chmod +x nginx_proxy/test_simple.sh
./nginx_proxy/test_simple.sh
```

**Ручной тест с curl:**

```bash
# С правильным API ключом
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -H "X-Request-Id: $(uuidgen)" \
  -d '{
    "login": "ТестИгрок",
    "password": "test123456",
    "gender": 1,
    "telegram_id": 999999999,
    "username": "test_user"
  }' | jq

# Без API ключа (должен вернуть 403)
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "login": "ТестИгрок",
    "password": "test123456",
    "gender": 1,
    "telegram_id": 999999999
  }'
# {"error": "invalid_api_key", "message": "API key is missing or invalid"}
```

### 4. Остановка

```bash
docker compose -f nginx_proxy/docker-compose.yml down
```

---

## 🚀 Production деплой

### 1. На HOST_SERVER (где WG-HUB)

**Установка nginx:**

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y
```

### 2. Генерация API ключа

```bash
# Генерируем случайный секретный ключ
API_KEY=$(openssl rand -base64 32)
echo "Ваш API ключ: $API_KEY"

# Сохраните его в безопасное место!
# Например: /root/.api_keys/registration_api_key
```

### 3. Настройка конфига

```bash
# Копируем продакшн конфиг
sudo cp nginx_proxy/nginx.prod.conf /etc/nginx/sites-available/api-proxy

# ВАЖНО: Редактируем конфиг
sudo nano /etc/nginx/sites-available/api-proxy
```

**Замените в конфиге:**

1. `api.yourdomain.com` → ваш реальный домен
2. `REPLACE_WITH_YOUR_SECRET_API_KEY_HERE` → ваш сгенерированный API ключ
3. `https://yourwebsite.com` → домен вашего сайта (для CORS)
4. `server 10.8.0.2:80` → IP вашего WG_CLIENT внутри VPN

**Узнать IP WG_CLIENT:**

```bash
# На HOST_SERVER
sudo wg show wg0 peers
# Найдите allowed-ips для вашего клиента
```

### 4. Получение SSL сертификата

```bash
# Активируем конфиг
sudo ln -s /etc/nginx/sites-available/api-proxy /etc/nginx/sites-enabled/

# Тестовый запуск без SSL (для ACME challenge)
sudo nginx -t
sudo systemctl reload nginx

# Получаем SSL сертификат
sudo certbot --nginx -d api.yourdomain.com

# Certbot автоматически настроит SSL в конфиге
```

### 5. Запуск

```bash
# Проверка конфигурации
sudo nginx -t

# Перезапуск
sudo systemctl restart nginx

# Автозапуск
sudo systemctl enable nginx
```

### 6. Проверка

```bash
# С вашего сайта или любого публичного сервера
curl -X POST https://api.yourdomain.com/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ВАШ_API_КЛЮЧ" \
  -d '{
    "login": "ТестИгрок",
    "password": "test123456",
    "gender": 1,
    "telegram_id": 123456789
  }'
```

---

## 🔑 API Key Management

### Локальная разработка

**Dev API Key:** `dev_api_key_12345`

Этот ключ жестко закодирован в `nginx.dev.fixed.conf` для удобства тестирования.

### Production

**Генерация нового ключа:**

```bash
openssl rand -base64 32
```

**Ротация ключей:**

1. Сгенерируйте новый ключ
2. Добавьте его в nginx конфиг параллельно со старым:

```nginx
if ($http_x_api_key = "OLD_KEY") {
    set $api_key_valid 1;
}
if ($http_x_api_key = "NEW_KEY") {
    set $api_key_valid 1;
}
```

3. Обновите клиентов на новый ключ
4. Удалите старый ключ из конфига
5. Перезапустите nginx

**Хранение ключей:**

```bash
# На HOST_SERVER
sudo mkdir -p /root/.api_keys
sudo chmod 700 /root/.api_keys

# Сохраните ключ
echo "YOUR_API_KEY_HERE" | sudo tee /root/.api_keys/registration_api_key
sudo chmod 600 /root/.api_keys/registration_api_key

# Использование в конфиге через include (опционально)
```

---

## 🧪 Тестирование

### Автоматизированные тесты

**Тест 1: Health Check**
- Без API ключа
- Ожидается: 200 OK

**Тест 2: Запрос без API ключа**
- Ожидается: 403 Forbidden

**Тест 3: Неверный API ключ**
- Ожидается: 403 Forbidden

**Тест 4: Правильный API ключ**
- Ожидается: 200 OK или бизнес-ошибки (409, 403)

**Тест 5: Rate Limiting**
- 15 запросов подряд
- Ожидается: первые 13 проходят, затем 429 Too Many Requests

**Тест 6: GET запрос**
- Ожидается: 405 Method Not Allowed

### Ручное тестирование

**JavaScript (для сайта):**

```javascript
async function registerUser(login, password, gender, telegram_id) {
  const response = await fetch('https://api.yourdomain.com/api/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'YOUR_SECRET_API_KEY',
      'X-Request-Id': crypto.randomUUID()
    },
    body: JSON.stringify({
      login,
      password,
      gender,
      telegram_id,
      username: 'from_website'
    })
  });
  
  const data = await response.json();
  
  if (response.ok) {
    console.log('Регистрация успешна!', data);
    return data;
  } else {
    console.error('Ошибка регистрации:', data);
    throw new Error(data.error || 'Registration failed');
  }
}
```

**Python:**

```python
import requests

def register_user(login, password, gender, telegram_id):
    response = requests.post(
        'https://api.yourdomain.com/api/register',
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': 'YOUR_SECRET_API_KEY',
            'X-Request-Id': str(uuid.uuid4())
        },
        json={
            'login': login,
            'password': password,
            'gender': gender,
            'telegram_id': telegram_id
        }
    )
    
    return response.json()
```

**PHP:**

```php
<?php
function registerUser($login, $password, $gender, $telegram_id) {
    $data = [
        'login' => $login,
        'password' => $password,
        'gender' => $gender,
        'telegram_id' => $telegram_id
    ];
    
    $ch = curl_init('https://api.yourdomain.com/api/register');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($data),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'X-API-Key: YOUR_SECRET_API_KEY',
            'X-Request-Id: ' . uniqid('req_', true)
        ]
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    return json_decode($response, true);
}
?>
```

---

## 📊 Мониторинг

### Логи

**Локальная разработка:**

```bash
# Все логи
docker compose -f nginx_proxy/docker-compose.yml logs -f

# Только nginx
tail -f nginx_proxy/logs/access.log
tail -f nginx_proxy/logs/error.log
```

**Production:**

```bash
# Access log
sudo tail -f /var/log/nginx/api-access.log

# Error log
sudo tail -f /var/log/nginx/api-error.log

# Fail2ban log (для блокировки атак)
sudo tail -f /var/log/nginx/fail2ban.log
```

### Метрики

**Nginx status:**

```bash
# Локально
curl http://localhost:8080/nginx_status

# Production (только с сервера)
curl http://localhost/nginx_status
```

**Статистика запросов:**

```bash
# Количество запросов по кодам
sudo awk '{print $9}' /var/log/nginx/api-access.log | sort | uniq -c | sort -rn

# Top 10 IP адресов
sudo awk '{print $1}' /var/log/nginx/api-access.log | sort | uniq -c | sort -rn | head -10

# Rate limited запросы (429)
sudo grep " 429 " /var/log/nginx/api-access.log | wc -l

# Invalid API keys (403)
sudo grep " 403 " /var/log/nginx/api-access.log | tail -20
```

---

## 🔒 Безопасность

### Rate Limiting

**Настройки:**
- `register_limit`: 10 запросов/минуту с одного IP
- `burst`: 3 дополнительных запроса
- `health_limit`: 30 запросов/минуту

**Изменить лимиты:**

```nginx
# В nginx конфиге
limit_req_zone $binary_remote_addr zone=register_limit:10m rate=5r/m;  # 5 req/min
```

### API Key Best Practices

1. **Длина:** минимум 32 байта (base64)
2. **Ротация:** каждые 90 дней
3. **Хранение:** никогда не коммитить в Git
4. **Передача:** только HTTPS в продакшн
5. **Логирование:** не логировать полный ключ

### CORS

**Локальная разработка:** разрешен `*`

**Production:** только ваш домен
```nginx
add_header 'Access-Control-Allow-Origin' 'https://yourwebsite.com' always;
```

### Fail2ban (опционально)

Защита от брутфорса:

```bash
# /etc/fail2ban/filter.d/nginx-api.conf
[Definition]
failregex = ^<HOST> .* "(POST|GET) /api/register.*" (403|429)
ignoreregex =

# /etc/fail2ban/jail.local
[nginx-api]
enabled = true
filter = nginx-api
logpath = /var/log/nginx/fail2ban.log
maxretry = 20
findtime = 300
bantime = 3600
```

---

## 🐛 Troubleshooting

### Проблема: 502 Bad Gateway

**Причина:** nginx не может подключиться к WG_CLIENT API

**Решение:**
```bash
# Проверьте, что API доступен
curl http://localhost:1010/api/register/health

# Проверьте IP в nginx конфиге
grep "server.*:80" /etc/nginx/sites-available/api-proxy

# Проверьте WireGuard
sudo wg show
```

### Проблема: 403 на валидный API ключ

**Причина:** ключ не совпадает с конфигом

**Решение:**
```bash
# Проверьте ключ в конфиге
sudo grep "http_x_api_key" /etc/nginx/sites-available/api-proxy

# Проверьте переданный ключ
curl -v -H "X-API-Key: YOUR_KEY" ...
```

### Проблема: CORS ошибки

**Решение:**
```nginx
# Убедитесь, что домен сайта в CORS
add_header 'Access-Control-Allow-Origin' 'https://yourwebsite.com' always;
```

---

## 📚 Дополнительные ресурсы

- [Nginx Rate Limiting](http://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [Let's Encrypt](https://letsencrypt.org/getting-started/)
- [CORS Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

---

## ✅ Чеклист деплоя

### Локальная разработка
- [ ] WG_CLIENT API запущен на :1010
- [ ] `docker compose up -d` для nginx
- [ ] Health check работает
- [ ] Тесты пройдены (`./test_api.sh`)

### Production
- [ ] Nginx установлен
- [ ] API ключ сгенерирован и сохранен
- [ ] Конфиг отредактирован (домен, API ключ, CORS)
- [ ] SSL сертификат получен
- [ ] Firewall настроен (порты 80, 443)
- [ ] DNS A-запись создана
- [ ] Тесты пройдены с публичного IP
- [ ] Мониторинг настроен

---

**Поддержка:** Для вопросов обращайтесь к документации `REGISTRATION_COMPLETE_GUIDE.md`

