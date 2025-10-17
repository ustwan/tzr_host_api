# WG_HUB - Исправленная версия

## 🚀 Быстрый запуск

### Автоматический запуск (рекомендуется)
```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client
./start_project.sh
```

### Ручной запуск
```bash
# 1. Очистка Docker
docker system prune -f
docker volume prune -f
docker network prune -f

# 2. Создание сетей
docker network create host-api-service_apinet
docker network create host-api-service_backnet
docker network create host-api-service_dbnet
docker network create monitoring

# 3. Запуск инфраструктуры
docker compose -f HOST_API_SERVICE_INFRASTRUCTURE.yml up -d

# 4. Ожидание готовности БД
sleep 10

# 5. Применение миграций
docker exec host-api-service-api_4_db-1 psql -U api4_user -d api4_battles -f /docker-entrypoint-initdb.d/V1__create_tables_complete.sql

# 6. Запуск API сервисов
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d

# 7. Запуск мониторинга
docker compose -f HOST_API_SERVICE_MONITORING.yml up -d
```

## 🔧 Исправления

### 1. Dockerfile для API 4
- ✅ Добавлено копирование `example/parser` в контейнер
- ✅ Добавлен скрипт миграций
- ✅ Исправлены права доступа

### 2. Относительные импорты
- ✅ Все импорты в API 4 исправлены на абсолютные
- ✅ Исправлены импорты в `database.py`, `analytics.py`, `routes.py`, `parser.py`

### 3. База данных
- ✅ Создана полная миграция `V1__create_tables_complete.sql`
- ✅ Все таблицы создаются автоматически
- ✅ Добавлены все необходимые индексы и функции

### 4. Сети Docker
- ✅ Исправлены имена сетей в compose файлах
- ✅ Все сервисы подключаются к правильным сетям

### 5. Интеграция парсера
- ✅ Новый парсер v2.0 полностью интегрирован
- ✅ API Mother отправляет файлы в API 4
- ✅ Все новые поля сохраняются в БД

## 📊 Доступные сервисы

- **API 4**: http://127.0.0.1:1010/api/battles/list
- **API Mother**: http://127.0.0.1:1010/api/mother/list
- **Portainer**: http://127.0.0.1:9100
- **Netdata**: http://127.0.0.1:19999
- **PgAdmin**: http://127.0.0.1:5050
- **Swagger UI**: http://127.0.0.1:8080

## 🧪 Тестирование

### Тест API 4
```bash
curl http://127.0.0.1:1010/api/battles/list
```

### Тест обработки файлов
```bash
curl -X POST "http://127.0.0.1:1010/api/mother/process-batch?limit=3"
```

### Тест нового парсера
```bash
curl -X POST "http://127.0.0.1:1010/api/mother/process/53/2655800.tzb"
```

## 🐛 Устранение проблем

### Если API 4 не запускается
1. Проверьте логи: `docker logs wg-client-api_4-1`
2. Убедитесь, что БД запущена: `docker ps | grep postgres`
3. Примените миграции вручную

### Если файлы не обрабатываются
1. Проверьте, что `example/parser` скопирован в контейнер
2. Проверьте логи API 4 на ошибки парсера

### Если данные не сохраняются
1. Проверьте подключение к БД
2. Убедитесь, что миграции применены
3. Проверьте логи на ошибки SQL

## 📝 Логи

```bash
# Логи API 4
docker logs wg-client-api_4-1 -f

# Логи API Mother
docker logs wg-client-api_mother-1 -f

# Логи БД
docker logs host-api-service-api_4_db-1 -f
```

## 🔄 Перезапуск

```bash
# Полный перезапуск
./start_project.sh

# Перезапуск только API 4
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml restart api_4

# Перезапуск только API Mother
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml restart api_mother
```









