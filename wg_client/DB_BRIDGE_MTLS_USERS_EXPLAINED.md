# 🔐 db_bridge: Разделение пользователей БД через mTLS

## 🎯 ВАШЕ ПРАВИЛЬНОЕ ПОНИМАНИЕ

Вы правильно помните: **один db_bridge + несколько пользователей БД**

Каждый API использует свой mTLS сертификат → свой пользователь БД → свои права!

---

## 🔍 КАК db_bridge ОПРЕДЕЛЯЕТ ПОЛЬЗОВАТЕЛЯ?

### Механизм: mTLS Client Certificate Common Name (CN)

```
┌────────────────────────────────────────────────────────────────┐
│ api_father (HOST_API)                                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ pymysql.connect(                                               │
│     host="10.8.0.20",                                          │
│     port=3307,                                                 │
│     user="api_register",  ← ЭТОТ параметр игнорируется!       │
│     ssl={                                                      │
│         'ca': '/certs/ca.crt',                                 │
│         'cert': '/certs/api_register.crt',  ← ВАЖНО!          │
│         'key': '/certs/api_register.key',                      │
│     }                                                          │
│ )                                                              │
│                                                                │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         │ mTLS connection
                         │ Сертификат: CN=api_register
                         ↓
┌────────────────────────────────────────────────────────────────┐
│ db_bridge (HOST_SERVER :3307)                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ nginx stream + ssl_preread                                    │
│                                                                │
│ 1. Принимает подключение                                      │
│ 2. Читает SSL certificate                                     │
│ 3. Извлекает CN (Common Name) из сертификата                  │
│    ↓                                                           │
│    CN = "api_register"  ← из сертификата!                     │
│                                                                │
│ 4. Маппинг CN → MySQL user:                                   │
│    ┌──────────────────────────────────────────────────┐       │
│    │ if CN == "api_register":                         │       │
│    │     mysql_user = "user_register"                 │       │
│    │     mysql_password = "pass_register"             │       │
│    │                                                  │       │
│    │ elif CN == "api_readonly":                       │       │
│    │     mysql_user = "user_readonly"                 │       │
│    │     mysql_password = "pass_readonly"             │       │
│    │                                                  │       │
│    │ elif CN == "api_analytics":                      │       │
│    │     mysql_user = "user_analytics"                │       │
│    │     mysql_password = "pass_analytics"            │       │
│    │                                                  │       │
│    │ else:                                            │       │
│    │     deny connection                              │       │
│    └──────────────────────────────────────────────────┘       │
│                                                                │
│ 5. Подключается к MySQL с выбранным пользователем             │
│    ↓                                                           │
└────┼───────────────────────────────────────────────────────────┘
     │
     │ MySQL protocol
     │ USER: user_register (из маппинга!)
     ↓
┌────────────────────────────────────────────────────────────────┐
│ MySQL (unix-socket)                                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ Подключение от: user_register                                 │
│                                                                │
│ GRANT для user_register:                                      │
│   ✅ SELECT на tgplayers (проверка лимита)                    │
│   ✅ INSERT на tgplayers (создание игрока)                    │
│   ❌ DELETE на tgplayers (запрещено!)                         │
│   ❌ DROP TABLE (запрещено!)                                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 📋 РАЗДЕЛЕНИЕ ПОЛЬЗОВАТЕЛЕЙ

### Сертификаты (HOST_API):

```
/certs/
├── ca.crt              # CA для проверки
├── api_register.crt    # CN=api_register (для API 2 - регистрация)
├── api_register.key
├── api_readonly.crt    # CN=api_readonly (для API 1 - чтение)
├── api_readonly.key
├── api_analytics.crt   # CN=api_analytics (для API 4 - аналитика)
└── api_analytics.key
```

### Пользователи БД (HOST_SERVER):

```sql
-- 1. Для регистрации (API 2 → api_father)
CREATE USER 'user_register'@'localhost' IDENTIFIED BY 'pass_register';
GRANT SELECT, INSERT ON tzserver.tgplayers TO 'user_register'@'localhost';
GRANT SELECT ON tzserver.constants TO 'user_register'@'localhost';
-- НЕТ: UPDATE, DELETE, DROP

