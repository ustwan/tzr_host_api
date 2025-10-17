# ✅ Исправление API интеграции — Готово!

## 🔧 Что исправлено

### 1. **API baseURL** → Через Nginx прокси
**Было:** `http://localhost:8005` (прямое подключение из браузера)  
**Стало:** `/api` (через Nginx прокси)

**Почему это важно:**
- Браузер не может подключиться напрямую к `host.docker.internal:8005`
- Nginx проксирует все запросы из `/api/*` → `http://host.docker.internal:8005/`

### 2. **Nginx прокси настроен**
Добавлено в `nginx.conf`:

```nginx
location /api/ {
    proxy_pass http://host.docker.internal:8005/;
    proxy_set_header Host $host;
    proxy_connect_timeout 30s;
    proxy_read_timeout 30s;
    
    # CORS headers
    add_header Access-Control-Allow-Origin * always;
    
    # SSE support
    proxy_buffering off;
    proxy_cache off;
}
```

### 3. **Удалены все демо-данные**
Убраны из всех дашбордов:
- ✅ heatmap.html
- ✅ players.html  
- ✅ analytics-heatmap.html
- ✅ analytics-clan-control.html
- ✅ analytics-peak-hours.html
- ✅ analytics-pvp-elo.html
- ✅ analytics-churn.html

---

## 🚀 Как теперь работает

### Схема запросов:

```
Браузер → http://localhost:14488/api/...
          ↓
    Nginx (контейнер)
          ↓
    host.docker.internal:8005
          ↓
    API5 (если запущен)
```

---

## ⚡ Запуск API5 (нужно для работы)

### Вариант 1: API5 уже запущен

```bash
# Проверка
curl http://localhost:8005/health

# Если ответ OK — всё готово!
```

### Вариант 2: Запустить API5

```bash
# Если API5 в Docker
docker-compose -f docker-compose.api5.yml up -d

# Если API5 локально
cd wg_client/api_5
uvicorn app.main:app --host 0.0.0.0 --port 8005
```

---

## 🧪 Тестирование прокси

### Проверка доступности через прокси:

```bash
# Health check через прокси
curl http://localhost:14488/api/health
# Ожидается: {"status": "ok"} или похожее

# Если 502 Bad Gateway — API5 не запущен
# Если 404 — endpoint не реализован
# Если 200 — всё работает!
```

---

## 🌐 Проверка в браузере

### Откройте: http://localhost:14488

1. Перейдите на любой дашборд (например, Analytics Heatmap)
2. Установите даты
3. Нажмите "Загрузить"
4. Если API запущен — данные загрузятся
5. Если API не запущен — появится ошибка (демо-данные больше НЕ загружаются)

---

## ✅ Текущий статус

```
✅ Nginx прокси: настроен
✅ API baseURL: /api
✅ Демо-данные: удалены
✅ Контейнер: пересобран и запущен
✅ Порт: 14488
⚠️ API5: нужно запустить на порту 8005
```

---

## 🔌 API Endpoints (нужны для работы)

Дашборды будут запрашивать:

```
GET /api/battles/heatmap
GET /api/analytics/map/heatmap
GET /api/analytics/pve/top-locations
GET /api/analytics/map/pvp-hotspots
GET /api/analytics/map/clan-control
GET /api/analytics/time/peak-hours
GET /api/analytics/time/activity-heatmap
GET /api/analytics/pvp/elo
GET /api/players/by-profession
GET /api/analytics/predictions/churn
```

Все запросы идут через Nginx прокси → `http://host.docker.internal:8005/`

---

## 🐛 Если API на другом порту

### Изменить в `nginx.conf`:

```nginx
location /api/ {
    proxy_pass http://host.docker.internal:ДРУГОЙ_ПОРТ/;
    ...
}
```

### Пересобрать:

```bash
docker-compose -f docker-compose.viz.yml up -d --build
```

---

## 📊 Проверка конфигурации

```bash
# Проверка nginx.conf в контейнере
docker exec wg_visualization cat /etc/nginx/conf.d/default.conf | grep proxy_pass

# Ожидаемый вывод:
# proxy_pass http://host.docker.internal:8005/;

# Проверка api-client.js
curl -s http://localhost:14488/assets/js/api-client.js | grep baseURL

# Ожидаемый вывод:
# baseURL: '/api',
```

---

## 🎯 Следующие шаги

1. **Запустить API5 на порту 8005**
   ```bash
   # Например
   cd wg_client/api_5
   uvicorn app.main:app --host 0.0.0.0 --port 8005
   ```

2. **Проверить health check**
   ```bash
   curl http://localhost:8005/health
   curl http://localhost:14488/api/health
   ```

3. **Открыть дашборды**
   ```
   http://localhost:14488
   ```

4. **Загрузить данные**
   - Выбрать дашборд
   - Установить фильтры
   - Нажать "Загрузить"
   - Данные придут из API!

---

## ✨ Преимущества текущей конфигурации

- ✅ **Нет CORS проблем** — всё через прокси
- ✅ **Единый домен** — `localhost:14488` для UI и API
- ✅ **SSE support** — для real-time в antibot
- ✅ **Нет демо-данных** — только реальные данные из API
- ✅ **Timeout 30s** — достаточно для долгих запросов

---

**Готово!** 🎉 

API интеграция настроена. Осталось только запустить API5 на порту 8005.









