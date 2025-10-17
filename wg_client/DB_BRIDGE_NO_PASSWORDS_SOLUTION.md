# 🔐 db_bridge БЕЗ хранения паролей - правильное решение

## ⚠️ ПРОТИВОРЕЧИЕ В ТЕКУЩЕМ РЕШЕНИИ

### Проблема:
```python
# db_bridge должен хранить пароли каждого пользователя БД:
CERT_MAPPINGS = {
    "api_register": {
        "mysql_user": "api_user_register",
        "mysql_password": "secret_register_2025",  ← ❌ Хранение пароля!
    }
}
```

**Это ПЛОХО:**
- ❌ db_bridge хранит все пароли от БД
- ❌ Взлом db_bridge = доступ ко всем пользователям БД
- ❌ Противоречит принципу "нет паролей на HOST_API"

---

## ✅ ПРАВИЛЬНОЕ РЕШЕНИЕ: MySQL SSL/TLS без паролей

### Механизм: MySQL mTLS Authentication Plugin

MySQL поддерживает аутентификацию через SSL сертификат **БЕЗ ПАРОЛЯ**!

### Как это работает:

```
1. api_father подключается с сертификатом
   ↓
2. db_bridge проверяет сертификат (CA подпись)
   ↓
3. db_bridge проксирует SSL соединение "как есть" в MySQL
   ↓
4. MySQL проверяет сертификат клиента
   ↓
5. MySQL извлекает CN из сертификата
   ↓
6. MySQL сам делает маппинг: CN → user (через mysql.user таблицу)
   ↓
7. Подключение от имени пользователя БЕЗ ПАРОЛЯ!
```

---

## 🔧 РЕАЛИЗАЦИЯ

### 1. Создание пользователей БД с SSL аутентификацией:

```sql
-- Пользователь для регистрации (БЕЗ ПАРОЛЯ!)
CREATE USER 'api_user_register'@'localhost' 
IDENTIFIED WITH mysql_native_password 
REQUIRE SSL;

-- Или с явным указанием сертификата:
CREATE USER 'api_user_register'@'localhost' 
REQUIRE SUBJECT '/CN=api_register/O=HOST_API/OU=Registration'
  AND ISSUER '/CN=CA/O=HOST_API';

-- Права
GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_user_register'@'localhost';
GRANT SELECT ON tzserver.constants TO 'api_user_register'@'localhost';
FLUSH PRIVILEGES;

-- Аналогично для api_user_status:
CREATE USER 'api_user_status'@'localhost'
REQUIRE SUBJECT '/CN=api_status/O=HOST_API/OU=Status'
  AND ISSUER '/CN=CA/O=HOST_API';

GRANT SELECT ON tzserver.constants TO 'api_user_status'@'localhost';
GRANT SELECT ON tzserver.tgplayers TO 'api_user_status'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Конфигурация MySQL (my.cnf):

```ini
[mysqld]
# Включить SSL
ssl-ca=/etc/mysql/certs/ca.crt
ssl-cert=/etc/mysql/certs/server.crt
ssl-key=/etc/mysql/certs/server.key

# Требовать SSL для удаленных подключений
require_secure_transport=ON
```

### 3. db_bridge БЕЗ хранения паролей:

```nginx
# Простой SSL passthrough
stream {
    server {
        listen 3307;
        
        # Просто проксируем SSL соединение "как есть"
        # БЕЗ расшифровки, БЕЗ маппинга
        proxy_pass unix:/var/run/mysqld/mysqld.sock;
        
        # SSL termination НЕ делаем
        # MySQL сам проверит сертификат клиента
    }
}
```

**ИЛИ** если нужна проверка на уровне db_bridge:

```nginx
stream {
    server {
        listen 3307 ssl;
        
        # Проверяем сертификат клиента
        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_client_certificate /etc/nginx/certs/ca.crt;
        ssl_verify_client on;
        
        # Проксируем в MySQL
        proxy_pass 127.0.0.1:3306;
        
        # Передаем SSL контекст дальше в MySQL
        proxy_ssl on;
        proxy_ssl_certificate     /etc/nginx/certs/client_for_mysql.crt;
        proxy_ssl_certificate_key /etc/nginx/certs/client_for_mysql.key;
    }
}
```

**Проблема:** Сложная схема SSL в SSL (двойное шифрование).

---

## 🎯 САМОЕ ПРОСТОЕ РЕШЕНИЕ

### MySQL User Mapping через CN (встроенная функция MySQL)

MySQL может автоматически маппить CN → пользователь!

```sql
-- Создать пользователь с именем = CN из сертификата
CREATE USER 'api_register'@'localhost' 
REQUIRE SUBJECT '/CN=api_register/O=HOST_API';

