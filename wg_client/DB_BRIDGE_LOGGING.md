# 📊 db_bridge - Логирование и мониторинг

## ✅ ДА, db_bridge ЛОГИРУЕТ!

### Что логируется:

```
┌─────────────────────────────────────────────────────────────┐
│ db_bridge (nginx stream)                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Логирует:                                                   │
│ ✅ IP клиента (кто подключается)                           │
│ ✅ Timestamp (когда)                                        │
│ ✅ CN из сертификата (какой API)                           │
│ ✅ Количество байт отправлено/получено                     │
│ ✅ Время сессии (latency)                                  │
│ ✅ Upstream адрес (MySQL)                                  │
│ ✅ Статус подключения (успех/ошибка)                       │
│                                                             │
│ НЕ логирует (по умолчанию):                                │
│ ❌ Содержимое SQL запросов (это сделал бы MySQL)           │
│ ❌ Результаты запросов                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 КОНФИГУРАЦИЯ ЛОГИРОВАНИЯ

### nginx stream log format:

```nginx
# db_bridge/nginx.conf

stream {
    # Формат лога
    log_format db_proxy '$remote_addr [$time_local] '
                        '$protocol $status $bytes_sent $bytes_received '
                        '$session_time "$upstream_addr" '
                        '$ssl_client_s_dn '  ← CN из сертификата!
                        '$upstream_bytes_sent $upstream_bytes_received '
                        '$upstream_connect_time';
    
    # Файлы логов
    access_log /var/log/nginx/db_bridge_access.log db_proxy;
    error_log  /var/log/nginx/db_bridge_error.log warn;
    
    server {
        listen 3307 ssl;
        
        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_client_certificate /etc/nginx/certs/ca.crt;
        ssl_verify_client on;
        
        proxy_pass 127.0.0.1:3306;
    }
}
```

---

## 📋 ПРИМЕР ЛОГОВ

### Access log (успешное подключение):

```
10.8.0.1 [01/Oct/2025:10:15:30 +0000] TCP 200 1024 2048 2.345 "127.0.0.1:3306" CN=api_register,O=HOST_API,OU=Registration 1024 2048 0.012
```

**Расшифровка:**
- `10.8.0.1` - IP клиента (HOST_API)
- `[01/Oct/2025:10:15:30 +0000]` - время
- `TCP` - протокол
- `200` - статус (успех)
- `1024` - байт отправлено клиенту
- `2048` - байт получено от клиента
- `2.345` - время сессии (секунды)
- `"127.0.0.1:3306"` - upstream (MySQL)
- `CN=api_register,O=HOST_API,OU=Registration` - из сертификата!
- `1024 2048` - байты upstream
- `0.012` - время подключения к upstream

### Error log (ошибка подключения):

```
2025/10/01 10:20:15 [error] 123#123: *456 upstream timed out (110: Connection timed out) while connecting to upstream, client: 10.8.0.1, server: 0.0.0.0:3307, upstream: "127.0.0.1:3306", bytes from/to client:0/0, bytes from/to upstream:0/0
```

### Error log (неправильный сертификат):

```
2025/10/01 10:25:00 [error] 123#123: *789 SSL_do_handshake() failed (SSL: error:14094418:SSL routines:ssl3_read_bytes:tlsv1 alert unknown ca) while SSL handshaking, client: 10.8.0.1, server: 0.0.0.0:3307
```

---

## 🔍 ЧТО ВИДНО В ЛОГАХ

### 1. Кто подключается:
```
Каждое подключение:
  IP: 10.8.0.1 (HOST_API)
  CN: api_register (API 2) или api_status (API 1/3)
```

### 2. Когда подключается:
```
Timestamp каждого подключения
Можно отследить:
  • Пики нагрузки
  • Частоту регистраций
  • Паттерны использования
```

### 3. Сколько данных передано:
```
bytes_sent: сколько отправлено клиенту (результаты SQL)
bytes_received: сколько получено от клиента (SQL запросы)

Можно отследить:
  • Размер результатов
  • Сложность запросов
  • Аномалии (слишком большие запросы)
```

### 4. Производительность:
```
session_time: общее время сессии
upstream_connect_time: время подключения к MySQL

Можно отследить:
  • Медленные запросы
  • Проблемы с БД
  • Latency
```

---

## 📊 МОНИТОРИНГ НА ОСНОВЕ ЛОГОВ

### Метрики (можно извлечь из логов):

```bash
# 1. Количество подключений по API
cat db_bridge_access.log | grep "CN=api_register" | wc -l
cat db_bridge_access.log | grep "CN=api_status" | wc -l

