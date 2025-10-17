# Site Agent - WebSocket Агент для взаимодействия с сайтом

## 📋 Описание

**Site Agent** - это WebSocket клиент-агент, который работает на **Хосте 2** и обеспечивает:

- 🔒 **Безопасное исходящее** WebSocket соединение к сайту (wss://)
- 🔐 **JWT авторизация** и **HMAC подпись** всех сообщений
- 🔑 **AES-GCM расшифровка** паролей для безопасной регистрации
- ♻️ **Идемпотентность** через request_id (защита от дублей)
- 🔄 **Auto-reconnect** с exponential backoff (3-30 секунд)
- 📊 **Мониторинг** и детальное логирование

## 🏗️ Архитектура

Агент построен по принципам **Clean Architecture**:

```
site_agent/
├── app/
│   ├── domain/              # DTO, entities
│   │   └── dto.py          # JobMessage, ResultMessage, ...
│   ├── usecases/            # Бизнес-логика
│   │   ├── process_register.py
│   │   └── process_server_status.py
│   ├── ports/               # Интерфейсы
│   │   ├── crypto.py       # HmacSigner, AesGcmCrypto
│   │   ├── websocket_client.py
│   │   └── local_api_client.py
│   ├── adapters/            # Реализации портов
│   │   ├── hmac_signer.py  # HMAC-SHA256
│   │   ├── aes_gcm_crypto.py  # AES-GCM 256
│   │   ├── ws_client.py    # WebSocket с auto-reconnect
│   │   └── http_local_api_client.py
│   ├── interfaces/          # Точки входа
│   │   └── main.py         # SiteAgent orchestrator
│   └── infrastructure/      # Конфигурация
│       └── config.py       # Загрузка из ENV
├── Dockerfile
├── requirements.txt
└── env.example
```

## 🚀 Быстрый старт

### 1. Конфигурация

Скопируйте `env.example` и заполните секреты:

```bash
cd wg_client/site_agent
cp env.example .env
nano .env
```

**Обязательные переменные:**
```bash
SITE_WS_URL=wss://site.example.com/ws/pull
AUTH_JWT=<JWT токен от сайта>
HMAC_SECRET=<общий секрет с сайтом>
AES_GCM_KEY=<base64 encoded AES-256 ключ>
```

**Генерация секретов:**
```bash
# HMAC секрет (hex)
openssl rand -hex 32

# AES-GCM ключ (base64)
openssl rand -base64 32
```

### 2. Локальная разработка (без Docker)

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск
python -m app.interfaces.main
```

### 3. Docker Compose

```bash
# Из корня wg_client/
docker compose -f HOST_API_SERVICE_SITE_AGENT.yml up -d

# Логи
docker logs -f site_agent

# Остановка
docker compose -f HOST_API_SERVICE_SITE_AGENT.yml down
```

## 🔌 Интеграция с существующими API

Агент вызывает **локальные API** внутри WG_HUB:

### Регистрация
```
POST http://api_2:8082/register
Headers: X-Request-Id: <job_id>
Body: {
  "login": "...",
  "password": "...",  # Расшифрованный!
  "gender": 0 | 1,
  "telegram_id": 123456,
  "username": "..."
}
```

### Статус сервера
```
GET http://api_father:9000/internal/constants
Response: {
  "ServerStatus": {"value": 1.0, "description": "..."},
  "RateExp": {"value": 2.0, "description": "..."},
  ...
}
```

## 📡 Протокол WebSocket

### Задача от сайта (Job)
```json
{
  "type": "job",
  "id": "uuid-1234",
  "job_type": "register" | "get_server_status",
  "payload": {
    "login": "Игрок",
    "password_encrypted": "base64(aes-gcm-encrypted-password)",
    "gender": 1,
    "telegram_id": 999999
  },
  "ts": 1734370000,
  "nonce": "uuid-5678",
  "sig": "hmac-sha256-hex"
}
```

### Ответ агента (Result)
```json
{
  "type": "result",
  "id": "uuid-1234",
  "ok": true,
  "result": {
    "user_id": 12345
  },
  "error": null,
  "ts": 1734370002,
  "nonce": "uuid-9012",
  "sig": "hmac-sha256-hex"
}
```

## 🔒 Безопасность

### HMAC Подпись
- Алгоритм: **HMAC-SHA256**
- Canonical JSON: sorted keys, no spaces
- Constant-time сравнение (защита от timing attacks)

### AES-GCM Шифрование
- Ключ: **256 бит** (32 байта)
- Формат зашифрованных данных: `base64(nonce[12] || tag[16] || ciphertext)`
- Nonce: случайные 96 бит (12 байт) для каждого шифрования
- Tag: AEAD authentication tag (128 бит)

### TTL и Nonce
- TTL задачи: **45 секунд** (настраивается)
- Nonce: уникальный UUID для каждого сообщения (защита от replay)

### Идемпотентность
- Регистрация использует `request_id = job.id`
- Повторные запросы с тем же ID не создают дубли в БД
- API_Father обрабатывает идемпотентность через X-Request-Id

## 📊 Логирование

Агент логирует:
- ✅ Подключение/разрыв WebSocket
- ✅ Получение задач (тип, ID)
- ✅ Обработка задач (результат, длительность)
- ✅ Ошибки (валидация, сеть, локальные API)
- ✅ Метрики (таймауты, backoff, переподключения)

**Формат логов:**
```
2025-10-16 19:20:05 INFO [site_agent] 🚀 WebSocket Agent запускается...
2025-10-16 19:20:05 INFO [site_agent] ✅ WebSocket подключен
2025-10-16 19:20:10 INFO [site_agent] 📥 Получена задача: register (id=abc-123)
2025-10-16 19:20:11 INFO [site_agent] ✅ Регистрация успешна: Игрок (user_id=12345, duration=0.82s)
2025-10-16 19:20:11 INFO [site_agent] 📤 Отправлен результат для задачи abc-123
```

## 🔧 Настройка переменных окружения

| Переменная | Описание | Дефолт | Обязательна |
|-----------|----------|--------|-------------|
| `SITE_WS_URL` | WSS URL сайта | - | ✅ |
| `AUTH_JWT` | JWT токен | - | ✅ |
| `HMAC_SECRET` | HMAC секрет (hex) | - | ✅ |
| `AES_GCM_KEY` | AES ключ (base64) | - | ✅ |
| `LOCAL_REGISTER_URL` | URL API регистрации | `http://api_2:8082/register` | ❌ |
| `LOCAL_STATUS_URL` | URL API статуса | `http://api_father:9000/internal/constants` | ❌ |
| `REQUEST_TIMEOUT` | Таймаут HTTP запросов | `8.0` | ❌ |
| `WS_PING_INTERVAL` | Интервал ping (сек) | `20.0` | ❌ |
| `RECONNECT_BACKOFF_MIN` | Мин backoff (сек) | `3.0` | ❌ |
| `RECONNECT_BACKOFF_MAX` | Макс backoff (сек) | `30.0` | ❌ |
| `JOB_TTL` | TTL задачи (сек) | `45` | ❌ |
| `LOG_LEVEL` | Уровень логов | `INFO` | ❌ |

## 🧪 Тестирование

### Unit тесты
```bash
pytest tests/unit/ -v
```

### Integration тесты (требуют локальные API)
```bash
# Запустить API_2 и API_Father
docker compose -f HOST_API_SERVICE_FATHER_API.yml up -d
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d

# Тесты
pytest tests/integration/ -v
```

### Тест-кейсы по ТЗ

✅ **1. Регистрация успешна**
- Принят job type=register
- Пароль расшифрован AES-GCM
- Локальный API вернул user_id
- Ответ ok=true

✅ **2. Идемпотентность**
- Повторный job с тем же ID
- Локальный API не создает дубли
- Возвращает тот же user_id

✅ **3. Статус сервера**
- Принят job type=get_server_status
- Корректный JSON с rates
- revision монотонный

✅ **4. Локальный API недоступен**
- Таймаут или сетевая ошибка
- Ответ ok=false с причиной

✅ **5. Auto-reconnect**
- Разрыв WebSocket
- Автоматический реконнект ≤ 30s

## 🚨 Troubleshooting

### Ошибка: "HMAC signature invalid"
- Проверьте что `HMAC_SECRET` одинаковый на сайте и агенте
- Убедитесь что canonical JSON формат совпадает

### Ошибка: "AES-GCM decryption failed"
- Проверьте `AES_GCM_KEY` (должен быть base64 encoded 32 байта)
- Формат зашифрованных данных: `nonce[12] || tag[16] || ciphertext`

### Ошибка: "Local API timeout"
- Проверьте доступность API_2 и API_Father
- Увеличьте `REQUEST_TIMEOUT` если нужно

### Разрыв WebSocket
- Агент автоматически переподключается с backoff 3-30s
- Проверьте сетевую доступность сайта
- Проверьте валидность JWT токена

### "Job expired"
- Задача старше 45 секунд (TTL)
- Проверьте синхронизацию времени между сайтом и агентом

## 📚 Дополнительные документы

- `wg_client/nginx_proxy/API_FOR_WEBSITE.md` - Публичные API для сайта
- `wg_client/MAIN_README.md` - Общая архитектура WG_HUB
- `CLEAN_ARCHITECTURE.md` - Принципы чистой архитектуры
- `LAYERING_RULES.md` - Правила слоев

## 🎯 Roadmap

- [ ] Метрики Prometheus (подключения, задачи, ошибки)
- [ ] Graceful JWT обновление (без разрыва соединения)
- [ ] Батчинг результатов (отправка нескольких за раз)
- [ ] Поддержка дополнительных типов задач
- [ ] Health check HTTP endpoint (опционально)

---

**Версия:** 1.0.0  
**Дата:** 16 октября 2025  
**Автор:** AI Assistant

