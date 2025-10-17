# API 5 - Quick Start Guide

## 🚀 Быстрый запуск

API 5 использует **те же ключи авторизации** что и XML Workers!

### 1. Переменные окружения

Shop Workers используют существующие переменные из XML Workers:

```bash
# Те же переменные что в HOST_API_SERVICE_XML_WORKERS.yml
SOVA_MOSCOW_LOGIN=Sova
SOVA_MOSCOW_KEY=<ваш ключ>

SOVA_OASIS_LOGIN=Sova
SOVA_OASIS_KEY=<ваш ключ>

SOVA_NEVA_LOGIN=Sova
SOVA_NEVA_KEY=<ваш ключ>
```

### 2. Запуск через Docker

```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client

# Запуск API 5 с БД
bash tools/ctl.sh api5-up-db

# Проверка
curl http://localhost:8085/healthz
curl http://localhost:8085/docs
```

### 3. Запуск воркеров

```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client/api_5

# Все 3 воркера сразу
python shop_workers/run_workers.py

# Или отдельно
python shop_workers/moscow_worker.py
```

### 4. API Endpoints

```bash
# Health
curl http://localhost:8085/healthz
curl http://localhost:8085/shop/health

# Товары
curl "http://localhost:8085/items/list?shop_code=moscow&limit=10"
curl http://localhost:8085/items/123456

# Снимки
curl http://localhost:8085/snapshots/latest?shop_code=moscow

# Статус ботов
curl http://localhost:8085/admin/bots/status

# Swagger UI
open http://localhost:8085/docs
```

## 🔐 Авторизация

Shop Workers используют **точно ту же схему авторизации** что и XML Workers:

1. Подключение к `185.92.72.18:5190`
2. Отправка `<LOGIN ... p="{LOGIN_KEY}" l="{LOGIN_NAME}" />`
3. Получение ответа
4. Отправка `<GETME />`
5. Keep-alive через `<N />`

## 📡 Протокол магазина

Вместо команды `//blook {battle_id}` используется:

```xml
<SH c="k" s="" p="0" />
```

Где:
- `c` — категория (k, p, v, h, ...)
- `s` — фильтр (для групп)
- `p` — страница (с 0)

## 🎯 Различия с XML Workers

| XML Workers | Shop Workers |
|-------------|--------------|
| Получают логи боёв | Парсят магазины |
| Команда `//blook ID` | Команда `<SH c="..." />` |
| Ответ `<BLOOK>` | Ответ `<SH><O /></SH>` |
| 6 воркеров | 3 воркера (по магазину) |
| Батч запросы | Последовательные запросы |

## ✅ Готово!

API 5 полностью интегрирован и использует ту же инфраструктуру авторизации что и XML Workers.







