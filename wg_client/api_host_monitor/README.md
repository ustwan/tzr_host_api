# API_HOST_MONITOR

Централизованная система мониторинга и управления инфраструктурой WG_HUB.

## Обзор

Этот модуль содержит все сервисы для мониторинга, управления и администрирования основной инфраструктуры проекта.

## Сервисы

### 🐳 Управление Docker
- **Portainer** (9100) - централизованное управление Docker контейнерами
- **Portainer Agent** (9001) - агент для удаленного управления (HOST_SERVER)

### 📊 Мониторинг
- **Netdata** (9101) - метрики хоста и контейнеров в реальном времени
- **Dozzle** (9102) - просмотр логов всех контейнеров
- **Uptime Kuma** (9103) - мониторинг доступности сервисов

### 🏠 Управление
- **Homarr** (9104) - единая старт-страница со всеми сервисами
- **pgAdmin** (9105) - веб-интерфейс для PostgreSQL
- **Metabase** (9106) - аналитика и дашборды
- **Swagger UI** (9107) - централизованное тестирование всех API
- **File Browser** (9108) - файловый менеджер
- **ttyd** (9109) - веб-терминал

### 🔗 Внешние сервисы
- **wg-easy** - веб-интерфейс для WireGuard (запускается в compose WG_HOST)

### 🗄️ База данных
- **PostgreSQL** (5433) - отдельная БД для Metabase (минимальная конфигурация)

## Быстрый старт

```bash
# Переход в папку
cd api_host_monitor

# Запуск всех сервисов
docker-compose -f compose.monitoring.yml up -d

# Просмотр логов
docker-compose -f compose.monitoring.yml logs -f

# Остановка
docker-compose -f compose.monitoring.yml down
```

## Порты

| Сервис | Порт | Описание |
|--------|------|----------|
| Portainer | 9100 | Управление Docker |
| Netdata | 9101 | Метрики |
| Dozzle | 9102 | Логи |
| Uptime Kuma | 9103 | Аптайм |
| Homarr | 9104 | Старт-страница |
| pgAdmin | 9105 | PostgreSQL UI |
| Metabase | 9106 | Аналитика |
| Swagger UI | 9107 | Тестирование API |
| File Browser | 9108 | Файлы |
| ttyd | 9109 | Терминал |
| PostgreSQL | 5433 | БД для Metabase |
| wg-easy | - | WireGuard UI (в compose WG_HOST) |

## Доступ

После запуска все сервисы будут доступны по адресам:
- `http://localhost:9100` - Portainer
- `http://localhost:9101` - Netdata
- `http://localhost:9102` - Dozzle
- `http://localhost:9103` - Uptime Kuma
- `http://localhost:9104` - Homarr
- `http://localhost:9105` - pgAdmin
- `http://localhost:9106` - Metabase
- `http://localhost:9107` - Swagger UI
- `http://localhost:9108` - File Browser
- `http://localhost:9109` - ttyd
- `http://localhost:8080` - wg-easy (из compose WG_HOST)

## Учетные данные

### По умолчанию
- **pgAdmin**: admin@wg-hub.local / wg_hub_admin
- **ttyd**: admin / wg_hub_password
- **Metabase**: настраивается при первом запуске
- **wg-easy**: wg_hub_password (из compose WG_HOST)

### PostgreSQL (Metabase)
- **Host**: metabase-db
- **Port**: 5432
- **Database**: metabase
- **User**: metabase
- **Password**: metabase_password

## Конфигурация

### Переменные окружения
Скопируйте `env.example` в `.env` и настройте под свои нужды:

```bash
cp env.example .env
```

### Сети
- `monitoring` - внутренняя сеть для сервисов мониторинга
- `dbnet` - подключение к основной БД (для pgAdmin)
- `HOST_API_SERVICE_default` - подключение к основной сети для доступа к API (для Swagger UI)

## Архитектура

```
┌─────────────────┐    ┌─────────────────┐
│   HOST_API      │    │  HOST_SERVER    │
│                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Portainer   │ │◄───┤ │ Portainer   │ │
│ │ (9100)      │ │    │ │ Agent (9001)│ │
│ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │
│ ┌─────────────┐ │    └─────────────────┘
│ │ Monitoring  │ │
│ │ Services    │ │
│ └─────────────┘ │
│                 │
│ ┌─────────────┐ │
│ │ Management  │ │
│ │ Services    │ │
│ └─────────────┘ │
└─────────────────┘
```

## Мониторинг

### Netdata
- Реальные метрики CPU, RAM, диска
- Метрики Docker контейнеров
- Сетевой трафик
- Процессы

### Uptime Kuma
- HTTP проверки API
- Ping проверки
- Уведомления о недоступности
- История аптайма

### Dozzle
- Логи всех контейнеров
- Фильтрация по сервисам
- Поиск по логам
- Автообновление

## Безопасность

- Все сервисы изолированы в отдельной сети
- Базовые пароли (измените в продакшене!)
- Доступ только через локальную сеть
- Portainer Agent через WireGuard туннель

## Обслуживание

### Бэкап данных
```bash
# Бэкап volumes
docker run --rm -v portainer_data:/data -v $(pwd):/backup alpine tar czf /backup/portainer_backup.tar.gz -C /data .
```

### Обновление
```bash
# Обновление всех образов
docker-compose -f compose.monitoring.yml pull
docker-compose -f compose.monitoring.yml up -d
```

### Логи
```bash
# Все сервисы
docker-compose -f compose.monitoring.yml logs

# Конкретный сервис
docker-compose -f compose.monitoring.yml logs metabase
```

## Troubleshooting

### Проблемы с портами
Убедитесь, что порты 9100-9110 и 5433 свободны:
```bash
netstat -tulpn | grep -E ':(910[0-9]|5433)'
```

### Проблемы с сетью
Проверьте подключение к основной БД:
```bash
docker network ls | grep dbnet
```

### Проблемы с Metabase
Проверьте подключение к БД:
```bash
docker-compose -f compose.monitoring.yml logs metabase-db
```
