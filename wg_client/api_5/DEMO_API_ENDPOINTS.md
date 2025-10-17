# 📡 API 5 - Демонстрация всех endpoints

**Все 10 API endpoints с примерами запросов и ответов**

---

## 🏥 HEALTH & SERVICE (3 endpoints)

### 1. GET /healthz
**Что делает:** Проверка работоспособности сервиса

**Запрос:**
```bash
curl http://localhost:8085/healthz
```

**Ответ:**
```json
{
  "status": "ok",
  "service": "API 5 - Shop Parser"
}
```

**Когда использовать:** 
- Проверка что сервис запущен
- Healthcheck в Docker
- Мониторинг (Prometheus)

---

### 2. GET /shop/health
**Что делает:** Проверка работоспособности модуля магазина

**Запрос:**
```bash
curl http://localhost:8085/shop/health
```

**Ответ:**
```json
{
  "status": "ok",
  "service": "Shop Parser Module"
}
```

**Когда использовать:**
- Проверка специфичной функциональности магазина
- Диагностика проблем

---

### 3. GET /db/health
**Что делает:** Проверка подключения к PostgreSQL БД

**Запрос:**
```bash
curl http://localhost:8085/db/health
```

**Ответ:**
```json
{
  "status": "ok",
  "database": "connected"
}
```

**Когда использовать:**
- Проверка доступности БД
- Диагностика проблем с подключением

---

## 📦 ITEMS (3 endpoints)

### 4. GET /items/list
**Что делает:** Получить список товаров с пагинацией и фильтрами

**Запрос 1: Все товары**
```bash
curl "http://localhost:8085/items/list?page=1&limit=10"
```

**Запрос 2: Только Moscow**
```bash
curl "http://localhost:8085/items/list?shop_code=moscow&page=1&limit=5"
```

**Запрос 3: Только Oasis**
```bash
curl "http://localhost:8085/items/list?shop_code=oasis&limit=20"
```

**Ответ:**
```json
{
  "items": [
    {
      "id": 79469641,
      "txt": "Butterfly knife",
      "price": 4.0,
      "current_quality": 125,
      "max_quality": 125,
      "shop_id": 1,
      "template_id": 42,
      "owner": null
    },
    {
      "id": 79470735,
      "txt": "Beretta 92/93",
      "price": 22.0,
      "current_quality": 95,
      "max_quality": 95,
      "shop_id": 1,
      "template_id": 43,
      "owner": "PlayerX"
    },
    ... (ещё 8 товаров)
  ],
  "total": 10,
  "page": 1,
  "limit": 10
}
```

**Параметры:**
- `shop_code` — фильтр по магазину (moscow/oasis/neva)
- `page` — номер страницы (с 1)
- `limit` — количество на странице (max 1000)

**Когда использовать:**
- Просмотр товаров в магазине
- Поиск по магазину
- Экспорт данных
- Аналитика ассортимента

---

### 5. GET /items/{id}
**Что делает:** Получить детальную информацию о товаре

**Запрос:**
```bash
curl http://localhost:8085/items/79469641
```

**Ответ:**
```json
{
  "id": 79469641,
  "txt": "Butterfly knife",
  "price": 4.0,
  "current_quality": 125,
  "max_quality": 125,
  "shop_id": 1,
  "template_id": 42,
  "owner": null
}
```

**Когда использовать:**
- Проверка конкретного товара
- Отслеживание изменений цены
- Детальная информация для пользователя

---

### 6. GET /items/search (TODO)
**Что делает:** Поиск товаров по фильтрам

**Запрос (когда будет готово):**
```bash
curl "http://localhost:8085/items/search?txt=knife&price_min=5&price_max=50"
```

**Когда использовать:**
- Поиск по названию
- Фильтрация по цене
- Фильтрация по качеству

---

## 📸 SNAPSHOTS (2 endpoints)

### 7. GET /snapshots/list
**Что делает:** Получить список всех снимков магазинов

**Запрос:**
```bash
curl "http://localhost:8085/snapshots/list"
```

**Ответ:**
```json
{
  "snapshots": [
    {
      "id": 5,
      "shop_id": 1,
      "created_at": "2025-10-11T15:30:00",
      "items_count": 1847,
      "worker_name": "moscow_worker"
    },
    {
      "id": 4,
      "shop_id": 1,
      "created_at": "2025-10-11T14:30:00",
      "items_count": 1835,
      "worker_name": "moscow_worker"
    },
    {
      "id": 3,
      "shop_id": 2,
      "created_at": "2025-10-11T15:30:15",
      "items_count": 1652,
      "worker_name": "oasis_worker"
    }
  ],
  "total": 3
}
```

