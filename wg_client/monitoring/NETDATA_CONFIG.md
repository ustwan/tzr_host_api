# Netdata Configuration Guide

## Доступ

- **URL**: http://localhost:9101
- **Автологин**: Включен

## Автоматическая группировка контейнеров

Netdata автоматически обнаруживает и группирует Docker контейнеры по:
- CPU usage
- Memory usage
- Network I/O
- Disk I/O
- Container count

## Рекомендуемые Dashboard

### 1. Overview
- **URL**: http://localhost:9101/#menu_system
- Общая нагрузка на систему
- CPU, RAM, Network, Disk

### 2. Docker Containers
- **URL**: http://localhost:9101/#menu_docker
- Метрики всех контейнеров
- Группировка по CPU/Memory

### 3. Applications
- **URL**: http://localhost:9101/#menu_apps
- Метрики по приложениям
- MySQL, PostgreSQL, Redis, Nginx

## Алерты для HOST_API_SERVICE

### CPU Alerts
```yaml
# Высокая нагрузка CPU на API
alarm: api_high_cpu
on: docker.cpu
lookup: average -1m
units: %
every: 10s
warn: $this > 80
crit: $this > 95
info: API container CPU usage is high
to: sysadmin
```

### Memory Alerts
```yaml
# Высокое потребление памяти
alarm: api_high_memory
on: docker.mem
lookup: average -1m
units: MB
every: 10s
warn: $this > 500
crit: $this > 800
info: API container memory usage is high
to: sysadmin
```

### Network Alerts
```yaml
# Проблемы с сетью
alarm: api_network_errors
on: docker.net
lookup: sum -1m
units: errors
every: 10s
warn: $this > 10
crit: $this > 50
info: Network errors detected
to: sysadmin
```

## Метки для группировки

Добавить в `docker-compose.yml`:

```yaml
services:
  api_1:
    labels:
      - "netdata.group=api_services"
      - "netdata.type=lightweight"
      - "netdata.priority=high"
  
  api_2:
    labels:
      - "netdata.group=api_services"
      - "netdata.type=lightweight"
      - "netdata.priority=high"
  
  api_father:
    labels:
      - "netdata.group=api_services"
      - "netdata.type=central"
      - "netdata.priority=critical"
  
  api_4:
    labels:
      - "netdata.group=api_services"
      - "netdata.type=heavyweight"
      - "netdata.priority=high"
  
  api_mother:
    labels:
      - "netdata.group=api_services"
      - "netdata.type=lightweight"
      - "netdata.priority=medium"
  
  btl_syncer:
    labels:
      - "netdata.group=file_workers"
      - "netdata.type=io_intensive"
      - "netdata.priority=medium"
  
  btl_compressor:
    labels:
      - "netdata.group=file_workers"
      - "netdata.type=cpu_intensive"
      - "netdata.priority=medium"
  
  worker:
    labels:
      - "netdata.group=workers"
      - "netdata.type=queue_processor"
      - "netdata.priority=medium"
  
  db:
    labels:
      - "netdata.group=databases"
      - "netdata.type=mysql"
      - "netdata.priority=critical"
  
  api_4_db:
    labels:
      - "netdata.group=databases"
      - "netdata.type=postgresql"
      - "netdata.priority=high"
  
  api_father_redis:
    labels:
      - "netdata.group=databases"
      - "netdata.type=redis"
      - "netdata.priority=high"
  
  traefik:
    labels:
      - "netdata.group=infrastructure"
      - "netdata.type=gateway"
      - "netdata.priority=critical"
```

## Полезные метрики

### API Performance
- **Endpoint**: http://localhost:9101/api/v1/data?chart=docker.cpu
- Мониторинг CPU всех API контейнеров

### Database Health
- **MySQL**: Connections, queries/sec, slow queries
- **PostgreSQL**: Connections, transactions, cache hit ratio
- **Redis**: Commands/sec, memory usage, keyspace

### File Workers
- **btl_syncer**: Network I/O, disk reads
- **btl_compressor**: CPU usage, disk writes

### Infrastructure
- **Traefik**: HTTP requests/sec, response times, errors
- **WireGuard**: VPN traffic, connected peers

## Health Checks

Netdata автоматически проверяет:
- ✅ Container is running
- ✅ CPU < 90%
- ✅ Memory < 90% limit
- ✅ No network errors
- ✅ Disk not full

## Интеграция с Uptime Kuma

Настроить webhook в Netdata для отправки алертов в Uptime Kuma:

```yaml
# /etc/netdata/health_alarm_notify.conf
SEND_CUSTOM="YES"
CUSTOM_URL="http://uptime-kuma:3001/api/push/{monitorID}?status=down&msg="
```

## Export метрик

### Prometheus format
```bash
curl http://localhost:9101/api/v1/allmetrics?format=prometheus
```

### JSON format
```bash
curl http://localhost:9101/api/v1/charts
```

## Графики и Dashboard

### Создать custom dashboard
1. Перейти в http://localhost:9101
2. Нажать на иконку **Settings** (⚙️)
3. Выбрать **My nodes**
4. Добавить интересующие графики drag & drop

### Рекомендуемые графики
- **System Overview**: CPU, RAM, Network
- **Docker Containers**: All containers CPU/Memory
- **API Services**: api_1, api_2, api_father, api_4, api_mother
- **Databases**: MySQL, PostgreSQL, Redis
- **File Workers**: btl_syncer, btl_compressor
- **Infrastructure**: Traefik, WireGuard

## Retention

По умолчанию Netdata хранит:
- **Tier 0**: 1 секунда разрешение, 1 час хранение
- **Tier 1**: 1 минута разрешение, 1 день хранение
- **Tier 2**: 1 час разрешение, 1 месяц хранение

Изменить в `/etc/netdata/netdata.conf`:
```ini
[db]
    mode = dbengine
    storage tiers = 3
    dbengine multihost disk space MB = 2048
```

## Best Practices

1. **Регулярно проверяйте Dashboard**
2. **Настройте алерты для критичных сервисов**
3. **Мониторьте тренды (CPU/Memory growth)**
4. **Экспортируйте метрики в Prometheus для долговременного хранения**
5. **Используйте теги для группировки сервисов**










