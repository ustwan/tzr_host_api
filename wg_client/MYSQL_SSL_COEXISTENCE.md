# 🔐 MySQL: SSL пользователи + обычные пользователи одновременно

## ✅ ОТВЕТ: ДА, можно!

MySQL позволяет иметь **разные требования для разных пользователей**.

---

## 📊 ТАБЛИЦА СОСУЩЕСТВОВАНИЯ

| Пользователь | Требование | Аутентификация | Использование | Затронут? |
|--------------|-----------|----------------|---------------|-----------|
| `root` | NONE | Пароль | Администрирование | ❌ НЕТ |
| `tzuser` | NONE | Пароль | Тестовая БД | ❌ НЕТ |
| `gameuser` | NONE | Пароль | Game Server | ❌ НЕТ |
| `api_register` | REQUIRE SSL | SSL сертификат (БЕЗ пароля) | HOST_API (API 2) | ✅ НОВЫЙ |
| `api_status` | REQUIRE SSL | SSL сертификат (БЕЗ пароля) | HOST_API (API 1, 3) | ✅ НОВЫЙ |

---

## 🔧 КАК ЭТО РАБОТАЕТ

### Конфигурация MySQL (my.cnf):

```ini
[mysqld]
# Включить SSL (делает SSL ДОСТУПНЫМ для всех)
ssl-ca=/etc/mysql/certs/ca.crt
ssl-cert=/etc/mysql/certs/mysql_server.crt
ssl-key=/etc/mysql/certs/mysql_server.key

# ❌ НЕ включать require_secure_transport=ON
# Это бы ТРЕБОВАЛО SSL для ВСЕХ пользователей!

# ✅ Вместо этого: требование SSL на уровне отдельных пользователей
```

### Создание пользователей:

```sql
-- Существующие пользователи (БЕЗ изменений):
-- root, tzuser, gameuser - продолжают работать с паролями

-- Новые пользователи (с SSL):
CREATE USER 'api_register'@'localhost'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API/OU=Registration';
-- ↑ Только ЭТОТ пользователь требует SSL!

CREATE USER 'api_status'@'localhost'
REQUIRE SUBJECT '/CN=api_status/O=HOST_API/OU=Status';
-- ↑ Только ЭТОТ пользователь требует SSL!
```

---

## ✅ ПРИМЕРЫ ПОДКЛЮЧЕНИЙ

### 1. Старый пользователь (tzuser) - работает как раньше:

```bash
# С паролем (как всегда):
mysql -utzuser -ptzpass tzserver
# ✅ Успех! Пароль принят, SSL не требуется

# Даже БЕЗ SSL сервер примет подключение
mysql -h127.0.0.1 -utzuser -ptzpass tzserver
# ✅ Успех!
```

### 2. Новый пользователь (api_register) - требует SSL:

```bash
# Попытка с паролем:
mysql -uapi_register -psomepassword tzserver
# ❌ ERROR: Access denied (SSL required)

# С SSL сертификатом:
mysql -uapi_register \
  --ssl-cert=/certs/api_register.crt \
  --ssl-key=/certs/api_register.key \
  --ssl-ca=/certs/ca.crt \
  tzserver
# ✅ Успех! SSL сертификат принят, пароль НЕ нужен
```

### 3. Game Server пользователь - не затронут:

```bash
# Продолжает работать с паролем:
mysql -ugameuser -pgamepass tzserver
# ✅ Успех! Все как раньше
```

---

## 🎯 ВАЖНЫЕ МОМЕНТЫ

### 1. require_secure_transport vs REQUIRE в пользователе

```sql
-- ГЛОБАЛЬНО (для ВСЕХ пользователей):
[mysqld]
require_secure_transport=ON  ← ❌ НЕ используем!

-- ПО ОТДЕЛЬНОСТИ (для конкретных пользователей):
CREATE USER 'api_register'@'localhost' 
REQUIRE SSL;  ← ✅ Используем!
```

### 2. Типы REQUIRE:

```sql
-- Требовать ЛЮБОЙ валидный SSL:
CREATE USER 'user1'@'localhost' REQUIRE SSL;

-- Требовать конкретный SUBJECT (CN):
CREATE USER 'user2'@'localhost' 
REQUIRE SUBJECT '/CN=api_register/O=HOST_API';

-- Требовать SUBJECT + ISSUER:
CREATE USER 'user3'@'localhost'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API'
  AND ISSUER '/CN=CA/O=HOST_API';

-- Без требований (обычный пароль):
CREATE USER 'user4'@'localhost' IDENTIFIED BY 'password';
```

### 3. Проверка требований:

```sql
-- Посмотреть все пользователи и их требования
SELECT user, host, ssl_type, x509_subject 
FROM mysql.user
ORDER BY ssl_type DESC, user;

-- Результат:
-- user         | host      | ssl_type  | x509_subject
-- -------------|-----------|-----------|---------------------------
-- api_register | localhost | SPECIFIED | /CN=api_register/O=HOST_API/OU=Registration
-- api_status   | localhost | SPECIFIED | /CN=api_status/O=HOST_API/OU=Status
-- root         | localhost | (NULL)    | (NULL) ← работает с паролем
-- tzuser       | %         | (NULL)    | (NULL) ← работает с паролем
-- gameuser     | localhost | (NULL)    | (NULL) ← работает с паролем
```

