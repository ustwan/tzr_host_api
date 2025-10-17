# TZR Host API

> Микросервисная архитектура игрового сервера с WebSocket агентом для сайта

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)](MAIN_README.md)

## 🎯 О проекте

**TZR Host API** - полнофункциональная backend-платформа для онлайн игры с:

- 🔐 **Регистрация и авторизация** с Telegram интеграцией
- 🌐 **Site Agent** - безопасный WebSocket мост между сайтом и API
- ⚔️ **Сбор и анализ игровых данных** (логи боев, статистика)
- 🤖 **ML/AI для детекции ботов** с продвинутыми алгоритмами
- 🛒 **Магазин предметов** с системой снапшотов
- 📊 **Аналитика и статистика** игроков
- 🔒 **Безопасность** - HMAC, AES-GCM, JWT

## ⚡ Быстрый старт

```bash
# Клонирование
git clone https://github.com/ustwan/tzr_host_api.git
cd tzr_host_api/wg_client

# Конфигурация
cp env.example .env

# Запуск
docker network create host-api-network
docker compose -f HOST_API_SERVICE_INFRASTRUCTURE.yml up -d
docker compose -f HOST_API_SERVICE_FATHER_API.yml up -d
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d
```

**📖 Полная инструкция:** [QUICKSTART.md](QUICKSTART.md)

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────┐
│ Фронтенд сайта                                  │
│   ↓ POST /proxy/register                        │
│ Django (Host 1)                                 │
│   ↓ Job в БД + WebSocket push                   │
│ Site Agent (Host 2) ← WebSocket агент          │
│   ↓ расшифровка + локальные API                 │
│ WG_HUB API (API_2, API_Father, и т.д.)         │
└─────────────────────────────────────────────────┘
```

## 📦 Основные компоненты

| Сервис | Описание | Порт |
|--------|----------|------|
| **Site Agent** | WebSocket агент для сайта | - |
| **API_1** | Статус сервера | 8081 |
| **API_2** | Регистрация | 8082 |
| **API_4** | Битвы и аналитика | 8084 |
| **API_5** | Магазин | 8085 |
| **API_Father** | Оркестратор | 9000 |

## 🌟 Site Agent

**WebSocket агент** для безопасного взаимодействия сайта с внутренними API:

- ✅ Исходящее WSS соединение (нет входящих портов)
- ✅ JWT авторизация
- ✅ HMAC-SHA256 подпись всех сообщений
- ✅ AES-GCM-256 расшифровка паролей
- ✅ Идемпотентность через request_id
- ✅ Auto-reconnect с exponential backoff

**Конфигурация:**
```bash
cd wg_client/site_agent
cp env.example .env

# Обязательные переменные:
SITE_WS_URL=wss://site.example.com/ws/pull
AUTH_JWT=<токен>
HMAC_SECRET=<секрет>
AES_GCM_KEY=<ключ>
```

**Документация:** [wg_client/site_agent/README.md](wg_client/site_agent/README.md)

## 🛠️ Технологии

- **Backend:** Python 3.11+ (FastAPI, asyncio)
- **Databases:** PostgreSQL, MySQL, Redis
- **ML:** scikit-learn (K-means, Isolation Forest)
- **Infrastructure:** Docker Compose, Traefik
- **Security:** HMAC-SHA256, AES-GCM-256, JWT
- **Architecture:** Clean Architecture (Domain → UseCases → Ports → Adapters)

## 📚 Документация

| Документ | Описание |
|----------|----------|
| **[QUICKSTART.md](QUICKSTART.md)** | ⭐ Быстрый старт |
| **[MAIN_README.md](MAIN_README.md)** | Полная техническая документация |
| **[wg_client/site_agent/README.md](wg_client/site_agent/README.md)** | Site Agent |
| **[wg_client/nginx_proxy/API_FOR_WEBSITE.md](wg_client/nginx_proxy/API_FOR_WEBSITE.md)** | API для сайта |

## 🔐 Безопасность

### Генерация секретов

```bash
# HMAC секрет (hex, 64 символа)
openssl rand -hex 32

# AES-GCM ключ (base64, 44 символа)
openssl rand -base64 32
```

### Важно

- ❌ Не коммитить `.env` файлы
- ✅ Использовать переменные окружения
- ✅ HTTPS в production
- ✅ Регулярно обновлять JWT токены

## 🚀 Запуск в Production

```bash
# 1. Настроить переменные окружения
cp wg_client/env.example wg_client/.env
nano wg_client/.env

# 2. Настроить секреты для Site Agent
cd wg_client/site_agent
cp env.example .env
nano .env

# 3. Запустить все сервисы
cd wg_client
docker compose -f HOST_API_SERVICE_INFRASTRUCTURE.yml up -d
docker compose -f HOST_API_SERVICE_FATHER_API.yml up -d
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d
docker compose -f HOST_API_SERVICE_SITE_AGENT.yml up -d

# 4. Проверить статус
docker ps
docker logs -f site_agent
```

## 🧪 Тестирование

```bash
# Health checks
curl http://localhost:9000/internal/health
curl http://localhost:8082/health

# Регистрация (через локальный API)
curl -X POST http://localhost:8082/register \
  -H "Content-Type: application/json" \
  -d '{"login": "Test", "password": "pass123", "gender": 1, "telegram_id": 123456}'
```

## 📊 Структура проекта

```
tzr_host_api/
├── wg_client/           # Основной код
│   ├── api_1/          # Статус сервера
│   ├── api_2/          # Регистрация
│   ├── api_4/          # Битвы и аналитика (ML)
│   ├── api_5/          # Магазин
│   ├── api_father/     # Оркестратор + БД
│   ├── site_agent/     # WebSocket агент для сайта ⭐
│   ├── nginx_proxy/    # Публичный API gateway
│   └── *.yml           # Docker Compose конфигурации
├── scripts/            # Утилиты управления
├── QUICKSTART.md       # Быстрый старт ⭐
├── MAIN_README.md      # Полная документация
└── README.md           # Этот файл
```

## 🤝 Вклад

Проект использует Clean Architecture:
- **domain** - модели и DTO
- **usecases** - бизнес-логика
- **ports** - интерфейсы
- **adapters** - реализации
- **interfaces** - точки входа

## 📞 Поддержка

- **GitHub Issues:** [github.com/ustwan/tzr_host_api/issues](https://github.com/ustwan/tzr_host_api/issues)
- **Документация:** См. `MAIN_README.md`

## 📄 Лицензия

Проприетарный проект. Все права защищены.

---

**Репозиторий:** https://github.com/ustwan/tzr_host_api  
**Версия:** 1.0.0  
**Дата:** Октябрь 2025
