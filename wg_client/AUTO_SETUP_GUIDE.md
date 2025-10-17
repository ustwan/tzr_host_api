# 🚀 Автоматическая Настройка WG_HUB

## 📋 Что происходит автоматически

### ✅ При первом запуске

1. **Автоматические миграции БД**
   - API 4 ждёт доступности БД (макс 60 сек)
   - Применяет все миграции из `migrations/`
   - Логирует результат

2. **XML Sync по умолчанию**
   - Автоматически запускается `auto-continue`
   - Загружает новые бои через XML Workers
   - Работает в фоне (не блокирует API)

3. **Swagger UI с предустановками**
   - Authorization token предзаполнен
   - Try it out включён
   - Настройки сохраняются между пересборками

---

## 🔧 Переменные окружения

### XML Sync (по умолчанию в API 4)

```bash
# Режим синхронизации: xml / file / both
SYNC_MODE=xml

# Автоматический запуск XML sync при старте
ENABLE_XML_SYNC_ON_START=true

# Размер батча для auto-continue
XML_SYNC_BATCH_SIZE=1000

# Интервал повторного sync (0 = однократно)
XML_SYNC_INTERVAL=0

# Автоматические миграции
AUTO_APPLY_MIGRATIONS=true
```

### Swagger UI (в MONITORING compose)

```bash
# Persistent authorization
PERSIST_AUTHORIZATION=true

# Config file
CONFIG_URL=/swagger-config.json
```

---

## 🚀 Быстрый старт

### Первый запуск (с нуля)

```bash
cd wg_client

# 1. Запуск XML Workers
docker-compose -f HOST_API_SERVICE_XML_WORKERS.yml up -d

# 2. Запуск API 4 (применит миграции автоматически)
docker-compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d

# 3. Запуск Swagger UI (с persistent настройками)
docker-compose -f HOST_API_SERVICE_MONITORING_SIMPLE.yml up -d swagger-ui
```

**Результат:**
- ✅ БД создана с миграциями
- ✅ XML Sync загружает новые бои автоматически
- ✅ Swagger UI с авторизацией

### Или через ctl.sh

```bash
cd wg_client
./tools/ctl.sh start-all
```

---

## 📊 Что происходит при запуске API 4

```
1. Entrypoint.sh
   ├─ Ждёт БД (60 сек)
   ├─ Применяет миграции
   └─ Запускает uvicorn

2. Startup Event (main.py)
   ├─ Подключается к БД
   ├─ Инициализирует сервисы
   ├─ Логирует конфигурацию
   └─ Запускает XML Sync в фоне (если включён)

3. XML Sync (фон)
   ├─ Ждёт 5 сек
   ├─ Запускает auto-continue
   └─ Загружает новые бои
```

---

## 🔄 Поведение после пересборки

### Docker Compose Down + Up

```bash
docker-compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml down
docker-compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d
```

**Что происходит:**
1. ✅ Миграции применяются (idempotent, безопасно)
2. ✅ XML Sync продолжает с последнего успешного ID
3. ✅ Конфигурация сохраняется (env vars в compose)
4. ✅ Swagger UI сохраняет настройки (volume)

### Полная очистка (Down с --volumes)

```bash
docker-compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml down --volumes
docker-compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d
```

**Что происходит:**
1. ✅ БД создаётся заново
2. ✅ Миграции применяются автоматически
3. ✅ XML Sync начинает с ID 1475356
4. ✅ Конфигурация восстанавливается из env vars

---

## ⚙️ Настройка режима работы

### Отключить XML Sync при старте

```yaml
# В HOST_API_SERVICE_HEAVY_WEIGHT_API.yml
environment:
  - ENABLE_XML_SYNC_ON_START=false
```

### Использовать file upload вместо XML

```yaml
environment:
  - SYNC_MODE=file
  - ENABLE_XML_SYNC_ON_START=false
```

### Оба режима доступны

```yaml
environment:
  - SYNC_MODE=both
  - ENABLE_XML_SYNC_ON_START=false  # Вручную через API
```

---

## 🧪 Проверка настроек

### Конфигурация API 4

```bash
docker logs wg-client-api_4-1 2>&1 | grep "Конфигурация:"
```

Вывод:
```
Конфигурация: {'sync_mode': 'xml', 'xml_sync_on_start': True, ...}
```

### XML Sync статус

```bash
curl http://localhost:8084/admin/xml-sync/status
```

### Swagger UI

Откройте: http://localhost:9107
- ✅ Authorization должна быть установлена
- ✅ Try it out включён по умолчанию

---

## 📝 Логи

### Миграции

```bash
docker logs wg-client-api_4-1 2>&1 | grep -A 10 "Применение миграций"
```

### XML Sync

```bash
docker logs wg-client-api_4-1 2>&1 | grep "XML Sync"
```

### XML Workers

```bash
docker logs host-api-xml-worker-1
```

---

## 🎯 Итог

**Теперь при любой пересборке:**
- ✅ Миграции применяются автоматически
- ✅ XML Sync начинает работать сразу
- ✅ Настройки сохраняются
- ✅ Swagger UI предн��строен

**Никаких ручных действий не требуется!** 🎉




