# 🔍 Анализ необходимых пользователей БД

## 📊 АНАЛИЗ API И ИХ ОПЕРАЦИЙ С БД

### API 1 (server_status) - Получение бонусов и статуса сервера

**Эндпоинт:** `GET /server/status`

**Операции с БД:**
```python
# api_father/app/main.py:93
SELECT Name, Value, Description FROM constants ORDER BY Value ASC
```

**Необходимые права:**
- ✅ SELECT на `tzserver.constants`
- ❌ INSERT, UPDATE, DELETE - НЕ нужны

**Рекомендуемый пользователь:** `api_user_status`

---

### API 2 (register) - Регистрация игроков

**Эндпоинт:** `POST /register`

**Операции с БД:**
```python
# Проверка лимита
SELECT COUNT(*) AS c FROM tgplayers WHERE telegram_id=%s

# Проверка логина
SELECT 1 FROM tgplayers WHERE login=%s

# Создание игрока
INSERT INTO tgplayers (telegram_id, username, login) 
VALUES (%s, %s, %s)
ON DUPLICATE KEY UPDATE 
    username = VALUES(username),
    login = VALUES(login)
```

**Необходимые права:**
- ✅ SELECT на `tzserver.tgplayers`
- ✅ INSERT на `tzserver.tgplayers`
- ✅ SELECT на `tzserver.constants` (для проверок)
- ❌ UPDATE, DELETE - НЕ нужны

**Рекомендуемый пользователь:** `api_user_register`

---

### API 3 (info) - Информация о сервере

**Эндпоинт:** `GET /info/internal/health`

**Операции с БД:**
```python
# Предположительно (нужно проверить):
SELECT ... FROM constants
SELECT ... FROM tgplayers (возможно, статистика)
```

**Необходимые права:**
- ✅ SELECT на `tzserver.constants`
- ✅ SELECT на `tzserver.tgplayers` (возможно)
- ❌ INSERT, UPDATE, DELETE - НЕ нужны

**Рекомендуемый пользователь:** `api_user_status` (тот же что API 1)

---

### API 4 (battle_logs) - Аналитика логов

**Эндпоинт:** `GET /battle/analytics/*`

**Операции с БД:**
```python
# Аналитика - чтение всех таблиц
SELECT * FROM tgplayers
SELECT * FROM battles (если есть)
SELECT * FROM любые_таблицы_для_аналитики
```

**Необходимые права:**
- ✅ SELECT на `tzserver.*` (все таблицы)
- ❌ INSERT, UPDATE, DELETE - НЕ нужны

**Рекомендуемый пользователь:** `api_user_analytics`

---

## ✅ ИТОГОВАЯ ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ

| # | Пользователь БД | Сертификат (CN) | API | Права | Таблицы |
|---|----------------|----------------|-----|-------|---------|
| 1 | `api_user_register` | `api_register.crt` (CN=api_register) | API 2 | SELECT, INSERT | tgplayers, constants (SELECT) |
| 2 | `api_user_status` | `api_status.crt` (CN=api_status) | API 1, API 3 | SELECT | constants, tgplayers |
| 3 | `api_user_analytics` | `api_analytics.crt` (CN=api_analytics) | API 4 | SELECT | tzserver.* (все) |

---

## 📋 SQL КОМАНДЫ ДЛЯ СОЗДАНИЯ ПОЛЬЗОВАТЕЛЕЙ

### 1. api_user_register (API 2 - регистрация)
```sql
-- Создание пользователя
CREATE USER 'api_user_register'@'localhost' 
IDENTIFIED BY 'secret_register_2025';

-- Права на регистрацию
GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_user_register'@'localhost';

-- Чтение констант для проверок
GRANT SELECT ON tzserver.constants TO 'api_user_register'@'localhost';

-- Применить
FLUSH PRIVILEGES;
```

**Проверка прав:**
```sql
SHOW GRANTS FOR 'api_user_register'@'localhost';

-- Ожидаемый результат:
-- GRANT USAGE ON *.* TO `api_user_register`@`localhost`
-- GRANT SELECT, INSERT ON `tzserver`.`tgplayers` TO `api_user_register`@`localhost`
-- GRANT SELECT ON `tzserver`.`constants` TO `api_user_register`@`localhost`
```

---

### 2. api_user_status (API 1, API 3 - чтение статуса)
```sql
-- Создание пользователя
CREATE USER 'api_user_status'@'localhost' 
IDENTIFIED BY 'secret_status_2025';

-- Права на чтение констант
GRANT SELECT ON tzserver.constants TO 'api_user_status'@'localhost';

-- Права на чтение игроков (для статистики, бонусов)
GRANT SELECT ON tzserver.tgplayers TO 'api_user_status'@'localhost';

-- Применить
FLUSH PRIVILEGES;
```