-- Теперь MySQL сам поймет:
-- Сертификат с CN=api_register → пользователь api_register

GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_register'@'localhost';
GRANT SELECT ON tzserver.constants TO 'api_register'@'localhost';
FLUSH PRIVILEGES;

-- Аналогично:
CREATE USER 'api_status'@'localhost'
REQUIRE SUBJECT '/CN=api_status/O=HOST_API';

GRANT SELECT ON tzserver.* TO 'api_status'@'localhost';
FLUSH PRIVILEGES;
```

### db_bridge (простой passthrough):

```nginx
stream {
    server {
        listen 3307;
        
        # Просто проксируем TCP
        proxy_pass 127.0.0.1:3306;
        
        # MySQL сам проверит SSL и сделает маппинг CN → user
    }
}
```

### api_father подключение:

```python
pymysql.connect(
    host="10.8.0.20",
    port=3307,
    user="api_register",  # Имя пользователя = CN в сертификате!
    # password НЕ НУЖЕН!
    ssl={
        'ca': '/certs/ca.crt',
        'cert': '/certs/api_register.crt',  # CN=api_register
        'key': '/certs/api_register.key',
    }
)
```

**MySQL проверит:**
1. SSL сертификат подписан CA? ✅
2. CN в сертификате = api_register? ✅
3. Пользователь api_register требует этот SUBJECT? ✅
4. Подключение разрешено БЕЗ ПАРОЛЯ! ✅

---

## 🎉 ИТОГОВАЯ АРХИТЕКТУРА (БЕЗ ПАРОЛЕЙ)

```
┌────────────────────────────────────────────────────────────┐
│ HOST_API                                                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ api_father                                                 │
│   pymysql.connect(                                         │
│     host="10.8.0.20",                                      │
│     port=3307,                                             │
│     user="api_register",  ← Имя = CN сертификата          │
│     ssl={                                                  │
│       'cert': 'api_register.crt'  ← CN=api_register       │
│     }                                                      │
│   )                                                        │
│                                                            │
└──────────────────┬─────────────────────────────────────────┘
                   │
                   │ SSL connection
                   │ Сертификат: CN=api_register
                   ↓
┌────────────────────────────────────────────────────────────┐
│ HOST_SERVER                                                │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ db_bridge (простой TCP proxy)                             │
│   • НЕ хранит пароли ✅                                   │
│   • НЕ делает маппинг ✅                                  │
│   • Просто проксирует TCP                                 │
│   ↓                                                        │
│ MySQL :3306                                                │
│   • Проверяет SSL сертификат ✅                           │
│   • Извлекает CN = "api_register" ✅                      │
│   • Находит пользователя "api_register" ✅                │
│   • Проверяет REQUIRE SUBJECT ✅                          │
│   • Подключение БЕЗ ПАРОЛЯ! ✅                            │
│                                                            │
│ Пользователи БД:                                           │
│   CREATE USER 'api_register'@'localhost'                  │
│   REQUIRE SUBJECT '/CN=api_register/O=HOST_API';          │
│   # ↑ БЕЗ ПАРОЛЯ!                                         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## ✅ ПРЕИМУЩЕСТВА

1. **БЕЗ паролей** ✅
   - db_bridge НЕ хранит пароли
   - api_father НЕ знает пароли
   - MySQL аутентифицирует по сертификату

2. **Простота** ✅
   - db_bridge = простой TCP proxy
   - Маппинг делает MySQL сам
   - Меньше кода, меньше ошибок