# 2. Средняя латентность
awk '{print $8}' db_bridge_access.log | awk '{sum+=$1; count++} END {print sum/count}'

# 3. Количество ошибок
grep -c "error" db_bridge_error.log

# 4. Самые активные клиенты
awk '{print $1}' db_bridge_access.log | sort | uniq -c | sort -nr

# 5. Распределение по времени
awk '{print $2}' db_bridge_access.log | cut -d: -f1-2 | uniq -c
```

---

## 🔐 БЕЗОПАСНОСТЬ: Что НЕ логируется

### ❌ НЕ логируется (и это хорошо):

1. **Содержимое SQL запросов**
   - db_bridge работает на уровне TCP
   - Не расшифровывает MySQL protocol
   - Не видит SQL команды

2. **Результаты запросов**
   - db_bridge не парсит MySQL результаты
   - Только видит размер (байты)

3. **Пароли** (их нет!)
   - Аутентификация через SSL
   - Пароли не передаются

### ✅ Если нужно логировать SQL:

**Включить на уровне MySQL:**

```sql
-- MySQL general query log
SET GLOBAL general_log = 'ON';
SET GLOBAL general_log_file = '/var/log/mysql/queries.log';

-- Или slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  # секунды
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow_queries.log';
```

**Плюсы:**
- Видно все SQL команды
- Можно оптимизировать запросы

**Минусы:**
- Большой объем логов
- Может содержать чувствительные данные

---

## 📈 РАСШИРЕННОЕ ЛОГИРОВАНИЕ (опционально)

### Вариант 1: db_bridge + SQL proxy

Если нужно логировать SQL, можно добавить промежуточный слой:

```
api_father → db_bridge:3307 → mysql_proxy:33071 → MySQL:3306
                               ↑
                          Логирует SQL
```

### Вариант 2: MySQL audit plugin

```sql
INSTALL PLUGIN audit_log SONAME 'audit_log.so';

SET GLOBAL audit_log_policy = 'ALL';
SET GLOBAL audit_log_format = 'JSON';
```

---

## 🎯 РЕКОМЕНДУЕМАЯ КОНФИГУРАЦИЯ

### db_bridge логирование:

```nginx
stream {
    log_format detailed '$remote_addr - $ssl_client_s_dn [$time_local] '
                        '$protocol $status '
                        'sent:$bytes_sent recv:$bytes_received '
                        'time:${session_time}s '
                        'upstream:"$upstream_addr" '
                        'up_time:${upstream_connect_time}s';
    
    access_log /var/log/nginx/db_bridge.log detailed;
    error_log  /var/log/nginx/db_bridge_error.log info;
    
    server {
        listen 3307 ssl;
        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_client_certificate /etc/nginx/certs/ca.crt;
        ssl_verify_client on;
        
        proxy_pass 127.0.0.1:3306;
    }
}
```

### Пример лога:

```
10.8.0.1 - CN=api_register,O=HOST_API,OU=Registration [01/Oct/2025:10:30:00 +0000] TCP 200 sent:512 recv:1024 time:0.234s upstream:"127.0.0.1:3306" up_time:0.005s
10.8.0.1 - CN=api_status,O=HOST_API,OU=Status [01/Oct/2025:10:30:05 +0000] TCP 200 sent:256 recv:128 time:0.102s upstream:"127.0.0.1:3306" up_time:0.002s
```

**Из этого лога видно:**
- Кто: CN=api_register (API 2) или CN=api_status (API 1/3)
- Откуда: 10.8.0.1 (HOST_API)
- Когда: точное время
- Сколько данных: 512 байт отправлено, 1024 получено
- Как быстро: 0.234 секунды общее время, 0.005 подключение к MySQL

---

## ✅ ИТОГИ

### db_bridge логирует:

✅ **ДА!** И это очень полезно:
- Видно какой API обращается (по CN)
- Видно когда и как часто
- Видно производительность (latency)
- Видно ошибки подключения

✅ **БЕЗ паролей:**
- db_bridge НЕ хранит пароли
- Аутентификация через SSL

✅ **Безопасно:**
- SQL команды НЕ логируются на уровне db_bridge
- Чувствительные данные защищены
- Можно включить SQL логи на MySQL если нужно

---

**Дата:** 2025-10-01  
**Статус:** db_bridge логирует метаданные, БЕЗ SQL содержимого