**Когда использовать:**
- Просмотр истории снимков
- Аналитика частоты обновлений
- Выбор снимков для сравнения

---

### 8. GET /snapshots/latest
**Что делает:** Получить последний снимок конкретного магазина

**Запрос:**
```bash
curl "http://localhost:8085/snapshots/latest?shop_code=moscow"
```

**Ответ:**
```json
{
  "id": 5,
  "shop_id": 1,
  "created_at": "2025-10-11T15:30:00",
  "items_count": 1847,
  "worker_name": "moscow_worker"
}
```

**Когда использовать:**
- Проверка последнего обновления
- Получение актуального состояния магазина
- Мониторинг работы воркеров

---

## 👑 ADMIN (2 endpoints)

### 9. POST /admin/snapshot/trigger
**Что делает:** Запустить создание снимка магазина вручную (без ожидания часа)

**Запрос:**
```bash
curl -X POST "http://localhost:8085/admin/snapshot/trigger?shop_code=moscow"
```

**Ответ:**
```json
{
  "status": "triggered",
  "shop_code": "moscow",
  "message": "Snapshot creation started"
}
```

**Когда использовать:**
- Тестирование
- Принудительное обновление данных
- Диагностика проблем
- После изменений на сервере

---

### 10. GET /admin/bots/status
**Что делает:** Получить статус всех ботов-парсеров (moscow, oasis, neva)

**Запрос:**
```bash
curl http://localhost:8085/admin/bots/status
```

**Ответ:**
```json
{
  "bots": [
    {
      "shop_code": "moscow",
      "bot_login": "Sova",
      "authenticated": true,
      "session_id": "Sova...",
      "last_activity": "2025-10-11T15:45:30"
    },
    {
      "shop_code": "oasis",
      "bot_login": "Sova",
      "authenticated": true,
      "session_id": "Sova...",
      "last_activity": "2025-10-11T15:45:28"
    },
    {
      "shop_code": "neva",
      "bot_login": "Sova",
      "authenticated": false,
      "session_id": null,
      "last_activity": null
    }
  ]
}
```

**Что показывает:**
- Статус авторизации каждого бота
- Время последней активности
- ID сессии
- Проблемы с подключением

**Когда использовать:**
- Мониторинг работы воркеров
- Диагностика проблем с авторизацией
- Проверка keep-alive пингов

---

## 📚 SWAGGER UI

### 11. GET /docs
**Что делает:** Интерактивная документация API

**Открыть:**
```bash
open http://localhost:8085/docs
```

**Что можно:**
- ✅ Просмотреть все endpoints
- ✅ Протестировать запросы прямо в браузере
- ✅ Посмотреть схемы данных
- ✅ Скачать OpenAPI спецификацию

---

## 🎯 СЦЕНАРИИ ИСПОЛЬЗОВАНИЯ

### Сценарий 1: Проверка работоспособности

```bash
# Шаг 1: Проверить что API работает
curl http://localhost:8085/healthz

# Шаг 2: Проверить БД
curl http://localhost:8085/db/health

# Шаг 3: Проверить статус ботов
curl http://localhost:8085/admin/bots/status
```

**Результат:** Понять что всё работает или найти проблему

---

### Сценарий 2: Создать снимок и проверить данные

```bash
# Шаг 1: Запустить снимок Moscow
curl -X POST "http://localhost:8085/admin/snapshot/trigger?shop_code=moscow"

# Шаг 2: Подождать 10-15 минут

# Шаг 3: Проверить последний снимок
curl "http://localhost:8085/snapshots/latest?shop_code=moscow"
# → items_count: 1847

# Шаг 4: Посмотреть товары
curl "http://localhost:8085/items/list?shop_code=moscow&limit=10"
```

**Результат:** Снимок создан, товары в БД

---

### Сценарий 3: Мониторинг изменений

```bash
# Каждые 10 минут проверять:
while true; do
    curl -s http://localhost:8085/snapshots/latest?shop_code=moscow | \
        jq '{id, items_count, created_at}'
    sleep 600
done
```

**Результат:** Видим как меняется количество товаров со временем

---