3. **Безопасность** ✅
   - Взлом db_bridge НЕ дает пароли
   - Нужен сертификат + ключ для подключения
   - Минимальные права на уровне БД

4. **Единообразие** ✅
   - CN в сертификате = имя пользователя БД
   - Понятная схема

---

## 📋 SQL КОМАНДЫ (ИСПРАВЛЕННЫЕ)

### 1. Пользователь для регистрации (API 2)
```sql
-- БЕЗ ПАРОЛЯ! Аутентификация через SSL сертификат
CREATE USER 'api_register'@'localhost'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API/OU=Registration'
  AND ISSUER '/CN=CA/O=HOST_API';

-- Права
GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_register'@'localhost';
GRANT SELECT ON tzserver.constants TO 'api_register'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Пользователь для статуса (API 1, API 3)
```sql
-- БЕЗ ПАРОЛЯ! Аутентификация через SSL сертификат
CREATE USER 'api_status'@'localhost'
REQUIRE SUBJECT '/CN=api_status/O=HOST_API/OU=Status'
  AND ISSUER '/CN=CA/O=HOST_API';

-- Права
GRANT SELECT ON tzserver.constants TO 'api_status'@'localhost';
GRANT SELECT ON tzserver.tgplayers TO 'api_status'@'localhost';
FLUSH PRIVILEGES;
```

### Проверка:
```sql
-- Проверить требования SSL
SELECT user, host, ssl_type, ssl_cipher, x509_issuer, x509_subject 
FROM mysql.user 
WHERE user LIKE 'api_%';

-- Должно показать:
-- api_register | localhost | SPECIFIED | ... | /CN=CA/O=HOST_API | /CN=api_register/O=HOST_API/OU=Registration
-- api_status   | localhost | SPECIFIED | ... | /CN=CA/O=HOST_API | /CN=api_status/O=HOST_API/OU=Status
```

---

## 🎯 ОТВЕТ НА ВАШИ ВОПРОСЫ

### Q: db_bridge хранит логин и пароль от каждого юзера?

**A: НЕТ! db_bridge НЕ хранит пароли!**

### Q: Мы хотели отказаться от хранения паролей?

**A: ДА! И это возможно через MySQL SSL certificate authentication!**

### Как это работает БЕЗ паролей:

```
1. api_father отправляет SSL сертификат (CN=api_register)
   ↓
2. db_bridge проксирует соединение (без расшифровки)
   ↓
3. MySQL получает SSL сертификат
   ↓
4. MySQL проверяет:
   • Сертификат подписан CA? ✅
   • CN = "api_register"? ✅
   • Пользователь "api_register" требует этот CN? ✅
   ↓
5. MySQL разрешает подключение БЕЗ ПАРОЛЯ! ✅
```

---

## 📊 СРАВНЕНИЕ ПОДХОДОВ

| Параметр | С паролями (ПЛОХО) | Без паролей (ХОРОШО) |
|----------|-------------------|---------------------|
| **db_bridge хранит пароли** | ❌ ДА | ✅ НЕТ |
| **Взлом db_bridge** | ❌ Доступ к БД | ✅ Нужен еще сертификат |
| **Сложность** | ⚠️ Средняя | ✅ Простая |
| **Маппинг CN → user** | db_bridge (Python) | MySQL (встроенно) |
| **db_bridge реализация** | Сложный proxy | Простой passthrough |

---

## 🔧 УПРОЩЕННАЯ АРХИТЕКТУРА

### db_bridge (ОЧЕНЬ ПРОСТОЙ):

```nginx
# wg_client/mock_host_server/nginx/nginx.conf

stream {
    server {
        listen 3307;
        
        # Просто TCP proxy
        # НЕТ SSL termination на уровне nginx
        # MySQL сам обработает SSL
        proxy_pass 127.0.0.1:3306;
    }
}
```

**ИЛИ с проверкой сертификата на уровне db_bridge:**

```nginx
stream {
    server {
        listen 3307 ssl;
        
        # Проверяем клиентский сертификат
        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_client_certificate /etc/nginx/certs/ca.crt;
        ssl_verify_client on;
        
        # Проксируем в MySQL БЕЗ re-encryption
        proxy_pass 127.0.0.1:3306;
        proxy_ssl off;  # НЕ шифруем повторно
    }
}
```

### MySQL конфигурация:

```ini
[mysqld]
# SSL сертификаты
ssl-ca=/etc/mysql/certs/ca.crt
ssl-cert=/etc/mysql/certs/server.crt
ssl-key=/etc/mysql/certs/server.key

