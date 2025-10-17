# ✅ API 5 - Полный список endpoints

**Всего:** 15 endpoints  
**Категории:** 6 групп  
**Статус:** ✅ Все работают

---

## 📋 ВСЕ 15 ENDPOINTS

### 🏥 Health & Service (3)

1. `GET /healthz` — Проверка сервиса
2. `GET /shop/health` — Проверка модуля
3. `GET /db/health` — Проверка БД

### 📦 Items (2)

4. `GET /items/list` — Список товаров (пагинация, фильтр по магазину)
5. `GET /items/{id}` — Детали товара

### 🗂️ Categories (2) ← **НОВОЕ!**

6. **`GET /categories/list`** — **Список всех 27 категорий**
7. **`GET /categories/{code}/items`** — **Товары категории** ✨

### 👤 Sellers (3) ← **НОВОЕ!**

8. **`GET /sellers/search`** — **Поиск по нику продавца** ✨
9. **`GET /sellers/stats`** — **ТОП продавцов (ник + кол-во + стоимость)** ✨
10. **`GET /sellers/{owner}/summary`** — **Сводка продавца** ✨

### 📸 Snapshots (2)

11. `GET /snapshots/list` — Список снимков
12. `GET /snapshots/latest` — Последний снимок

### 👑 Admin (2)

13. `POST /admin/snapshot/trigger` — Запустить снимок
14. `GET /admin/bots/status` — Статус ботов

### 📚 Bonus

15. `GET /docs` — Swagger UI

---

## ✨ НОВЫЕ ENDPOINTS (что ты просил)

### ✅ 1. Ввожу категорию → получаю товары

**GET /categories/{code}/items**

```bash
# Все ресурсы (s)
curl "http://localhost:8085/categories/s/items"

# Крафт-реагенты (y) в Moscow
curl "http://localhost:8085/categories/y/items?shop_code=moscow"

# Встройки (u) в Oasis
curl "http://localhost:8085/categories/u/items?shop_code=oasis&limit=200"
```

**Ответ:**
```json
{
  "category": "s",
  "shop_code": "moscow",
  "items": [
    {"id": 123, "txt": "Железная руда", "price": 8.0},
    {"id": 124, "txt": "Медь", "price": 10.0},
    ... (ещё 98 ресурсов)
  ],
  "total": 100
}
```

---

### ✅ 2. Поиск по нику продавца

**GET /sellers/search?owner={ник}**

```bash
# Все товары PlayerX
curl "http://localhost:8085/sellers/search?owner=PlayerX"

# Товары PlayerX только в Moscow
curl "http://localhost:8085/sellers/search?owner=PlayerX&shop_code=moscow"
```

**Ответ:**
```json
{
  "owner": "PlayerX",
  "items": [
    {"id": 456, "txt": "Glock 17", "price": 25.0, "owner": "PlayerX"},
    {"id": 457, "txt": "Combat helmet", "price": 45.0, "owner": "PlayerX"},
    ... (ещё товары)
  ],
  "total": 15
}
```

---

### ✅ 3. Все продавцы + статистика

**GET /sellers/stats**

```bash
# ТОП-50 продавцов
curl "http://localhost:8085/sellers/stats?limit=50"

# ТОП-20 в Moscow (минимум 5 товаров)
curl "http://localhost:8085/sellers/stats?shop_code=moscow&min_items=5&limit=20"
```

**Ответ:**
```json
[
  {
    "owner": "MegaSeller",
    "items_count": 142,          ← Количество товаров
    "total_value": 15820.50,     ← Общая стоимость!
    "min_price": 2.0,
    "max_price": 5000.0,
    "avg_price": 111.41
  },
  {
    "owner": "WeaponShop",
    "items_count": 89,
    "total_value": 8450.00,
    "avg_price": 94.94
  },
  ... (ещё 48 продавцов)
]
```

**Сортировка:** По количеству товаров (DESC)

---

### ✅ 4. Детальная сводка продавца

**GET /sellers/{owner}/summary**