-- 2. Для чтения (API 1 → api_father)
CREATE USER 'user_readonly'@'localhost' IDENTIFIED BY 'pass_readonly';
GRANT SELECT ON tzserver.constants TO 'user_readonly'@'localhost';
-- ТОЛЬКО SELECT!

-- 3. Для аналитики (API 4 → api_father)
CREATE USER 'user_analytics'@'localhost' IDENTIFIED BY 'pass_analytics';
GRANT SELECT ON tzserver.* TO 'user_analytics'@'localhost';
-- Только чтение всех таблиц
```

---

## 🔧 РЕАЛИЗАЦИЯ В db_bridge

### Вариант 1: nginx stream + ssl_preread + map

```nginx
stream {
    # Извлекаем CN из сертификата
    map $ssl_client_s_dn $mysql_backend {
        ~CN=api_register   mysql_register;
        ~CN=api_readonly   mysql_readonly;
        ~CN=api_analytics  mysql_analytics;
        default            deny;
    }
    
    # Upstream для каждого пользователя
    upstream mysql_register {
        server unix:/var/run/mysqld/register.sock;
    }
    
    upstream mysql_readonly {
        server unix:/var/run/mysqld/readonly.sock;
    }
    
    upstream mysql_analytics {
        server unix:/var/run/mysqld/analytics.sock;
    }
    
    upstream deny {
        server 127.0.0.1:1;  # несуществующий порт
    }
    
    server {
        listen 3307 ssl;
        
        ssl_certificate     /etc/nginx/certs/server/server.crt;
        ssl_certificate_key /etc/nginx/certs/server/server.key;
        ssl_client_certificate /etc/nginx/certs/ca.crt;
        ssl_verify_client on;
        
        ssl_preread on;
        
        proxy_pass $mysql_backend;
    }
}
```

**Проблема:** nginx stream не может напрямую подключаться к MySQL с разными пользователями через один unix-socket!

---

### Вариант 2: Отдельные порты для каждого пользователя (ПРОСТОЕ РЕШЕНИЕ)

```nginx
stream {
    # Регистрация - порт 3307
    server {
        listen 3307 ssl;
        
        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_client_certificate /etc/nginx/certs/ca.crt;
        ssl_verify_client on;
        
        # Проверка CN
        ssl_verify_depth 2;
        
        proxy_pass 127.0.0.1:33071;  # MySQL proxy для user_register
    }
    
    # Readonly - порт 3308
    server {
        listen 3308 ssl;
        
        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_client_certificate /etc/nginx/certs/ca.crt;
        ssl_verify_client on;
        
        proxy_pass 127.0.0.1:33072;  # MySQL proxy для user_readonly
    }
}
```

Затем отдельные MySQL proxy процессы подключаются к MySQL с разными пользователями.

**Проблема:** Сложная архитектура, много процессов.

---

### Вариант 3: Python/Go proxy с mTLS маппингом (РЕКОМЕНДУЕМОЕ)

```python
# db_bridge/bridge.py

import socket
import ssl
import mysql.connector

# Маппинг CN → MySQL credentials
CERT_TO_USER = {
    "api_register": {
        "user": "user_register",
        "password": "pass_register",
        "grants": ["SELECT", "INSERT"],
    },
    "api_readonly": {
        "user": "user_readonly", 
        "password": "pass_readonly",
        "grants": ["SELECT"],
    },
    "api_analytics": {
        "user": "user_analytics",
        "password": "pass_analytics",
        "grants": ["SELECT"],
    },
}