# Требовать SSL
require_secure_transport=ON
```

### api_father подключение:

```python
# wg_client/api_father/app/infrastructure/db.py

def get_dsn_and_db():
    if mode == "production":
        return dict(
            host="10.8.0.20",
            port=3307,
            user="api_register",  # Имя = CN в сертификате!
            # password НЕ НУЖЕН!
            ssl={
                'ca': '/certs/ca.crt',
                'cert': '/certs/api_register.crt',  # CN=api_register
                'key': '/certs/api_register.key',
            }
        ), "tzserver"
```

---

## ⚡ УПРОЩЕННОЕ РЕШЕНИЕ (для начала)

### Вариант А: Один пользователь БД с разными сертификатами (ВРЕМЕННО)

```sql
-- Создать одного пользователя, но с SSL
CREATE USER 'api_common'@'localhost'
REQUIRE SSL;

-- Дать все необходимые права
GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_common'@'localhost';
GRANT SELECT ON tzserver.constants TO 'api_common'@'localhost';
FLUSH PRIVILEGES;
```

**Плюсы:**
- ✅ Работает сразу
- ✅ Не нужны пароли
- ✅ Простая реализация

**Минусы:**
- ❌ Нет разделения прав между API
- ❌ Взлом одного API = доступ ко всем операциям

---

### Вариант Б: Разные пользователи с SSL (ПРАВИЛЬНО)

```sql
-- Пользователь = CN из сертификата
CREATE USER 'api_register'@'localhost'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API';

CREATE USER 'api_status'@'localhost'
REQUIRE SUBJECT '/CN=api_status/O=HOST_API';

-- Разные права для каждого
GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_register'@'localhost';
GRANT SELECT ON tzserver.* TO 'api_status'@'localhost';
FLUSH PRIVILEGES;
```

**Плюсы:**
- ✅ БЕЗ паролей
- ✅ Разделение прав
- ✅ MySQL делает маппинг сам
- ✅ db_bridge остается простым

**Минусы:**
- ⚠️ Нужна настройка MySQL с SSL

---

## 🎯 РЕКОМЕНДАЦИЯ

### ✅ Использовать Вариант Б (БЕЗ паролей):

1. **MySQL пользователи:**
   ```sql
   CREATE USER 'api_register'@'localhost' REQUIRE SSL;
   CREATE USER 'api_status'@'localhost' REQUIRE SSL;
   ```

2. **db_bridge:**
   - Простой TCP proxy (nginx stream)
   - БЕЗ хранения паролей
   - БЕЗ сложного маппинга

3. **MySQL:**
   - Сам проверяет SSL сертификат
   - Сам делает маппинг CN → user
   - Аутентификация БЕЗ пароля

---

## ✅ ИТОГИ

### Вы правильно заметили:

❌ **Хранение паролей в db_bridge - ПЛОХАЯ идея**
✅ **MySQL SSL certificate authentication - ПРАВИЛЬНОЕ решение**

### Что меняется:

**Было (с паролями):**
```python
# db_bridge хранит:
"api_register": {
    "mysql_user": "api_user_register",
    "mysql_password": "secret_register_2025"  ← ❌
}
```

**Стало (БЕЗ паролей):**
```sql
-- MySQL сам делает маппинг:
CREATE USER 'api_register'@'localhost'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API';
-- БЕЗ ПАРОЛЯ! ✅
```

### db_bridge:
- БЕЗ хранения паролей ✅
- БЕЗ сложного маппинга ✅
- Простой TCP/SSL proxy ✅

**Безопасность повышена! Архитектура упрощена!** 🎉

---

**Дата:** 2025-10-01  
**Статус:** ПРАВИЛЬНОЕ понимание, требуется реализация