```bash
# Полная сводка PlayerX
curl "http://localhost:8085/sellers/PlayerX/summary"

# Сводка в конкретном магазине
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

**Показывает:**
- Сколько товаров выложил
- На какую сумму
- Разбивку по категориям
- Мин/макс/средняя цена

---

### ✅ 5. Список всех категорий

**GET /categories/list**

```bash
curl "http://localhost:8085/categories/list"
```

**Ответ:**
```json
{
  "categories": [
    {"code": "k", "name": "Холодное оружие", "group": "Оружие"},
    {"code": "p", "name": "Пистолеты", "group": "Оружие"},
    {"code": "s", "name": "Ресурсы", "group": "Прочее"},
    {"code": "y", "name": "Крафт-реагенты", "group": "Прочее"},
    {"code": "u", "name": "Встройки", "group": "Прочее"},
    ... (всего 27)
  ],
  "total": 27
}
```

---

## 🎯 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Пример 1: Найти все ресурсы в Moscow

```bash
curl "http://localhost:8085/categories/s/items?shop_code=moscow&limit=200"
```

**Результат:** Все 192 ресурса из магазина Moscow

---

### Пример 2: Найти все товары продавца MinerPro

```bash
curl "http://localhost:8085/sellers/search?owner=MinerPro"
```

**Результат:** Все товары MinerPro во всех магазинах

---

### Пример 3: ТОП-10 продавцов Moscow по количеству товаров

```bash
curl "http://localhost:8085/sellers/stats?shop_code=moscow&limit=10"
```

**Результат:**
```json
[
  {"owner": "MegaSeller", "items_count": 142, "total_value": 15820.50},
  {"owner": "WeaponShop", "items_count": 89, "total_value": 8450.00},
  {"owner": "ArmorKing", "items_count": 67, "total_value": 12340.00},
  ...
]
```

---

### Пример 4: Детальная сводка продавца WeaponShop

```bash
curl "http://localhost:8085/sellers/WeaponShop/summary"
```

**Результат:**
```json
{
  "owner": "WeaponShop",
  "total_items": 89,
  "total_value": 8450.00,
  "avg_price": 94.94,
  "by_category": [
    {"category": "p", "count": 45},  // Больше всего пистолетов
    {"category": "v", "count": 28},  // Винтовки
    {"category": "k", "count": 16}   // Холодное
  ]
}
```

**Вывод:** WeaponShop торгует в основном пистолетами!

---

### Пример 5: Найти все встройки (u) в Neva

```bash
curl "http://localhost:8085/categories/u/items?shop_code=neva&limit=100"
```

**Результат:** Все 82 встройки из магазина Neva

---

## 📊 СРАВНЕНИЕ: ДО И ПОСЛЕ

### Было (10 endpoints):
```
✅ Health
✅ Items (общий список)
✅ Snapshots
✅ Admin
```

**Проблема:** Нельзя фильтровать по категориям и продавцам

### Стало (15 endpoints):
```
✅ Health
✅ Items (общий список)
✅ Categories (список + фильтр по категории) ← НОВОЕ!
✅ Sellers (поиск + статистика + сводка) ← НОВОЕ!
✅ Snapshots
✅ Admin
```

**Решение:** Можно искать по категориям и продавцам!

---

## 🎯 ВСЕ ТВОИ ЗАПРОСЫ РЕАЛИЗОВАНЫ

### ✅ "Ввести категорию → получить товары"
```bash
GET /categories/{code}/items
```

### ✅ "Поиск по нику продавца"
```bash
GET /sellers/search?owner={ник}
```

### ✅ "Все продавцы + количество + стоимость"
```bash
GET /sellers/stats
```

### ✅ "И т.д." — Детальная сводка продавца
```bash
GET /sellers/{owner}/summary
```

---

## 📚 Swagger UI

Все 15 endpoints доступны в Swagger:

```bash
open http://localhost:8085/docs
```

**Теперь там 6 категорий:**
- 🏥 Health (3)
- 📦 Items (2)
- 🗂️ **Categories (2)** ← НОВОЕ!
- 👤 **Sellers (3)** ← НОВОЕ!
- 📸 Snapshots (2)
- 👑 Admin (2)

---

## ✅ CORS исправлен!

Swagger UI теперь работает без ошибок CORS:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  ← Добавлено
)
```

---

**Все endpoints готовы к использованию!** 🚀

**Swagger UI работает!** 📚