def handle_client(client_sock, client_cert):
    # Извлекаем CN из сертификата
    cn = client_cert.get('subject', ((),))[0][0][1]
    
    # Получаем credentials для MySQL
    if cn not in CERT_TO_USER:
        client_sock.close()
        return
    
    mysql_creds = CERT_TO_USER[cn]
    
    # Подключаемся к MySQL с нужным пользователем
    mysql_conn = mysql.connector.connect(
        unix_socket='/var/run/mysqld/mysqld.sock',
        user=mysql_creds['user'],
        password=mysql_creds['password'],
        database='tzserver'
    )
    
    # Проксируем данные между client и MySQL
    proxy_data(client_sock, mysql_conn)
```

**Преимущества:**
- ✅ Полный контроль над маппингом
- ✅ Легко добавить логирование по пользователю
- ✅ Можно добавить дополнительные проверки

---

## 🎯 ТЕКУЩАЯ СИТУАЦИЯ В ПРОЕКТЕ

### ⚠️ ПРОБЛЕМА: Сейчас НЕ реализовано разделение!

Проверяю текущий код:

```python
# wg_client/api_father/app/infrastructure/db.py

def get_dsn_and_db():
    mode = os.getenv("DB_MODE")
    
    if mode == "production":
        return dict(
            host="10.8.0.20",
            port=3307,  # db_bridge
            user="api_register",  ← Это НЕ работает с текущим db_bridge!
            password="...",       ← Пароль игнорируется в mTLS
        ), "tzserver"
```

### Текущая реализация db_bridge (mock):

```nginx
# wg_client/mock_host_server/nginx/nginx.conf

stream {
    server {
        listen 3307 ssl;
        
        ssl_certificate     /etc/nginx/certs/server/server.crt;
        ssl_certificate_key /etc/nginx/certs/server/server.key;
        ssl_client_certificate /etc/nginx/certs/ca.crt;
        ssl_verify_client on;
        
        proxy_pass 127.0.0.1:3306;  ← Прокси на MySQL БЕЗ маппинга!
    }
}
```

**Проблема:** Нет маппинга CN → MySQL user!

---

## ✅ ЧТО НУЖНО СДЕЛАТЬ

### 1. Создать отдельные сертификаты для API:

```bash
# API 2 (регистрация)
openssl req -new -key api_register.key -out api_register.csr \
    -subj "/CN=api_register/O=HOST_API/OU=Registration"

# API 1 (readonly)
openssl req -new -key api_readonly.key -out api_readonly.csr \
    -subj "/CN=api_readonly/O=HOST_API/OU=Readonly"

# API 4 (analytics)
openssl req -new -key api_analytics.key -out api_analytics.csr \
    -subj "/CN=api_analytics/O=HOST_API/OU=Analytics"
```

### 2. Создать пользователей MySQL с разными правами:

```sql
-- Пользователь для регистрации (API 2)
CREATE USER 'user_register'@'localhost' IDENTIFIED BY 'register_secret';
GRANT SELECT, INSERT ON tzserver.tgplayers TO 'user_register'@'localhost';
GRANT SELECT ON tzserver.constants TO 'user_register'@'localhost';

-- Пользователь для чтения (API 1, API 3)
CREATE USER 'user_readonly'@'localhost' IDENTIFIED BY 'readonly_secret';
GRANT SELECT ON tzserver.constants TO 'user_readonly'@'localhost';
GRANT SELECT ON tzserver.tgplayers TO 'user_readonly'@'localhost';

-- Пользователь для аналитики (API 4)
CREATE USER 'user_analytics'@'localhost' IDENTIFIED BY 'analytics_secret';
GRANT SELECT ON tzserver.* TO 'user_analytics'@'localhost';
```

### 3. Реализовать маппинг в db_bridge

**РЕКОМЕНДУЕМОЕ РЕШЕНИЕ:** Python/Go proxy

```python
# db_bridge/mysql_proxy.py

import ssl
import socket
import mysql.connector

# Маппинг сертификатов → пользователи БД
CERT_MAPPINGS = {
    "api_register": {
        "mysql_user": "user_register",
        "mysql_password": "register_secret",
        "description": "API 2 - регистрация игроков",
    },
    "api_readonly": {
        "mysql_user": "user_readonly",
        "mysql_password": "readonly_secret",
        "description": "API 1, API 3 - чтение данных",
    },
    "api_analytics": {
        "mysql_user": "user_analytics",
        "mysql_password": "analytics_secret",
        "description": "API 4 - аналитика",
    },
}

