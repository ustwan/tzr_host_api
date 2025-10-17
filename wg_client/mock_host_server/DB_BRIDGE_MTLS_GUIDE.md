# DB Bridge mTLS Configuration Guide

## Архитектура

```
API Service → db_bridge (nginx:3307, mTLS) → MySQL (localhost:3306)
```

## Сертификаты и пользователи

| Роль | CN | Сертификаты | БД-пользователь | Права |
|------|-----|-------------|-----------------|-------|
| Регистрация | api_register | client_register/client.{crt,key} | api_register | INSERT users, user_sessions; SELECT constants, servers |
| Чтение | api_readonly | client_readonly/client.{crt,key} | api_readonly | SELECT на все таблицы gamedb |
| Администратор | api_admin | client_admin/client.{crt,key} | api_admin | ALL на gamedb, api4_battles |

## Использование в API

### api_father (регистрация)

```python
import pymysql
import ssl

# Подключение с client_register сертификатом
ssl_ctx = ssl.create_default_context(cafile="/certs/ca/ca.crt")
ssl_ctx.load_cert_chain(
    certfile="/certs/client_register/client.crt",
    keyfile="/certs/client_register/client.key"
)

conn = pymysql.connect(
    host="db_bridge",  # или mock_db_bridge в локале
    port=3307,
    user="api_register",
    password="register_pass_change_me",
    database="gamedb",
    ssl=ssl_ctx
)
```

### api_1, api_2 (чтение)

```python
# Подключение с client_readonly сертификатом
ssl_ctx = ssl.create_default_context(cafile="/certs/ca/ca.crt")
ssl_ctx.load_cert_chain(
    certfile="/certs/client_readonly/client.crt",
    keyfile="/certs/client_readonly/client.key"
)

conn = pymysql.connect(
    host="db_bridge",
    port=3307,
    user="api_readonly",
    password="readonly_pass_change_me",
    database="gamedb",
    ssl=ssl_ctx
)
```

### api_4, api_mother (администратор)

```python
# Подключение с client_admin сертификатом
ssl_ctx = ssl.create_default_context(cafile="/certs/ca/ca.crt")
ssl_ctx.load_cert_chain(
    certfile="/certs/client_admin/client.crt",
    keyfile="/certs/client_admin/client.key"
)

conn = pymysql.connect(
    host="db_bridge",
    port=3307,
    user="api_admin",
    password="admin_pass_change_me",
    database="gamedb",  # или api4_battles
    ssl=ssl_ctx
)
```

## Переменные окружения

```bash
# Для локальной разработки
DB_BRIDGE_HOST=mock_db_bridge
DB_BRIDGE_PORT=3307

# Для продакшн
DB_BRIDGE_HOST=10.8.0.20  # HOST_SERVER IP в VPN
DB_BRIDGE_PORT=3307

# Пути к сертификатам
DB_CA_CERT=/certs/ca/ca.crt
DB_CLIENT_CERT=/certs/client_register/client.crt  # или другой клиент
DB_CLIENT_KEY=/certs/client_register/client.key

# Credentials
DB_USER=api_register  # или другой пользователь
DB_PASSWORD=register_pass_change_me
DB_NAME=gamedb
```

## Проверка подключения

```bash
# Тест с mysql client
mysql \
  --host=localhost \
  --port=3307 \
  --user=api_register \
  --password=register_pass_change_me \
  --ssl-ca=/path/to/ca/ca.crt \
  --ssl-cert=/path/to/client_register/client.crt \
  --ssl-key=/path/to/client_register/client.key \
  gamedb
```

## Безопасность

1. **Разделение прав**: Каждый API использует только те права, которые ему нужны
2. **mTLS**: Обязательная взаимная аутентификация
3. **Разные пароли**: Каждый пользователь имеет свой уникальный пароль
4. **CA verification**: Все стороны проверяют сертификаты через общий CA

## Мониторинг

- Логировать все подключения по CN сертификата
- Алерты на неудачные попытки подключения
- Метрики по пользователям и типам запросов










