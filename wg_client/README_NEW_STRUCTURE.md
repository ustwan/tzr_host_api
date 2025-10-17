# WG_HUB - Новая структура Docker Compose

## 📋 Структура compose файлов

### 🏗️ **HOST_API_SERVICE_INFRASTRUCTURE.yml**
- **traefik** :80 - маршрутизация и прокси
- **wg_vpn** - WireGuard VPN клиент  
- **api_father_redis** :6379 - Redis кэш

### 🎯 **HOST_API_SERVICE_FATHER_API.yml**
- **api_father** :9000 - центральный API

### ⚡ **HOST_API_SERVICE_LIGHT_WEIGHT_API.yml**
- **api_1** :8081 - статус игрового сервера
- **api_2** :8082 - регистрация и бонусы

### 🔥 **HOST_API_SERVICE_HEAVY_WEIGHT_API.yml**
- **api_4** :8084 - аналитика боёв

### 👷 **HOST_API_SERVICE_WORKERS.yml**
- **worker** - фоновые задачи
- **game_server_mock** :5190 - мок игрового сервера

### 🗄️ **HOST_API_SERVICE_DB_API.yml**
- **db** :3306 - MySQL тестовая БД
- **api_4_db** :5432 - PostgreSQL для API_4

### 📊 **HOST_API_SERVICE_MONITORING.yml**
- **portainer** :9100 - управление Docker
- **netdata** :9101 - метрики хоста
- **dozzle** :9102 - просмотр логов
- **uptime-kuma** :9103 - мониторинг аптайма
- **homarr** :9104 - старт-страница
- **pgadmin** :9105 - PostgreSQL админ
- **swagger-ui** :9107 - API документация
- **filebrowser** :9108 - файловый менеджер
- **ttyd** :9109 - веб-терминал

### 🗃️ **HOST_API_SERVICE_DB_MONITORING.yml**
- **metabase-db** :5433 - PostgreSQL для Metabase
- **metabase** :9106 - аналитика и дашборды

### 🛠️ **HOST_API_SERVICE_UTILITIES.yml**
- **migrator** - миграции схемы БД

## 🚀 Команды управления

### Основные команды
```bash
# Базовая система (инфраструктура + API + воркеры)
bash tools/ctl.sh up

# Полная система (включая API_4 и БД)
bash tools/ctl.sh up-full

# С тестовой БД и миграциями
bash tools/ctl.sh up-testdb

# Только мониторинг
bash tools/ctl.sh up-monitoring
```

## 🧪 Тестирование

- Unit/Smoke: `pytest -q` (см. `HOST_API_SERVICE/pytest.ini`)
- Интеграционные (локально): поднимите нужные стеки командой `tools/ctl.sh config|ps` (без запуска для проверки конфигов), затем запускайте TestClient‑тесты.

## 📚 Clean Architecture гайд

Подробности и правила слоёв: см. файл `CLEAN_ARCHITECTURE.md` в корне репозитория.

Дополнительно:
- Проверка правил слоёв: `python tools/layer_lint.py` (возвращает ненулевой код при нарушениях импортов)

### Остановка
```bash
# Базовая система
bash tools/ctl.sh down

# Полная система
bash tools/ctl.sh down-full

# Все + удаление volumes
bash tools/ctl.sh down-all

# Только мониторинг
bash tools/ctl.sh down-monitoring
```

### Перезапуск сервисов
```bash
bash tools/ctl.sh restart-api1      # API_1
bash tools/ctl.sh restart-api2      # API_2  
bash tools/ctl.sh restart-api4      # API_4
bash tools/ctl.sh restart-father    # API_FATHER
```

### Логи
```bash
bash tools/ctl.sh logs              # Базовая система
bash tools/ctl.sh logs-full         # Полная система
bash tools/ctl.sh logs-monitoring   # Мониторинг
```

### Управление отдельными компонентами
```bash
bash tools/ctl.sh infrastructure    # Только инфраструктура
bash tools/ctl.sh father           # Только API_FATHER
bash tools/ctl.sh lightweight      # Только легкие API
bash tools/ctl.sh heavyweight      # Только API_4
bash tools/ctl.sh workers          # Только воркеры
bash tools/ctl.sh db               # Только БД
bash tools/ctl.sh monitoring       # Только мониторинг
```

## 🎯 Преимущества новой структуры

### ✅ **Модульность**
- Каждый compose файл отвечает за свою область
- Можно запускать только нужные компоненты
- Независимое развитие сервисов

### ✅ **Гибкость**
- Разные профили запуска для разных задач
- Легко масштабировать отдельные компоненты
- Простое тестирование

### ✅ **Безопасность**
- Четкое разделение ответственности
- Изоляция критических компонентов
- Контролируемые зависимости

### ✅ **Удобство**
- Понятные названия файлов
- Логичная группировка сервисов
- Расширенные возможности управления

## 🔄 Миграция со старой структуры

Старые команды → Новые команды:
```bash
# Было
docker compose -f compose.base.yml -f compose.apis.yml up
# Стало  
bash tools/ctl.sh up

# Было
docker compose -f compose.base.yml -f compose.apis.yml -f compose.db.test.yml up
# Стало
bash tools/ctl.sh up-testdb

# Было
docker compose -f compose.monitoring.yml up
# Стало
bash tools/ctl.sh up-monitoring
```