def handle_connection(client_sock, ssl_context):
    # 1. SSL handshake
    ssl_sock = ssl_context.wrap_socket(client_sock, server_side=True)
    
    # 2. Получаем сертификат клиента
    cert = ssl_sock.getpeercert()
    
    # 3. Извлекаем CN
    cn = None
    for field in cert.get('subject', ()):
        for key, value in field:
            if key == 'commonName':
                cn = value
                break
    
    # 4. Проверяем маппинг
    if cn not in CERT_MAPPINGS:
        print(f"[DENY] Unknown CN: {cn}")
        ssl_sock.close()
        return
    
    mapping = CERT_MAPPINGS[cn]
    print(f"[ALLOW] CN={cn} → MySQL user={mapping['mysql_user']}")
    
    # 5. Подключаемся к MySQL с нужным пользователем
    mysql_conn = mysql.connector.connect(
        unix_socket='/var/run/mysqld/mysqld.sock',
        user=mapping['mysql_user'],
        password=mapping['mysql_password'],
        database='tzserver'
    )
    
    # 6. Проксируем данные
    proxy_bidirectional(ssl_sock, mysql_conn.get_socket())
```

---

## 📊 ТАБЛИЦА РАЗДЕЛЕНИЯ ПРАВ

| API | Сертификат (CN) | MySQL User | Права | Назначение |
|-----|----------------|------------|-------|------------|
| **API 2** | `api_register` | `user_register` | SELECT, INSERT | Регистрация игроков |
| **API 1** | `api_readonly` | `user_readonly` | SELECT | Получение констант |
| **API 3** | `api_readonly` | `user_readonly` | SELECT | Информация о сервере |
| **API 4** | `api_analytics` | `user_analytics` | SELECT (все таблицы) | Аналитика |

### Пример прав:

```sql
-- user_register (API 2)
✅ SELECT COUNT(*) FROM tgplayers WHERE telegram_id = ?
✅ SELECT 1 FROM tgplayers WHERE login = ?
✅ INSERT INTO tgplayers (telegram_id, username, login) VALUES (?, ?, ?)
❌ DELETE FROM tgplayers  -- ЗАПРЕЩЕНО!
❌ UPDATE tgplayers SET login = 'hacker'  -- ЗАПРЕЩЕНО!

-- user_readonly (API 1, API 3)
✅ SELECT Name, Value FROM constants
✅ SELECT login FROM tgplayers WHERE telegram_id = ?
❌ INSERT INTO tgplayers  -- ЗАПРЕЩЕНО!
❌ DELETE FROM tgplayers  -- ЗАПРЕЩЕНО!

-- user_analytics (API 4)
✅ SELECT * FROM tgplayers
✅ SELECT * FROM battles
✅ SELECT * FROM любая_таблица  -- только чтение!
❌ INSERT, UPDATE, DELETE  -- ЗАПРЕЩЕНО!
```

---

## 🔄 КАК ЭТО РАБОТАЕТ (полная цепочка)

### Регистрация (API 2):

```
1. api_father (HOST_API)
   pymysql.connect(
       host="10.8.0.20", 
       port=3307,
       user="api_register",  ← В коде указан, но игнорируется
       ssl={
           'cert': '/certs/api_register.crt'  ← CN=api_register
       }
   )
   ↓
2. db_bridge читает сертификат
   CN = "api_register"
   ↓
3. db_bridge маппинг
   CN="api_register" → mysql_user="user_register"
   ↓
4. db_bridge подключается к MySQL
   mysql.connect(
       unix_socket='/var/run/mysqld/mysqld.sock',
       user='user_register',  ← ИЗ МАППИНГА!
       password='register_secret'
   )
   ↓
5. MySQL проверяет права
   user_register имеет: SELECT, INSERT на tgplayers ✅
   ↓
