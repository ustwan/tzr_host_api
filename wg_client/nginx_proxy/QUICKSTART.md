# ⚡ Быстрый старт (5 минут)

## Локальное тестирование

### 1. Запуск nginx proxy

```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client

# Запустить nginx proxy
docker compose -f nginx_proxy/docker-compose.yml up -d

# Проверить статус
docker compose -f nginx_proxy/docker-compose.yml ps
```

### 2. Проверка доступности

```bash
# Health check (без API ключа)
curl http://localhost:8090/api/register/health

# Ожидается: {"status": "ok"}
```

### 3. Тестирование

**Вариант A: Автоматический тест**

```bash
chmod +x nginx_proxy/test_api.sh
./nginx_proxy/test_api.sh
```

**Вариант B: Простой тест**

```bash
chmod +x nginx_proxy/test_simple.sh
./nginx_proxy/test_simple.sh
```

**Вариант C: Веб-интерфейс**

```bash
# Откройте в браузере
open nginx_proxy/test_page.html
# или
firefox nginx_proxy/test_page.html
```

**Вариант D: Ручной curl**

```bash
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{
    "login": "User_123",
    "password": "test123456",
    "gender": 1,
    "telegram_id": 999999999
  }' | jq
```

---

## Что внутри?

### ✅ Включено из коробки:

- **API Key authentication** (`X-API-Key: dev_api_key_12345`)
- **Rate limiting** (10 запросов/минуту)
- **CORS headers** (для фронтенда)
- **Request logging** (в `nginx_proxy/logs/`)
- **Health check** эндпоинт

### 🔧 Конфигурация:

| Параметр | Значение |
|----------|----------|
| Локальный URL | http://localhost:8090 |
| Dev API Key | `dev_api_key_12345` |
| Rate Limit | 10 req/min + 3 burst |
| Upstream | http://host.docker.internal:1010 |

---

## Остановка

```bash
docker compose -f nginx_proxy/docker-compose.yml down
```

---

## Production деплой

См. полную документацию: [README.md](README.md#production-деплой)

**Кратко:**
1. Сгенерировать API ключ: `openssl rand -base64 32`
2. Скопировать `nginx.prod.conf` на сервер
3. Заменить плейсхолдеры (домен, API ключ, CORS)
4. Получить SSL: `certbot --nginx -d api.yourdomain.com`
5. Запустить: `systemctl restart nginx`

---

## Troubleshooting

**502 Bad Gateway:**
```bash
# Проверьте, что API доступен
curl http://localhost:1010/api/register/health
```

**403 Forbidden:**
```bash
# Убедитесь, что передаете правильный API ключ
curl -v -H "X-API-Key: dev_api_key_12345" http://localhost:8090/api/register
```

**Логи:**
```bash
# Real-time логи
docker compose -f nginx_proxy/docker-compose.yml logs -f

# Или файлы
tail -f nginx_proxy/logs/access.log
tail -f nginx_proxy/logs/error.log
```

---

**Полная документация:** [README.md](README.md)

