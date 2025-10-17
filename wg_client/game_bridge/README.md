# 🎮 game_bridge - TCP Proxy для Game Server

## Назначение

`game_bridge` - это TCP прокси на базе nginx stream, который обеспечивает:

1. **Изоляцию Game Server** - Game Server слушает только localhost
2. **IP filtering** - доступ только с HOST_API (10.8.0.1)
3. **Логирование** - все подключения и запросы логируются
4. **Мониторинг** - метрики подключений, байты, латентность

## Архитектура

```
api_father (HOST_API, 10.8.0.1)
    ↓ socket.connect(10.8.0.20, 5191)
    ↓ через VPN
game_bridge (HOST_SERVER, 0.0.0.0:5191)
    ├─ Проверка IP (whitelist)
    ├─ Логирование
    └─ Прокси на localhost:5190
        ↓
Game Server (127.0.0.1:5190)
    ├─ Слушает ТОЛЬКО localhost
    └─ Полностью изолирован
```

## Конфигурация

### nginx.conf

- **Порт:** 5191 (открыт в VPN)
- **Upstream:** 127.0.0.1:5190 (Game Server на localhost)
- **IP whitelist:** 10.8.0.1 (раскомментировать в проде)
- **Таймауты:** connect=5s, proxy=10s
- **Логи:** `/var/log/nginx/game_bridge_*.log`

### Переменные окружения

Не требуются - вся конфигурация в `nginx.conf`

## Использование

### Локально (для тестов)

```bash
# Собрать образ
docker build -t game_bridge:local wg_client/game_bridge/

# Запустить
docker run -d \
  --name game_bridge_local \
  --network host \
  game_bridge:local
```

### В продакшне

Добавлено в `HOST_API_SERVICE_UTILITIES.yml`:

```yaml
game_bridge:
  build:
    context: ./game_bridge
  container_name: ${PROJECT_NAME}-game_bridge
  networks:
    - backnet
  ports:
    - "5191:5191"
  restart: unless-stopped
```

## Логи

### Просмотр логов

```bash
# Логи доступа
docker exec game_bridge cat /var/log/nginx/game_bridge_access.log

# Логи ошибок
docker exec game_bridge cat /var/log/nginx/game_bridge_error.log

# Через docker logs
docker logs game_bridge
```

### Формат лога

```
<client_ip> [<timestamp>] <protocol> <status> <sent_bytes> <recv_bytes> <session_time> "<upstream>" ...
```

Пример:
```
10.8.0.1 [01/Oct/2025:10:15:30 +0000] TCP 200 256 512 0.123 "127.0.0.1:5190" 256 512 0.001
```

## Мониторинг

### Метрики

- **Количество подключений:** считается из логов
- **Байты отправлено/получено:** `$bytes_sent`, `$bytes_received`
- **Латентность:** `$session_time`
- **Ошибки подключения:** error.log

### Проверка работоспособности

```bash
# Тест подключения
echo '<ADDUSER l="test" p="test" g="1" m="test@test.ru"/>' | nc game_bridge 5191

# Статус nginx
docker exec game_bridge nginx -t
```

## Безопасность

### IP Whitelisting (ПРОДАКШН)

В проде раскомментировать в `nginx.conf`:

```nginx
allow 10.8.0.1;
deny all;
```

Это разрешит подключения **ТОЛЬКО** с HOST_API (10.8.0.1).

### Изоляция Game Server

Game Server должен слушать **ТОЛЬКО** localhost:

```bash
# В конфигурации Game Server:
bind_address = 127.0.0.1
port = 5190
```

### Rate Limiting (опционально)

Добавить в `nginx.conf`:

```nginx
limit_conn_zone $binary_remote_addr zone=game_conn:10m;
limit_conn game_conn 10;  # макс 10 одновременных подключений
```

## Сравнение с db_bridge

| Параметр | db_bridge | game_bridge |
|----------|-----------|-------------|
| Протокол | MySQL (TCP) | Socket TCP |
| Порт | 3307 | 5191 |
| Backend | MySQL (unix-socket) | Game Server :5190 |
| Защита | mTLS | IP whitelist |
| Логи | ✅ | ✅ |
| Технология | nginx stream | nginx stream |

## Troubleshooting

### Game Server недоступен

```bash
# Проверить, что Game Server слушает localhost:5190
netstat -tlnp | grep 5190

# Проверить логи game_bridge
docker logs game_bridge
```

### Подключение отклоняется

```bash
# Проверить IP whitelist
# Если включен, убедиться что client IP = 10.8.0.1

# Временно отключить для теста
# Закомментировать allow/deny в nginx.conf
```

### Таймауты

```bash
# Увеличить таймауты в nginx.conf:
proxy_connect_timeout 10s;
proxy_timeout 30s;
```

## TODO

- [ ] Добавить Prometheus exporter для метрик
- [ ] Настроить автоматическую ротацию логов
- [ ] Добавить health check endpoint
- [ ] Rate limiting для защиты от DDoS











