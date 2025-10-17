# 🚀 PROD режим - Как это работает (БЕЗ паролей!)

## 🎯 Главное: МЫ НЕ ХРАНИМ ПАРОЛИ!

Вместо паролей используем **mTLS сертификаты** для аутентификации.

---

## 🏗️ Архитектура PROD

```
┌─────────────────────────────────────────────────────────┐
│ HOST_API (WG_CLIENT) - 10.8.0.2                         │
│ Ваш сервер с API сервисами                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ api_father                                              │
│   pymysql.connect(                                      │
│     host="10.8.0.20",    ← HOST_SERVER через VPN        │
│     port=3307,            ← db_bridge порт              │
│     user="api_register", ← Имя = CN в сертификате!     │
│     # БЕЗ ПАРОЛЯ!                                       │
│     ssl={                                               │
│       'ca': '/certs/ca.crt',                            │
│       'cert': '/certs/api_register.crt',  ← CN=...     │
│       'key': '/certs/api_register.key'                  │
│     }                                                   │
│   )                                                     │
│                                                         │
└───────────────────┬─────────────────────────────────────┘
                    │
                    │ mTLS через VPN (10.8.0.0/24)
                    │ Сертификат: CN=api_register
                    ↓
┌─────────────────────────────────────────────────────────┐
│ HOST_SERVER (игровой сервер) - 10.8.0.20               │
│ Удаленный сервер с MySQL и Game Server                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ┌─────────────────────────────────────────┐            │
│ │ db_bridge (Nginx TCP proxy) :3307       │            │
│ │   • НЕ хранит пароли! ✅                │            │
│ │   • Просто проксирует SSL → MySQL       │            │
│ │   • IP whitelist (10.8.0.2)             │            │
│ └─────────────┬───────────────────────────┘            │
│               │                                         │
│               ↓                                         │
│ ┌─────────────────────────────────────────┐            │
│ │ MySQL :3306 (unix socket)               │            │
│ │   • Проверяет SSL сертификат            │            │
│ │   • Извлекает CN = "api_register"       │            │
│ │   • Маппит на user БД = "api_register"  │            │
│ │   • Подключение БЕЗ ПАРОЛЯ! ✅          │            │
│ │                                         │            │
│ │ Пользователи:                           │            │
│ │   CREATE USER 'api_register'@'%'       │            │
│ │   REQUIRE SUBJECT '/CN=api_register';   │            │
│ │   # ↑ БЕЗ ПАРОЛЯ!                       │            │
│ └─────────────────────────────────────────┘            │
│                                                         │
│ ┌─────────────────────────────────────────┐            │
│ │ game_bridge (Nginx TCP proxy) :5191     │            │
│ │   • Проксирует в Game Server :5190      │            │
│ │   • IP whitelist (10.8.0.2)             │            │
│ └─────────────┬───────────────────────────┘            │
│               ↓                                         │
│ ┌─────────────────────────────────────────┐            │
│ │ Game Server :5190                       │            │
│ │   • Регистрация персонажей              │            │
│ │   • Игровой сервер                      │            │
│ └─────────────────────────────────────────┘            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 БЕЗ ПАРОЛЕЙ - Как это работает

### 1. Создание сертификатов (ONE-TIME)

**На HOST_API (WG_CLIENT):**

```bash
# Генерация сертификатов для разных API
cd /etc/certs

# CA (Certificate Authority)
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout ca.key -out ca.crt -days 3650 \
  -subj "/CN=CA/O=HOST_API"

# Сертификат для регистрации (API_2)
openssl req -newkey rsa:2048 -nodes \
  -keyout api_register.key -out api_register.csr \
  -subj "/CN=api_register/O=HOST_API/OU=Registration"

openssl x509 -req -in api_register.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out api_register.crt -days 365

# Сертификат для статуса (API_1)
openssl req -newkey rsa:2048 -nodes \
  -keyout api_status.key -out api_status.csr \
  -subj "/CN=api_status/O=HOST_API/OU=Status"

openssl x509 -req -in api_status.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out api_status.crt -days 365
```

### 2. Пользователи MySQL БЕЗ ПАРОЛЕЙ

**На HOST_SERVER (в MySQL):**

```sql
-- Пользователь для регистрации (API_2)
-- БЕЗ ПАРОЛЯ! Аутентификация через SSL сертификат
CREATE USER 'api_register'@'%'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API/OU=Registration'
  AND ISSUER '/CN=CA/O=HOST_API';

-- Права
GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_register'@'%';
GRANT SELECT ON tzserver.constants TO 'api_register'@'%';
FLUSH PRIVILEGES;