6. Выполняет: SELECT COUNT(*) FROM tgplayers WHERE telegram_id = ?
   ✅ УСПЕХ (есть права)
   ↓
7. Возвращает результат через db_bridge → api_father
```

### Попытка хакнуть (неправильный сертификат):

```
1. Злоумышленник пытается:
   pymysql.connect(
       host="10.8.0.20",
       port=3307,
       ssl={'cert': '/certs/FAKE.crt'}  ← CN=hacker
   )
   ↓
2. db_bridge проверяет сертификат
   CN = "hacker"
   ↓
3. CN не найден в CERT_MAPPINGS
   ↓
4. db_bridge закрывает соединение
   ❌ ДОСТУП ЗАПРЕЩЕН!
```

---

## 🎯 ОТВЕТЫ НА ВАШИ ВОПРОСЫ

### Q1: Под каким пользователем API Father делает SELECT COUNT(*)?

**A:** Под `user_register` (определяется по сертификату `api_register.crt`)

```
api_father использует сертификат: api_register.crt (CN=api_register)
    ↓
db_bridge видит CN="api_register"
    ↓
db_bridge подключается к MySQL как: user_register
    ↓
MySQL выполняет запрос от имени: user_register
```

### Q2: Как db_bridge понимает какого пользователя использовать?

**A:** По **Common Name (CN)** из mTLS сертификата клиента!

```
Клиент отправляет сертификат → db_bridge читает CN → маппинг CN → MySQL user
```

### Q3: Мы договорились о разных пользователях для каждого API?

**A:** ✅ ДА! Но сейчас это НЕ реализовано в mock db_bridge!

**ЧТО ЕСТЬ СЕЙЧАС:**
- ❌ mock_db_bridge просто проксирует на MySQL без маппинга
- ❌ Все подключения используют одного пользователя БД

**ЧТО НУЖНО:**
- ✅ Реализовать маппинг CN → MySQL user
- ✅ Создать 3 пользователя БД с разными правами
- ✅ Выдать 3 сертификата с разными CN

---

## 📝 РЕКОМЕНДАЦИИ

### Для текущих тестов (локал):
**Можно оставить как есть** - один пользователь БД для простоты.

### Для продакшна:
**ОБЯЗАТЕЛЬНО реализовать:**
1. Python/Go db_bridge с маппингом CN → MySQL user
2. Создать отдельных пользователей БД
3. Выдать сертификаты для каждого API
4. Настроить минимальные права для каждого пользователя

---

## 🔐 БЕЗОПАСНОСТЬ: Почему это важно?

### Сценарий атаки (без разделения):
```
1. Взлом API 1 (readonly)
2. Получение сертификата api_readonly.crt
3. Подключение к db_bridge
4. БЕЗ маппинга → тот же user с правами INSERT/DELETE
5. ❌ Хакер может удалить всех игроков!
```

### С разделением:
```
1. Взлом API 1 (readonly)
2. Получение сертификата api_readonly.crt
3. Подключение к db_bridge
4. db_bridge: CN=api_readonly → user_readonly
5. MySQL: user_readonly имеет ТОЛЬКО SELECT
6. ✅ Попытка DELETE FROM tgplayers → ERROR 1142 (42000): 
   DELETE command denied to user 'user_readonly'
```

---

## ✅ ИТОГИ

### Сейчас в проекте:
- ❌ db_bridge БЕЗ маппинга пользователей
- ⚠️ Подходит для локальных тестов
- ❌ НЕ подходит для прода

### Что нужно для прода:
1. ✅ Реализовать db_bridge с маппингом CN → MySQL user
2. ✅ Создать 3 пользователя БД (register, readonly, analytics)
3. ✅ Выдать 3 сертификата (api_register, api_readonly, api_analytics)
4. ✅ Настроить GRANT для каждого пользователя

### Приоритет:
- **Локал (сейчас):** Можно отложить (1 пользователь БД)
- **Прод:** КРИТИЧНО реализовать!

---

**Дата:** 2025-10-01  
**Статус:** Требуется реализация для прода
