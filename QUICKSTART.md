# 🚀 TZR Host API - Быстрый старт

## 📋 Что это?

**TZR Host API** - микросервисная архитектура игрового сервера с:
- 🔐 **Site Agent** - WebSocket мост между сайтом и API
- 🎮 **API сервисы** - регистрация, статус, битвы, магазин
- 🌐 **Clean Architecture** - чистая архитектура с разделением слоев
- 🔒 **Безопасность** - HMAC, AES-GCM, JWT

## ⚡ Быстрый запуск

### 1. Требования

```bash
- Docker & Docker Compose
- Python 3.11+
- Linux (для production)
```

### 2. Клонирование

```bash
git clone https://github.com/ustwan/tzr_host_api.git
cd tzr_host_api/wg_client
```

### 3. Конфигурация

```bash
# Перейти в рабочую директорию
cd wg_client

# Скопировать примеры
cp env.example .env

# Редактировать .env
nano .env
```

**Минимальные настройки:**
```bash
# База данных
DB_MODE=test  # или prod

# Сети
TZ=Europe/Moscow
```

### 4. Запуск (одной командой!)

```bash
# Запустить ВСЁ автоматически (тестовый режим)
bash tools/ctl.sh start-test

# ИЛИ запустить в продакшн режиме
bash tools/ctl.sh start-prod

# ИЛИ просто всё (по умолчанию)
bash tools/ctl.sh start-all
```

**Скрипт автоматически:**
- ✅ Создаст все Docker сети
- ✅ Запустит инфраструктуру (Redis, PostgreSQL, MySQL)
- ✅ Запустит API Father (оркестратор)
- ✅ Запустит все API сервисы (API_1-5)
- ✅ Запустит Workers и XML Workers
- ✅ Запустит мониторинг

### 5. Проверка

```bash
# Статус всех сервисов (красивая таблица)
bash tools/ctl.sh status

# Логи всех сервисов
bash tools/ctl.sh logs

# Логи конкретного сервиса
bash tools/ctl.sh logs api_father
bash tools/ctl.sh logs api_2

# Проверить API
curl http://localhost:9000/internal/health
curl http://localhost:8082/health
```

### 6. Управление

```bash
# Остановить всё
bash tools/ctl.sh stop-all

# Остановить и удалить (с volumes)
bash tools/ctl.sh down-all

# Перезапустить сервис
bash tools/ctl.sh restart api_2

# Диагностика
bash tools/ctl.sh doctor

# Применить миграции
bash tools/ctl.sh migrate
```

## 🌟 Site Agent (для сайта)

### Конфигурация

```bash
cd wg_client/site_agent
cp env.example .env
nano .env
```

**Обязательные переменные:**
```bash
SITE_WS_URL=wss://site.example.com/ws/pull
AUTH_JWT=<JWT токен от сайта>
HMAC_SECRET=<общий секрет>
AES_GCM_KEY=<base64 ключ>
```

### Генерация секретов

```bash
# HMAC секрет (hex, 64 символа)
openssl rand -hex 32

# AES-GCM ключ (base64, 44 символа)
openssl rand -base64 32
```

### Запуск агента

```bash
cd wg_client
docker compose -f HOST_API_SERVICE_SITE_AGENT.yml up -d

# Логи
docker logs -f site_agent
```

## 📚 Структура проекта

```
tzr_host_api/
├── wg_client/           # Основной код
│   ├── api_1/          # Статус сервера
│   ├── api_2/          # Регистрация
│   ├── api_4/          # Битвы и аналитика
│   ├── api_5/          # Магазин
│   ├── api_father/     # Оркестратор
│   ├── site_agent/     # WebSocket агент для сайта
│   └── *.yml           # Docker Compose файлы
├── scripts/            # Утилиты управления
├── MAIN_README.md      # Полная документация
└── QUICKSTART.md       # Этот файл
```

## 🔧 Основные команды

```bash
# Логи всех сервисов
docker compose -f HOST_API_SERVICE_INFRASTRUCTURE.yml logs -f

# Перезапуск API
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml restart api_2

# Остановка всего
docker compose -f HOST_API_SERVICE_INFRASTRUCTURE.yml down
docker compose -f HOST_API_SERVICE_FATHER_API.yml down
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml down
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml down
```

## 📖 Документация

- **[MAIN_README.md](MAIN_README.md)** - Полная техническая документация
- **[wg_client/site_agent/README.md](wg_client/site_agent/README.md)** - Site Agent
- **[wg_client/nginx_proxy/API_FOR_WEBSITE.md](wg_client/nginx_proxy/API_FOR_WEBSITE.md)** - API для сайта

## 🆘 Помощь

### Проблемы с Docker

```bash
# Проверить сети
docker network ls
docker network inspect host-api-network

# Пересоздать сеть
docker network rm host-api-network
docker network create host-api-network
```

### Проблемы с БД

```bash
# Проверить MySQL
docker logs api_father_mysql

# Подключиться к БД
docker exec -it api_father_mysql mysql -u zero -p
```

### Проблемы с Site Agent

```bash
# Детальные логи
docker logs site_agent -f

# Проверить переменные
docker exec site_agent env | grep -E "SITE_|HMAC_|AES_"
```

## 🎯 Следующие шаги

1. ✅ Запустить базовую инфраструктуру
2. ✅ Настроить Site Agent (если нужен сайт)
3. 📖 Прочитать [MAIN_README.md](MAIN_README.md) для деталей
4. 🔐 Настроить production секреты
5. 🚀 Деплой на production сервер

---

**Репозиторий:** https://github.com/ustwan/tzr_host_api  
**Версия:** 1.0.0  
**Дата:** Октябрь 2025