**Проверка прав:**
```sql
SHOW GRANTS FOR 'api_user_status'@'localhost';

-- Ожидаемый результат:
-- GRANT USAGE ON *.* TO `api_user_status`@`localhost`
-- GRANT SELECT ON `tzserver`.`constants` TO `api_user_status`@`localhost`
-- GRANT SELECT ON `tzserver`.`tgplayers` TO `api_user_status`@`localhost`
```

---

### 3. api_user_analytics (API 4 - аналитика)
```sql
-- Создание пользователя
CREATE USER 'api_user_analytics'@'localhost' 
IDENTIFIED BY 'secret_analytics_2025';

-- Права на чтение ВСЕХ таблиц для аналитики
GRANT SELECT ON tzserver.* TO 'api_user_analytics'@'localhost';

-- Применить
FLUSH PRIVILEGES;
```

**Проверка прав:**
```sql
SHOW GRANTS FOR 'api_user_analytics'@'localhost';

-- Ожидаемый результат:
-- GRANT USAGE ON *.* TO `api_user_analytics`@`localhost`
-- GRANT SELECT ON `tzserver`.* TO `api_user_analytics`@`localhost`
```

---

## 🔐 МАППИНГ В db_bridge

### Python конфигурация:
```python
# db_bridge/config.py

CERT_TO_MYSQL_USER = {
    "api_register": {
        "mysql_user": "api_user_register",
        "mysql_password": "secret_register_2025",
        "description": "API 2 - регистрация игроков",
        "allowed_operations": ["SELECT", "INSERT"],
        "tables": ["tgplayers", "constants"],
    },
    "api_status": {
        "mysql_user": "api_user_status",
        "mysql_password": "secret_status_2025",
        "description": "API 1, API 3 - получение статуса и бонусов",
        "allowed_operations": ["SELECT"],
        "tables": ["constants", "tgplayers"],
    },
    "api_analytics": {
        "mysql_user": "api_user_analytics",
        "mysql_password": "secret_analytics_2025",
        "description": "API 4 - аналитика боев",
        "allowed_operations": ["SELECT"],
        "tables": ["*"],  # все таблицы
    },
}
```

---

## 🎯 ОТВЕТ НА ВАШИ ВОПРОСЫ

### Вопрос: Нужны ли еще пользователи?

**ОТВЕТ: НЕТ, достаточно 3 пользователей!**

✅ **api_user_register** - для API 2 (регистрация)
✅ **api_user_status** - для API 1, API 3 (чтение статуса/бонусов)
✅ **api_user_analytics** - для API 4 (аналитика)

### Почему API 1 и API 3 используют одного пользователя?

**Логика:**
- Оба API выполняют ТОЛЬКО SELECT
- Оба читают одни и те же таблицы (constants, tgplayers)
- Одинаковые права
- Нет смысла дублировать пользователей

**Можно разделить** если:
- API 3 требует доступ к дополнительным таблицам
- Нужно раздельное логирование/аудит
- Политика безопасности требует

---

## 📝 РЕКОМЕНДАЦИИ

### Минимальный набор (РЕКОМЕНДУЕТСЯ): 3 пользователя
```
1. api_user_register  - API 2 (SELECT, INSERT)
2. api_user_status    - API 1, API 3 (SELECT)
3. api_user_analytics - API 4 (SELECT на все)
```

### Расширенный набор (опционально): 4 пользователя
```
1. api_user_register  - API 2 (SELECT, INSERT)
2. api_user_status    - API 1 (SELECT на constants)
3. api_user_info      - API 3 (SELECT на constants, tgplayers)
4. api_user_analytics - API 4 (SELECT на все)
```

### Для вашего случая:

✅ **Используйте 2 пользователя** (как вы предложили):

```
1. api_user_register (api_register.crt)
   - API 2
   - SELECT, INSERT на tgplayers
   - SELECT на constants

2. api_user_status (api_status.crt)
   - API 1, API 3
   - SELECT на constants, tgplayers
```

**api_user_analytics НЕ нужен** если API 4 не обращается к MySQL!

---

## 🔍 ПРОВЕРКА API 4

**API 4 использует:**
- ❌ НЕТ прямого доступа к MySQL tzserver
- ✅ PostgreSQL api4_battles (локальная БД на HOST_API)
- ✅ Файлы через api_mother
- ✅ Опционально: api_father для данных игроков

**ВЫВОД:** API 4 может использовать api_user_status если нужен доступ к tgplayers через api_father!

---

## ✅ ФИНАЛЬНАЯ РЕКОМЕНДАЦИЯ

### Достаточно **2 пользователя**:

1. **api_user_register** (для API 2)
   ```sql
   GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_user_register'@'localhost';
   GRANT SELECT ON tzserver.constants TO 'api_user_register'@'localhost';
   ```

2. **api_user_status** (для API 1, API 3, API 4)
   ```sql
   GRANT SELECT ON tzserver.constants TO 'api_user_status'@'localhost';
   GRANT SELECT ON tzserver.tgplayers TO 'api_user_status'@'localhost';
   ```

**Дополнительные пользователи НЕ требуются!**

---

**Обновлено:** 2025-10-01