---

## 🔄 МИГРАЦИЯ (как добавить SSL пользователей к существующей БД)

### Сценарий: БД уже работает с обычными пользователями

```sql
-- Текущие пользователи (НЕ трогаем):
-- root@localhost (пароль)
-- gameuser@localhost (пароль)
-- tzuser@% (пароль)

-- Шаг 1: Настроить MySQL с SSL (только включить, НЕ требовать)
-- vim /etc/mysql/my.cnf
-- ssl-ca=/etc/mysql/certs/ca.crt
-- ssl-cert=/etc/mysql/certs/mysql_server.crt
-- ssl-key=/etc/mysql/certs/mysql_server.key
-- (БЕЗ require_secure_transport=ON!)

-- Шаг 2: Перезапустить MySQL
-- systemctl restart mysql

-- Шаг 3: Проверить что старые пользователи работают
mysql -utzuser -ptzpass tzserver
-- ✅ Должно работать как раньше!

-- Шаг 4: Создать новых пользователей с SSL
CREATE USER 'api_register'@'localhost'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API/OU=Registration';

CREATE USER 'api_status'@'localhost'
REQUIRE SUBJECT '/CN=api_status/O=HOST_API/OU=Status';

GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_register'@'localhost';
GRANT SELECT ON tzserver.* TO 'api_status'@'localhost';
FLUSH PRIVILEGES;

-- Шаг 5: Проверить что оба типа работают
mysql -utzuser -ptzpass tzserver  ✅ Старый (с паролем)
mysql -uapi_register --ssl-cert=... tzserver  ✅ Новый (с SSL)
```

---

## ⚠️ РАСПРОСТРАНЕННЫЕ ОШИБКИ

### Ошибка 1: Включили require_secure_transport=ON

```ini
[mysqld]
require_secure_transport=ON  ← ❌ ПЛОХО!
```

**Проблема:**
- ВСЕ пользователи требуют SSL
- root, tzuser, gameuser перестанут работать
- Нужно создавать SSL сертификаты для всех

**Решение:**
```ini
[mysqld]
# Убрать эту строку!
# require_secure_transport=ON  ← удалить или закомментировать
```

### Ошибка 2: Забыли включить SSL в MySQL

```ini
[mysqld]
# Забыли добавить:
ssl-ca=/etc/mysql/certs/ca.crt  ← НУЖНО!
```

**Проблема:**
- SSL недоступен для ВСЕХ пользователей
- Новые пользователи с REQUIRE SSL не смогут подключиться

**Решение:**
```ini
[mysqld]
ssl-ca=/etc/mysql/certs/ca.crt
ssl-cert=/etc/mysql/certs/mysql_server.crt
ssl-key=/etc/mysql/certs/mysql_server.key
# Это делает SSL ДОСТУПНЫМ (но не обязательным)
```

---

## ✅ ИТОГОВАЯ КОНФИГУРАЦИЯ (безопасная + обратно совместимая)

### MySQL конфиг (my.cnf):

```ini
[mysqld]
bind-address = 127.0.0.1
port = 3306

# SSL доступен (но НЕ обязателен для всех)
ssl-ca=/etc/mysql/certs/ca.crt
ssl-cert=/etc/mysql/certs/mysql_server.crt
ssl-key=/etc/mysql/certs/mysql_server.key
tls-version=TLSv1.2,TLSv1.3

# ❌ НЕ включаем require_secure_transport
```

### Пользователи БД:

```sql
-- Старые пользователи (НЕ меняем):
-- root@localhost - пароль
-- tzuser@% - пароль
-- gameuser@localhost - пароль
-- ✅ Все работают как раньше!

-- Новые пользователи (с SSL):
CREATE USER 'api_register'@'localhost' REQUIRE SSL;
CREATE USER 'api_status'@'localhost' REQUIRE SSL;
-- ✅ Только они требуют SSL!

GRANT ... TO 'api_register'@'localhost';
GRANT ... TO 'api_status'@'localhost';
FLUSH PRIVILEGES;
```

### Результат:

```
Одновременная работа:
  ✅ root, tzuser, gameuser → с паролями (как раньше)
  ✅ api_register, api_status → с SSL (БЕЗ паролей)
  
Никто не пострадал! ✅
```

---

## 🎉 ИТОГИ

### Вопрос: Как сделать чтоб требовало SSL только для новых пользователей?

**Ответ:**

1. ✅ **НЕ включать** `require_secure_transport=ON` в my.cnf
2. ✅ **Включить SSL** (ssl-ca, ssl-cert) - делает SSL доступным
3. ✅ **Требовать SSL** только для новых пользователей через `REQUIRE SUBJECT`
4. ✅ Старые пользователи **продолжают работать с паролями**

### Проверка:

```sql
SELECT user, host, ssl_type FROM mysql.user;

-- Покажет:
-- Старые: ssl_type = NULL (пароли работают)
-- Новые: ssl_type = SPECIFIED (требуют SSL)
```

**Все сосуществуют без проблем!** 🎉

---

**Дата:** 2025-10-01  
**Статус:** Проверено, работает
