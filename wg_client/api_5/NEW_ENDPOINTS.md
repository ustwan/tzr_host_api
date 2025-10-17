# 🆕 API 5 - Новые endpoints

**Добавлено:** 5 новых endpoints  
**Категории:** Categories (2) + Sellers (3)

---

## 🗂️ CATEGORIES (2 новых endpoints)

### 1. GET /categories/list
**Что делает:** Получить список всех 27 категорий магазина

**Запрос:**
```bash
curl http://localhost:8085/categories/list
```

**Ответ:**
```json
{
  "categories": [
    {"code": "k", "name": "Холодное оружие", "group": "Оружие"},
    {"code": "p", "name": "Пистолеты", "group": "Оружие"},
    {"code": "v", "name": "Винтовки/автоматы", "group": "Оружие"},
    ...
    {"code": "s", "name": "Ресурсы", "group": "Прочее"},
    {"code": "y", "name": "Крафт-реагенты", "group": "Прочее"},
    {"code": "u", "name": "Встройки", "group": "Прочее"}
  ],
  "total": 27
}
```

**Когда использовать:**
- Получить справочник категорий
- UI для выбора категории
- Документация

---

### 2. GET /categories/{category_code}/items
**Что делает:** Получить ВСЕ товары из конкретной категории

**Запрос 1: Все ресурсы (s)**
```bash
curl "http://localhost:8085/categories/s/items?limit=100"
```

**Запрос 2: Ресурсы только в Moscow**
```bash
curl "http://localhost:8085/categories/s/items?shop_code=moscow&limit=100"
```

**Запрос 3: Все пистолеты (p) в Oasis**
```bash
curl "http://localhost:8085/categories/p/items?shop_code=oasis&limit=50"
```

**Ответ:**
```json
{
  "category": "s",
  "shop_code": "moscow",
  "items": [
    {
      "id": 80235678,
      "txt": "Железная руда",
      "price": 8.0,
      "current_quality": 100,
      "max_quality": 100,
      "shop_id": 1,
      "owner": "MinerPro"
    },
    {
      "id": 80235679,
      "txt": "Медь",
      "price": 10.0,
      "current_quality": 100,
      "max_quality": 100,
      "shop_id": 1,
      "owner": "ResourceKing"
    },
    ... (ещё 98 ресурсов)
  ],
  "total": 100
}
```

**Когда использовать:**
- ✅ **ТО ЧТО ТЫ ХОТЕЛ!** Ввести категорию → получить все товары
- Фильтрация по категориям
- Анализ конкретного типа товаров
- Экспорт товаров категории

**Параметры:**
- `category_code` — k, p, v, s, y, u, ... (обязательно)
- `shop_code` — moscow/oasis/neva (опционально)
- `limit` — max товаров (default=100, max=1000)

---

## 👤 SELLERS (3 новых endpoints)

### 3. GET /sellers/search
**Что делает:** Найти ВСЕ товары конкретного продавца по нику

**Запрос 1: Все товары продавца**
```bash
curl "http://localhost:8085/sellers/search?owner=PlayerX&limit=100"
```

**Запрос 2: Товары продавца только в Moscow**
```bash
curl "http://localhost:8085/sellers/search?owner=PlayerX&shop_code=moscow"
```

**Ответ:**
```json
{
  "owner": "PlayerX",
  "shop_code": "moscow",
  "items": [
    {
      "id": 79470736,
      "txt": "Glock 17",
      "price": 25.0,
      "current_quality": 90,
      "max_quality": 100,
      "shop_id": 1,
      "owner": "PlayerX"
    },
    {
      "id": 79470737,
      "txt": "Desert Eagle",
      "price": 45.0,
      "current_quality": 85,
      "max_quality": 100,
      "shop_id": 1,
      "owner": "PlayerX"
    },
    ... (ещё товары PlayerX)
  ],
  "total": 15
}
```

**Когда использовать:**
- ✅ **ТО ЧТО ТЫ ХОТЕЛ!** Поиск по нику продавца
- Просмотр магазина конкретного игрока
- Анализ цен продавца

---

### 4. GET /sellers/stats
**Что делает:** Статистика по ВСЕМ продавцам (ТОП-100)

**Запрос 1: Все продавцы**
```bash
curl "http://localhost:8085/sellers/stats?limit=50"
```

**Запрос 2: Только Moscow, минимум 5 товаров**
```bash
curl "http://localhost:8085/sellers/stats?shop_code=moscow&min_items=5&limit=20"
```

