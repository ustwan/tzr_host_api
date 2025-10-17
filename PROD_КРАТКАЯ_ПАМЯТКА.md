# 🚀 PROD режим - Краткая памятка

## ✅ Вы правильно вспомнили!

**МЫ НЕ ХРАНИМ ПАРОЛИ ОТ PROD СЕРВЕРА!**

Используем **mTLS сертификаты** вместо паролей.

---

## 🏗️ Как это работает

```
HOST_API (10.8.0.2)                 HOST_SERVER (10.8.0.20)
├─ api_father                       ├─ db_bridge :3307
│  SSL cert: api_register.crt  ────→│  (простой TCP proxy)
│  CN=api_register                  │     ↓
│  БЕЗ ПАРОЛЯ!                      ├─ MySQL :3306
│                                   │  Проверяет CN=api_register
│                                   │  Подключает БЕЗ ПАРОЛЯ!
│                                   │
├─ Site Agent                       ├─ game_bridge :5191
│  WebSocket к сайту           ────→│  (TCP proxy)
│                                   │     ↓
│                                   └─ Game Server :5190
```

---

## 🔑 Что нужно для PROD

### На HOST_API (WG_CLIENT):

**1. Сертификаты в `/etc/certs/`:**
```
ca.crt              # CA сертификат
api_register.crt    # CN=api_register (для регистрации)
api_register.key    # Приватный ключ (chmod 600!)
api_status.crt      # CN=api_status (для статуса)
api_status.key      # Приватный ключ (chmod 600!)
```

**2. Конфиг `.env`:**
```bash
DB_MODE=prod
DB_PROD_HOST=10.8.0.20
DB_PROD_PORT=3307
DB_PROD_USER=api_register  # Имя = CN!
DB_PROD_PASSWORD=           # ПУСТО!
DB_PROD_SSL_CA=/certs/ca.crt
DB_PROD_SSL_CERT=/certs/api_register.crt
DB_PROD_SSL_KEY=/certs/api_register.key

GAME_SERVER_MODE=prod
GAME_SERVER_PROD_HOST=10.8.0.20
GAME_SERVER_PROD_PORT=5191
```

**3. Запуск:**
```bash
cd wg_client
bash tools/ctl.sh start-prod
```

### На HOST_SERVER:

**Что развернуто (один раз настроили):**
```
/opt/host_server/
├── mysql (с SSL)
├── db_bridge (Nginx proxy :3307)
└── game_bridge (Nginx proxy :5191)
```

**Пользователи MySQL БЕЗ паролей:**
```sql
CREATE USER 'api_register'@'%'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API';
-- БЕЗ ПАРОЛЯ!

GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_register'@'%';
```

---

## ⚡ Быстрый запуск PROD

```bash
# На вашем сервере
cd /mnt/docker/tzr_host_api/wg_client

# Проверить сертификаты
ls -la /etc/certs/

# Проверить .env
grep DB_MODE .env  # Должно быть: DB_MODE=prod

# Запустить
sudo bash tools/ctl.sh start-prod

# Проверить
sudo bash tools/ctl.sh status
sudo docker logs api_father | grep "10.8.0.20"
```

---

## 🎯 Главное

**НИКАКИХ ПАРОЛЕЙ!**
- ✅ Только mTLS сертификаты
- ✅ CN в сертификате = имя пользователя БД
- ✅ MySQL проверяет и разрешает БЕЗ пароля
- ✅ db_bridge НЕ знает паролей
- ✅ api_father НЕ знает паролей

**Безопасность через сертификаты, а не пароли!** 🔐

