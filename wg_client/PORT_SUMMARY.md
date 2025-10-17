# Сводка занятых портов проекта WG_HUB

## 🌐 **Внешние порты (доступны с хоста)**

### **Инфраструктура:**
- **80** - traefik (HTTP маршрутизация)
  - **Docker Compose:** `HOST_API_SERVICE_INFRASTRUCTURE.yml`
  - **Контейнер:** `traefik`

- **51820** - wg_vpn (WireGuard VPN)
  - **Docker Compose:** `HOST_API_SERVICE_INFRASTRUCTURE.yml`
  - **Контейнер:** `wg_vpn`

### **Базы данных:**
- **3306** - db (MySQL тестовая БД)
  - **Docker Compose:** `HOST_API_SERVICE_DB_API.yml`
  - **Контейнер:** `db`

- **5432** - api_4_db (PostgreSQL для API_4)
  - **Docker Compose:** `HOST_API_SERVICE_DB_API.yml`
  - **Контейнер:** `api_4_db`

- **5433** - metabase-db (PostgreSQL для Metabase)
  - **Docker Compose:** `HOST_API_SERVICE_DB_MONITORING.yml`
  - **Контейнер:** `metabase-db`

- **6379** - api_father_redis (Redis кэш)
  - **Docker Compose:** `HOST_API_SERVICE_INFRASTRUCTURE.yml`
  - **Контейнер:** `api_father_redis`

### **API сервисы:**
- **8081** - api_1 (статус игрового сервера)
  - **Docker Compose:** `HOST_API_SERVICE_LIGHT_WEIGHT_API.yml`
  - **Контейнер:** `api_1`

- **8082** - api_2 (регистрация и бонусы)
  - **Docker Compose:** `HOST_API_SERVICE_LIGHT_WEIGHT_API.yml`
  - **Контейнер:** `api_2`

- **8084** - api_4 (аналитика боёв)
  - **Docker Compose:** `HOST_API_SERVICE_HEAVY_WEIGHT_API.yml`
  - **Контейнер:** `api_4`

- **9000** - api_father (центральный API)
  - **Docker Compose:** `HOST_API_SERVICE_FATHER_API.yml`
  - **Контейнер:** `api_father`

### **Игровые сервисы:**
- **5190** - game_server_mock (мок игрового сервера)
  - **Docker Compose:** `HOST_API_SERVICE_WORKERS.yml`
  - **Контейнер:** `game_server_mock`

### **Мониторинг и администрирование:**
- **9100** - portainer (управление Docker)
  - **Docker Compose:** `HOST_API_SERVICE_MONITORING.yml`
  - **Контейнер:** `portainer`

- **9101** - netdata (метрики хоста)
  - **Docker Compose:** `HOST_API_SERVICE_MONITORING.yml`
  - **Контейнер:** `netdata`

- **9102** - dozzle (просмотр логов)
  - **Docker Compose:** `HOST_API_SERVICE_MONITORING.yml`
  - **Контейнер:** `dozzle`

- **9103** - uptime-kuma (мониторинг аптайма)
  - **Docker Compose:** `HOST_API_SERVICE_MONITORING.yml`
  - **Контейнер:** `uptime-kuma`

- **9104** - homarr (старт-страница)
  - **Docker Compose:** `HOST_API_SERVICE_MONITORING.yml`
  - **Контейнер:** `homarr`

- **9105** - pgadmin (PostgreSQL админ)
  - **Docker Compose:** `HOST_API_SERVICE_MONITORING.yml`
  - **Контейнер:** `pgadmin`

- **9106** - metabase (аналитика и дашборды)
  - **Docker Compose:** `HOST_API_SERVICE_DB_MONITORING.yml`
  - **Контейнер:** `metabase`

- **9107** - swagger-ui (API документация)
  - **Docker Compose:** `HOST_API_SERVICE_MONITORING.yml`
  - **Контейнер:** `swagger-ui`

- **9108** - filebrowser (файловый менеджер)
  - **Docker Compose:** `HOST_API_SERVICE_MONITORING.yml`
  - **Контейнер:** `filebrowser`

- **9109** - ttyd (веб-терминал)
  - **Docker Compose:** `HOST_API_SERVICE_MONITORING.yml`
  - **Контейнер:** `ttyd`

## 📦 **Группировка по Docker Compose файлам**

### **HOST_API_SERVICE_INFRASTRUCTURE.yml** (3 порта)
- **80** - traefik
- **51820** - wg_vpn  
- **6379** - api_father_redis

### **HOST_API_SERVICE_FATHER_API.yml** (1 порт)
- **9000** - api_father

### **HOST_API_SERVICE_LIGHT_WEIGHT_API.yml** (2 порта)
- **8081** - api_1
- **8082** - api_2

### **HOST_API_SERVICE_HEAVY_WEIGHT_API.yml** (1 порт)
- **8084** - api_4

### **HOST_API_SERVICE_WORKERS.yml** (1 порт)
- **5190** - game_server_mock

### **HOST_API_SERVICE_DB_API.yml** (2 порта)
- **3306** - db
- **5432** - api_4_db

### **HOST_API_SERVICE_MONITORING.yml** (9 портов)
- **9100** - portainer
- **9101** - netdata
- **9102** - dozzle
- **9103** - uptime-kuma
- **9104** - homarr
- **9105** - pgadmin
- **9107** - swagger-ui
- **9108** - filebrowser
- **9109** - ttyd

### **HOST_API_SERVICE_DB_MONITORING.yml** (2 порта)
- **5433** - metabase-db
- **9106** - metabase

### **HOST_API_SERVICE_UTILITIES.yml** (0 внешних портов)
- Только внутренние операции

## 📊 **Статистика портов**

**Всего занято портов:** 24
- **Инфраструктура:** 3 порта
- **Базы данных:** 4 порта  
- **API сервисы:** 4 порта
- **Игровые сервисы:** 1 порт
- **Мониторинг:** 12 портов

## 🎯 **Диапазоны портов**

| Диапазон | Назначение | Занято | Свободно |
|----------|------------|--------|----------|
| **80-99** | Стандартные HTTP | 1 | 18 |
| **3000-3099** | Веб-интерфейсы | 0 | 100 |
| **5000-5199** | Игровые сервисы | 1 | 199 |
| **8000-8099** | API сервисы | 3 | 97 |
| **9000-9099** | Центральные сервисы | 1 | 99 |
| **9100-9199** | Мониторинг | 10 | 90 |
| **Стандартные БД** | Базы данных | 4 | - |

## 🚫 **Зарезервированные порты**

- **8003** - API_3 (планируется)
- **8080** - альтернативный HTTP
- **8443** - альтернативный HTTPS
- **22, 25, 53, 110, 143, 443, 993, 995** - системные порты