**Ответ:**
```json
[
  {
    "owner": "MegaSeller",
    "items_count": 142,
    "total_value": 15820.50,
    "min_price": 2.0,
    "max_price": 5000.0,
    "avg_price": 111.41
  },
  {
    "owner": "WeaponShop",
    "items_count": 89,
    "total_value": 8450.00,
    "min_price": 10.0,
    "max_price": 850.0,
    "avg_price": 94.94
  },
  {
    "owner": "ArmorKing",
    "items_count": 67,
    "total_value": 12340.00,
    "min_price": 50.0,
    "max_price": 1200.0,
    "avg_price": 184.18
  },
  ... (ещё 47 продавцов)
]
```

**Когда использовать:**
- ✅ **ТО ЧТО ТЫ ХОТЕЛ!** Список всех продавцов с статистикой
- ТОП продавцов по количеству товаров
- Анализ рынка
- Поиск крупных торговцев

**Параметры:**
- `shop_code` — moscow/oasis/neva (опционально)
- `min_items` — минимум товаров (default=1)
- `limit` — max продавцов (default=100)

**Сортировка:** По количеству товаров (DESC)

---

### 5. GET /sellers/{owner}/summary
**Что делает:** Подробная сводка по продавцу (с разбивкой по категориям)

**Запрос:**
```bash
curl "http://localhost:8085/sellers/PlayerX/summary?shop_code=moscow"
```

**Ответ:**
```json
{
  "owner": "PlayerX",
  "shop_code": "moscow",
  "total_items": 15,
  "total_value": 485.0,
  "min_price": 5.0,
  "max_price": 120.0,
  "avg_price": 32.33,
  "by_category": [
    {"category": "p", "count": 8},   // Пистолеты
    {"category": "h", "count": 4},   // Каски
    {"category": "d", "count": 3}    // Медицина
  ]
}
```

**Когда использовать:**
- Детальная информация о продавце
- Какие категории продаёт
- Средний чек продавца

---

## 📊 ИТОГО ENDPOINTS

### **Было:** 10 endpoints

1. GET /healthz
2. GET /shop/health
3. GET /db/health
4. GET /items/list
5. GET /items/{id}
6. GET /snapshots/list
7. GET /snapshots/latest
8. POST /admin/snapshot/trigger
9. GET /admin/bots/status
10. GET /docs

### **Стало:** 15 endpoints (+5)

11. **GET /categories/list** — список категорий
12. **GET /categories/{code}/items** — товары категории ✨
13. **GET /sellers/search** — поиск по продавцу ✨
14. **GET /sellers/stats** — статистика продавцов ✨
15. **GET /sellers/{owner}/summary** — сводка продавца ✨

---

## 🎯 ОТВЕТЫ НА ТВОИ ЗАПРОСЫ

### ✅ 1. "Ручка где ввожу категорию и получаю товары"

```bash
GET /categories/{category_code}/items

# Примеры:
curl "http://localhost:8085/categories/s/items"        # Ресурсы
curl "http://localhost:8085/categories/y/items"        # Крафт
curl "http://localhost:8085/categories/u/items"        # Встройки
curl "http://localhost:8085/categories/p/items"        # Пистолеты
```

### ✅ 2. "Поиск по нику продавца"

```bash
GET /sellers/search?owner={ник}

# Пример:
curl "http://localhost:8085/sellers/search?owner=PlayerX"
```

### ✅ 3. "Все ники продавцов + сколько товаров + общая стоимость"

```bash
GET /sellers/stats

# Пример:
curl "http://localhost:8085/sellers/stats?limit=50"

# Ответ:
[
  {
    "owner": "MegaSeller",
    "items_count": 142,        ← Количество товаров
    "total_value": 15820.50,   ← Общая стоимость!
    "avg_price": 111.41
  },
  ...
]
```

---

## 🚀 ИСПОЛЬЗОВАНИЕ

### Пример 1: Найти все ресурсы в Moscow

```bash
curl "http://localhost:8085/categories/s/items?shop_code=moscow&limit=200"
```

### Пример 2: Найти все товары продавца MinerPro

```bash
curl "http://localhost:8085/sellers/search?owner=MinerPro"
```

### Пример 3: ТОП-20 продавцов Moscow

```bash
curl "http://localhost:8085/sellers/stats?shop_code=moscow&limit=20"
```

### Пример 4: Детальная сводка продавца

```bash
curl "http://localhost:8085/sellers/WeaponShop/summary"
```

---

## ✅ SWAGGER UI

Все новые endpoints доступны в Swagger:

```bash
open http://localhost:8085/docs
```

**Теперь там 15 endpoints в 6 категориях:**
- 🏥 Health (3)
- 📦 Items (2)
- 🗂️ **Categories (2)** ← НОВОЕ!
- 👤 **Sellers (3)** ← НОВОЕ!
- 📸 Snapshots (2)
- 👑 Admin (2)

---

**Все твои запросы реализованы!** ✅