-- Пользователь для статуса (API_1)
-- БЕЗ ПАРОЛЯ!
CREATE USER 'api_status'@'%'
REQUIRE SUBJECT '/CN=api_status/O=HOST_API/OU=Status'
  AND ISSUER '/CN=CA/O=HOST_API';

-- Права (только чтение)
GRANT SELECT ON tzserver.constants TO 'api_status'@'%';
GRANT SELECT ON tzserver.tgplayers TO 'api_status'@'%';
FLUSH PRIVILEGES;
```

### 3. db_bridge (простой proxy БЕЗ паролей)

**На HOST_SERVER:**

```nginx
# /opt/db_bridge/nginx.conf

stream {
    server {
        listen 3307;
        
        # IP whitelist - только HOST_API
        allow 10.8.0.2;  # HOST_API IP в VPN
        deny all;
        
        # Простой TCP proxy в MySQL
        # MySQL сам проверит SSL сертификат
        proxy_pass 127.0.0.1:3306;
        
        proxy_timeout 10s;
        proxy_connect_timeout 3s;
    }
}
```

**Docker Compose на HOST_SERVER:**

```yaml
# /opt/host_server/docker-compose.yml

services:
  db_bridge:
    image: nginx:alpine
    container_name: db_bridge
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "10.8.0.20:3307:3307"  # Слушаем на VPN IP
    network_mode: host
    restart: unless-stopped
  
  mysql:
    image: mysql:8.0
    container_name: mysql
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql/my.cnf:/etc/mysql/my.cnf
      - ./certs:/etc/mysql/certs:ro  # SSL сертификаты
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    network_mode: host
    restart: unless-stopped
    command: --require_secure_transport=ON
```

### 4. Конфигурация MySQL (my.cnf)

```ini
[mysqld]
# SSL сертификаты
ssl-ca=/etc/mysql/certs/ca.crt
ssl-cert=/etc/mysql/certs/server.crt
ssl-key=/etc/mysql/certs/server.key

# Требовать SSL для всех подключений
require_secure_transport=ON

# Разрешить подключения с любого IP (защищено VPN + firewall)
bind-address=0.0.0.0
```

---

## 🔧 Настройка PROD на HOST_API (WG_CLIENT)

### 1. Конфигурация .env

```bash
cd /mnt/docker/tzr_host_api/wg_client

nano .env
```

```bash
# ========== PROD РЕЖИМ ==========
DB_MODE=prod

# ========== БД (БЕЗ ПАРОЛЕЙ!) ==========
# Подключение через mTLS сертификаты
DB_PROD_HOST=10.8.0.20        # HOST_SERVER IP в VPN
DB_PROD_PORT=3307             # db_bridge порт
DB_PROD_NAME=tzserver
DB_PROD_USER=api_register     # Имя = CN в сертификате!
DB_PROD_PASSWORD=              # ← ПУСТО! Не нужен пароль!

# Пути к сертификатам
DB_PROD_SSL_CA=/certs/ca.crt
DB_PROD_SSL_CERT=/certs/api_register.crt
DB_PROD_SSL_KEY=/certs/api_register.key

# ========== GAME SERVER (через bridge) ==========
GAME_SERVER_MODE=prod
GAME_SERVER_PROD_HOST=10.8.0.20    # HOST_SERVER IP
GAME_SERVER_PROD_PORT=5191          # game_bridge порт

# ========== РЕСУРСЫ ==========
BATCH_SIZE=100
MAX_WORKERS=8
```

### 2. Монтирование сертификатов

**Вариант A: Docker volumes**

```yaml
# HOST_API_SERVICE_FATHER_API.yml
services:
  api_father:
    volumes:
      - /etc/certs:/certs:ro  # Монтируем сертификаты
    environment:
      - DB_PROD_SSL_CA=/certs/ca.crt
      - DB_PROD_SSL_CERT=/certs/api_register.crt
      - DB_PROD_SSL_KEY=/certs/api_register.key
