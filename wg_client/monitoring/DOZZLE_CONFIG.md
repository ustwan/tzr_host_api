# Dozzle Configuration Guide

## Доступ

- **URL**: http://localhost:9102
- **Автологин**: Включен (нет пароля)

## Группировка контейнеров

Dozzle автоматически группирует контейнеры. Рекомендуемые группы для фильтрации:

### 1. API Services
Фильтр в поиске: `api_`
```
- host-api-service-api_1-1
- host-api-service-api_2-1
- host-api-service-api_father-1
- host-api-service-api_4-1
- host-api-service-api_mother-1
```

### 2. File Contour (Файловый контур)
Фильтр в поиске: `btl`
```
- host-api-service-btl_syncer-1
- host-api-service-btl_compressor-1
```

### 3. Infrastructure
Фильтр в поиске: `traefik|redis|wg`
```
- host-api-service-traefik-1
- host-api-service-api_father_redis-1
- host-api-service-wg_vpn-1
```

### 4. Databases
Фильтр в поиске: `db`
```
- host-api-service-db-1 (MySQL)
- host-api-service-api_4_db-1 (PostgreSQL)
```

### 5. Mock Services
Фильтр в поиске: `mock`
```
- wg_client-mock_db_bridge-1
- wg_client-mock_btl_rsyncd-1
```

### 6. Workers
Фильтр в поиске: `worker|game_server`
```
- host-api-service-worker-1
- host-api-service-game_server_mock-1
```

## Полезные поисковые запросы

### Ошибки во всех сервисах
```
error|ERROR|Error|exception|Exception
```

### Логи файлового контура
```
btl
```

### API healthcheck
```
healthz|health
```

### База данных
```
mysql|postgres|redis
```

### HTTP запросы
```
GET|POST|PUT|DELETE
```

### Проблемы с подключением
```
connection|timeout|refused
```

## Настройки Dozzle

В `HOST_API_SERVICE_MONITORING_SIMPLE.yml` уже настроено:

```yaml
dozzle:
  image: amir20/dozzle:latest
  container_name: dozzle
  restart: unless-stopped
  ports:
    - "9102:8080"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  environment:
    - DOZZLE_LEVEL=info
    - DOZZLE_TAILSIZE=300
    - DOZZLE_FILTER=name=host-api-service|name=wg_client
```

## Горячие клавиши

- `Ctrl+F` или `/` - Открыть поиск
- `Esc` - Закрыть поиск
- `Ctrl+L` - Очистить экран
- `Ctrl+K` - Удалить все логи с экрана

## Multi-host режим

Для мониторинга нескольких Docker хостов:

```yaml
environment:
  - DOZZLE_REMOTE_HOST=tcp://remote-docker-host:2376
  - DOZZLE_REMOTE_HOST_CERT=/certs/cert.pem
  - DOZZLE_REMOTE_HOST_KEY=/certs/key.pem
```

## Цветовая схема

Dozzle автоматически подсвечивает:
- 🔴 **ERROR**, **FATAL** - красный
- 🟡 **WARN**, **WARNING** - желтый  
- 🔵 **INFO** - синий
- ⚪ **DEBUG**, **TRACE** - серый

## Экспорт логов

Нажмите на иконку **Download** в правом верхнем углу для экспорта логов контейнера в файл.

## Статистика контейнеров

Показывает в реальном времени:
- CPU usage
- Memory usage
- Network I/O
- Container status

## Best Practices

1. **Регулярно проверяйте файловый контур**:
   - Фильтр: `btl`
   - Ищите: `error|failed|timeout`

2. **Мониторьте API**:
   - Фильтр: `api_`
   - Ищите: `500|502|503|504|error`

3. **Следите за БД**:
   - Фильтр: `db`
   - Ищите: `slow query|deadlock|error`

4. **Проверяйте Traefik**:
   - Фильтр: `traefik`
   - Ищите: `404|502|timeout`