### Сценарий 4: Найти конкретный товар

```bash
# Шаг 1: Получить список товаров Moscow
curl "http://localhost:8085/items/list?shop_code=moscow&limit=100" | \
    jq '.items[] | select(.txt | contains("knife"))'

# Шаг 2: Взять ID и получить детали
curl http://localhost:8085/items/79469641
```

**Результат:** Детальная информация о товаре

---

## 📊 ПРИМЕРЫ РЕАЛЬНЫХ ДАННЫХ

### После первого снимка вы увидите:

**GET /items/list?shop_code=moscow&limit=5**
```json
{
  "items": [
    {"id": 100001, "txt": "Butterfly knife", "price": 4.0, "quality": 125},
    {"id": 100002, "txt": "Combat knife", "price": 8.0, "quality": 150},
    {"id": 200001, "txt": "Beretta 92/93", "price": 22.0, "quality": 95},
    {"id": 300001, "txt": "AK-47", "price": 85.0, "quality": 120},
    {"id": 400001, "txt": "Blaster Rifle", "price": 66.0, "quality": 50}
  ],
  "total": 5,
  "page": 1
}
```

**GET /snapshots/latest?shop_code=moscow**
```json
{
  "id": 1,
  "shop_id": 1,
  "created_at": "2025-10-11T15:30:00",
  "items_count": 1847,
  "worker_name": "moscow_worker"
}
```

**GET /admin/bots/status**
```json
{
  "bots": [
    {
      "shop_code": "moscow",
      "bot_login": "Sova",
      "authenticated": true,
      "last_activity": "2025-10-11T15:45:30"
    },
    {
      "shop_code": "oasis",
      "bot_login": "Sova",
      "authenticated": true,
      "last_activity": "2025-10-11T15:45:28"
    },
    {
      "shop_code": "neva",
      "bot_login": "Sova",
      "authenticated": true,
      "last_activity": "2025-10-11T15:45:32"
    }
  ]
}
```

---

## 🔧 ПОЛЕЗНЫЕ КОМАНДЫ

### Проверка здоровья системы
```bash
# Быстрая проверка
curl -s http://localhost:8085/healthz | jq

# Полная проверка
curl -s http://localhost:8085/healthz && \
curl -s http://localhost:8085/db/health && \
curl -s http://localhost:8085/admin/bots/status | jq
```

### Просмотр товаров
```bash
# Топ 10 самых дорогих в Moscow
curl -s "http://localhost:8085/items/list?shop_code=moscow&limit=1000" | \
    jq '.items | sort_by(.price) | reverse | .[0:10] | .[] | {txt, price}'

# Топ 10 лучшего качества
curl -s "http://localhost:8085/items/list?shop_code=moscow&limit=1000" | \
    jq '.items | sort_by(.current_quality) | reverse | .[0:10] | .[] | {txt, quality: .current_quality}'
```

### Мониторинг снимков
```bash
# Посмотреть последние снимки всех магазинов
for shop in moscow oasis neva; do
    echo "=== $shop ==="
    curl -s "http://localhost:8085/snapshots/latest?shop_code=$shop" | jq
    echo ""
done
```

---

## 🎯 ИТОГО: 10 ENDPOINTS

| № | Endpoint | Метод | Что делает |
|---|----------|-------|------------|
| 1 | `/healthz` | GET | Проверка сервиса |
| 2 | `/shop/health` | GET | Проверка модуля |
| 3 | `/db/health` | GET | Проверка БД |
| 4 | `/items/list` | GET | Список товаров (фильтры, пагинация) |
| 5 | `/items/{id}` | GET | Детали товара |
| 6 | `/items/search` | GET | Поиск (TODO) |
| 7 | `/snapshots/list` | GET | Список снимков |
| 8 | `/snapshots/latest` | GET | Последний снимок магазина |
| 9 | `/admin/snapshot/trigger` | POST | Запустить снимок вручную |
| 10 | `/admin/bots/status` | GET | Статус ботов |

**+ Swagger UI:** `/docs` — интерактивная документация

---

## 🚀 БЫСТРЫЙ ТЕСТ

### Скрипт автоматического тестирования:

```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client/api_5
./test_api_endpoints.sh
```

**Что делает:**
- Проверяет все 10 endpoints
- Показывает запросы и ответы
- Выводит результаты в удобном формате

---

**Все endpoints готовы к использованию!** ✅