```

**Вариант B: Копирование в образ**

```dockerfile
# api_father/Dockerfile
COPY certs /certs
RUN chmod 600 /certs/*.key
```

### 3. Код подключения (уже реализовано!)

```python
# wg_client/api_father/app/infrastructure/db.py

def get_dsn_and_db():
    mode = os.getenv("DB_MODE", "test")
    
    if mode == "prod":
        ssl_config = None
        
        # Если указаны пути к сертификатам
        ca = os.getenv("DB_PROD_SSL_CA")
        cert = os.getenv("DB_PROD_SSL_CERT")
        key = os.getenv("DB_PROD_SSL_KEY")
        
        if ca and cert and key:
            ssl_config = {
                'ca': ca,
                'cert': cert,
                'key': key
            }
        
        return {
            'host': os.getenv("DB_PROD_HOST"),
            'port': int(os.getenv("DB_PROD_PORT", 3306)),
            'database': os.getenv("DB_PROD_NAME"),
            'user': os.getenv("DB_PROD_USER"),
            # password НЕ передается если есть ssl_config!
            'ssl': ssl_config
        }
```

---

## 📋 Что НА КАКОМ СЕРВЕРЕ

### HOST_SERVER (10.8.0.20) - Игровой сервер

**Что развернуто:**
```bash
/opt/host_server/
├── docker-compose.yml
│   ├── mysql           # :3306 (unix socket)
│   ├── db_bridge       # :3307 (TCP proxy)
│   ├── game_bridge     # :5191 (TCP proxy)
│   └── game_server     # :5190 (игровой сервер)
├── mysql/
│   ├── my.cnf         # require_secure_transport=ON
│   └── init.sql       # Создание пользователей БЕЗ ПАРОЛЕЙ
├── certs/
│   ├── ca.crt         # CA для проверки
│   ├── server.crt     # MySQL server сертификат
│   └── server.key
└── nginx/
    └── nginx.conf     # db_bridge + game_bridge
```

**Порты открыты только в VPN:**
- `10.8.0.20:3307` - db_bridge (MySQL proxy)
- `10.8.0.20:5191` - game_bridge (Game Server proxy)

### HOST_API (10.8.0.2) - Ваш API сервер

**Что развернуто:**
```bash
/mnt/docker/tzr_host_api/wg_client/
├── .env                    # DB_MODE=prod
├── tools/ctl.sh           # Скрипт управления
├── certs/                 # mTLS сертификаты
│   ├── ca.crt            # CA для проверки
│   ├── api_register.crt  # CN=api_register
│   ├── api_register.key
│   ├── api_status.crt    # CN=api_status
│   └── api_status.key
└── api_father/           # Подключается к 10.8.0.20:3307
```

**Подключение:**
- К БД: `10.8.0.20:3307` (через db_bridge) с mTLS
- К игре: `10.8.0.20:5191` (через game_bridge)

---

## 🔑 Сертификаты - Вместо паролей

### Принцип работы:

1. **CN (Common Name) в сертификате = имя пользователя БД**
   ```
   api_register.crt имеет CN=api_register
   ↓
   MySQL пользователь = 'api_register'
   ```

2. **MySQL проверяет сертификат и разрешает подключение БЕЗ пароля**
   ```sql
   CREATE USER 'api_register'@'%'
   REQUIRE SUBJECT '/CN=api_register/O=HOST_API';
   -- БЕЗ ПАРОЛЯ!
   ```

3. **Каждый API имеет свой сертификат = свои права**
   ```
   api_register.crt → user 'api_register' → INSERT права
   api_status.crt   → user 'api_status'   → SELECT права
   ```

---

## 🚀 Как запустить PROD

### Шаг 1: На HOST_SERVER (один раз)

```bash
# 1. Развернуть db_bridge + game_bridge + MySQL
cd /opt/host_server
docker compose up -d

# 2. Создать пользователей БД БЕЗ паролей
docker exec -it mysql mysql -u root -p
```

```sql
-- В MySQL консоли
CREATE USER 'api_register'@'%'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API';

GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_register'@'%';
GRANT SELECT ON tzserver.constants TO 'api_register'@'%';
FLUSH PRIVILEGES;

-- Проверка
SHOW GRANTS FOR 'api_register'@'%';
SELECT user, host, ssl_type, x509_subject FROM mysql.user WHERE user='api_register';
```

### Шаг 2: На HOST_API (каждый раз при запуске)

```bash
cd /mnt/docker/tzr_host_api/wg_client

# 1. Проверить что сертификаты на месте
ls -la /etc/certs/
# Должны быть:
# ca.crt, api_register.crt, api_register.key

# 2. Проверить .env
cat .env | grep DB_MODE
# DB_MODE=prod

# 3. Запустить в PROD режиме
bash tools/ctl.sh start-prod

# 4. Проверить подключение к БД
docker logs api_father | grep -i "connected\|ssl\|10.8.0.20"
```

---

## 🔧 Переключение режимов

### TEST → PROD

```bash
cd /mnt/docker/tzr_host_api/wg_client

# 1. Остановить TEST
bash tools/ctl.sh stop-all

# 2. Изменить .env
nano .env
# DB_MODE=test → DB_MODE=prod

# 3. Проверить сертификаты
ls /etc/certs/

# 4. Запустить PROD
bash tools/ctl.sh start-prod

# 5. Проверить логи
docker logs api_father | grep "10.8.0.20"
```

### PROD → TEST

```bash
# 1. Остановить PROD
bash tools/ctl.sh stop-all

# 2. Изменить .env
nano .env
# DB_MODE=prod → DB_MODE=test

# 3. Запустить TEST
bash tools/ctl.sh start-test
```

---

## 🎯 ЧТО ХРАНИТСЯ / НЕ ХРАНИТСЯ

### ❌ НЕ ХРАНИМ (безопасно!):
- Пароли от MySQL ✅
- Пароли от пользователей БД ✅
- Конфиденциальные креды ✅

### ✅ ХРАНИМ (нужно защитить):
- **Приватные ключи** (*.key) → `chmod 600`
- **Сертификаты** (*.crt) → можно `chmod 644`
- **CA сертификат** (ca.crt) → можно `chmod 644`

### Защита ключей:

```bash
# На HOST_API
chmod 600 /etc/certs/*.key
chmod 644 /etc/certs/*.crt
chown root:docker /etc/certs/*

# В Docker монтировать read-only
volumes:
  - /etc/certs:/certs:ro
```

---

## 📊 Таблица режимов

| Параметр | TEST | PROD |
|----------|------|------|
| **БД** | Docker контейнер | HOST_SERVER через mTLS |
| **DB_HOST** | `db` | `10.8.0.20` |
| **DB_PORT** | `3306` | `3307` (db_bridge) |
| **Пароль** | `tzpass` | **НЕТ! mTLS сертификат** |
| **SSL** | Нет | Обязателен |
| **Game Server** | Mock | `10.8.0.20:5191` (game_bridge) |
| **Сертификаты** | Не нужны | `/etc/certs/*.crt, *.key` |

---

## 🎓 Памятка: Как это работает

### Без паролей (mTLS):

```
1. api_father → db_bridge (10.8.0.20:3307)
   Отправляет: SSL сертификат (CN=api_register)
   
2. db_bridge → MySQL (127.0.0.1:3306)
   Проксирует SSL соединение "как есть"
   
3. MySQL проверяет:
   ✅ Сертификат подписан CA?
   ✅ CN = "api_register"?
   ✅ Пользователь 'api_register' требует этот CN?
   
4. MySQL разрешает подключение БЕЗ ПАРОЛЯ!
   Пользователь: 'api_register'
   Права: SELECT, INSERT на tgplayers
```

---

## 🚨 Важные моменты

### 1. Сертификаты должны быть НА МЕСТЕ

```bash
# Проверка на HOST_API
ls -la /etc/certs/
# ca.crt
# api_register.crt
# api_register.key
# api_status.crt
# api_status.key

# Проверка прав
ls -l /etc/certs/*.key
# -rw------- 1 root docker ... api_register.key  ← 600!
```

### 2. VPN должен быть активен

```bash
# Проверка VPN
ping 10.8.0.20  # Должен отвечать

# Проверка db_bridge
telnet 10.8.0.20 3307  # Должен подключаться

# Проверка game_bridge
telnet 10.8.0.20 5191  # Должен подключаться
```

### 3. MySQL на HOST_SERVER настроен с SSL

```bash
# На HOST_SERVER проверка
docker exec mysql mysql -u root -p -e "SHOW VARIABLES LIKE '%ssl%';"

# Должно показать:
# have_ssl = YES
# ssl_ca = /etc/mysql/certs/ca.crt
# ssl_cert = /etc/mysql/certs/server.crt
```

---

## ✅ Итого: PROD без паролей!

**Вы правильно помните!** Мы делали систему БЕЗ хранения паролей:

1. **mTLS сертификаты** вместо паролей ✅
2. **db_bridge** - простой TCP proxy (НЕ хранит пароли) ✅
3. **MySQL пользователи** с `REQUIRE SUBJECT` (БЕЗ паролей) ✅
4. **Разделение прав** через разные сертификаты ✅
5. **Безопасность** - даже если взломают контейнер, нет паролей ✅

**Команда запуска:**
```bash
cd /mnt/docker/tzr_host_api/wg_client
bash tools/ctl.sh start-prod
```

**Файлы документации:**
- `DB_BRIDGE_NO_PASSWORDS_SOLUTION.md` - детали mTLS
- `DB_BRIDGE_MTLS_USERS_EXPLAINED.md` - пользователи БД
- `GAME_BRIDGE_IMPLEMENTATION_SUMMARY.md` - game_bridge

---

**Сохранил в:** `PROD_АРХИТЕКТУРА.md` для справки! 📖

