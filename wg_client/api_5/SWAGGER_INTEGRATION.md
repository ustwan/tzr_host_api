# ✅ API 5 - Интеграция со Swagger UI

**Статус:** ✅ Добавлен в общий Swagger UI на порту 9107

---

## 📚 Общий Swagger UI (порт 9107)

В проекте есть **единый Swagger UI** для всех API на порту `9107`.

### Конфигурация

Файл: `wg_client/swagger_config/initializer.js`

**Добавлено API 5:**

```javascript
urls: [
  {"name": "API 1", "url": "http://localhost:8081/openapi.json"},
  {"name": "API 2", "url": "http://localhost:8082/openapi.json"},
  {"name": "API 4", "url": "http://localhost:8084/openapi.json"},
  {"name": "API 5 - Shop Parser", "url": "http://localhost:8085/openapi.json"}, ← ДОБАВЛЕНО!
  {"name": "API Father", "url": "http://localhost:8080/openapi.json"},
  {"name": "API Mother", "url": "http://localhost:8083/openapi.json"}
]
```

---

## 🔧 Исправление CORS

### Проблема:
```
❌ Fetch error: Possible cross-origin (CORS) issue
   The URL origin (http://localhost:8084) does not match 
   the page (http://localhost:9107)
```

### Решение:

**Для API 5** уже добавлено в `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  ← Важно для Swagger!
)
```

**Для API 4** нужно добавить то же самое в его `main.py`.

---

## 🚀 Использование

### Открыть общий Swagger UI:

```bash
open http://localhost:9107
```

### Выбрать API:

В выпадающем списке сверху будет:
- API 1
- API 2
- API 4
- **API 5 - Shop Parser** ← НОВОЕ!
- API Father
- API Mother

### Посмотреть endpoints API 5:

1. Выбрать "API 5 - Shop Parser" в списке
2. Увидеть 15 endpoints в 6 категориях:
   - 🏥 Health & Service (3)
   - 📦 Items (2)
   - 🗂️ Categories (2)
   - 👤 Sellers (3)
   - 📸 Snapshots (2)
   - 👑 Admin (2)

---

## 📊 Endpoints в Swagger

### Swagger UI покажет:

```
API 5 - Shop Parser v1.0.0

API парсинга и аналитики игровых магазинов
Магазины: Moscow, Oasis, Neva

🏥 Health & Service
├─ GET /healthz
├─ GET /shop/health
└─ GET /db/health

📦 Items
├─ GET /items/list
└─ GET /items/{id}

🗂️ Categories
├─ GET /categories/list
└─ GET /categories/{code}/items

👤 Sellers
├─ GET /sellers/search
├─ GET /sellers/stats
└─ GET /sellers/{owner}/summary

📸 Snapshots
├─ GET /snapshots/list
└─ GET /snapshots/latest

👑 Admin
├─ POST /admin/snapshot/trigger
└─ GET /admin/bots/status
```

### Можно тестировать:

1. Нажать "Try it out"
2. Ввести параметры (например, category="s", shop_code="moscow")
3. Нажать "Execute"
4. Увидеть результат

---

## ✅ Готово!

API 5 интегрирован в общий Swagger UI проекта!

**Доступен по адресу:** http://localhost:9107  
**Выбрать:** API 5 - Shop Parser в выпадающем списке







