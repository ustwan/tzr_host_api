# 🔄 Режимы работы: PROD vs TEST

## 📋 Обзор режимов

У проекта есть **3 способа** управления режимами:

1. **Через скрипт ctl.sh** (рекомендуется) ✅
2. **Через .env файл** (ручное редактирование)
3. **Через env.test / env.prod** (предустановленные конфиги)

---

## 🎮 Способ 1: Через ctl.sh (РЕКОМЕНДУЕТСЯ)

### Тестовый режим

```bash
cd wg_client
bash tools/ctl.sh start-test
```

**Что происходит:**
- ✅ Автоматически загружает `env.test` (если есть)
- ✅ Устанавливает `DB_MODE=test`
- ✅ Ограниченные ресурсы: `BATCH_SIZE=10`, `MAX_WORKERS=2`
- ✅ Запускает **тестовую БД в Docker** (MySQL в контейнере)
- ✅ Запускает все API сервисы
- ✅ Подходит для разработки и тестирования

### Продакшн режим

```bash
cd wg_client
bash tools/ctl.sh start-prod
```

**Что происходит:**
- ✅ Автоматически загружает `env.prod` (если есть)
- ✅ Устанавливает `DB_MODE=prod`
- ✅ Полные ресурсы: `BATCH_SIZE=100`, `MAX_WORKERS=8`
- ✅ Подключается к **реальной БД на LAN** (10.0.0.50 или другой IP)
- ✅ Запускает все API сервисы
- ✅ Подходит для production серверов

### По умолчанию

```bash
cd wg_client
bash tools/ctl.sh start-all
```

**Что происходит:**
- ✅ Средний режим: `DB_MODE=test`, `BATCH_SIZE=50`, `MAX_WORKERS=4`
- ✅ Универсальный для большинства случаев

---

## ⚙️ Способ 2: Через .env файл (ручное)

### Структура .env

```bash
cd wg_client
nano .env
```

**Ключевая переменная:**
```bash
# Переключатель режима БД
DB_MODE=test    # или prod
```

### Тестовый режим (.env)

```bash
# ========== РЕЖИМ: TEST ==========
DB_MODE=test

# Тестовая БД (Docker контейнер)
DB_TEST_HOST=db
DB_TEST_PORT=3306
DB_TEST_NAME=tzserver
DB_TEST_USER=tzuser
DB_TEST_PASSWORD=tzpass

# Ресурсы (ограниченные)
BATCH_SIZE=10
MAX_WORKERS=2

# Game Server (mock)
GAME_SERVER_MODE=test
GAME_SERVER_TEST_HOST=game_server_mock
```

**Запуск:**
```bash
bash tools/ctl.sh start-all  # Прочитает DB_MODE=test из .env
```

### Продакшн режим (.env)

```bash
# ========== РЕЖИМ: PROD ==========
DB_MODE=prod

# Продакшн БД (на другом сервере в LAN)
DB_PROD_HOST=10.0.0.50      # IP вашего MySQL сервера
DB_PROD_PORT=3306
DB_PROD_NAME=tzserver
DB_PROD_USER=prod_user
DB_PROD_PASSWORD=ваш_безопасный_пароль

# Ресурсы (полные)
BATCH_SIZE=100
MAX_WORKERS=8

# Game Server (реальный)
GAME_SERVER_MODE=prod
GAME_SERVER_PROD_HOST=10.8.0.20   # Реальный игровой сервер
```

**Запуск:**
```bash
bash tools/ctl.sh start-all  # Прочитает DB_MODE=prod из .env
```

---

## 📁 Способ 3: Через env.test / env.prod

### Предустановленные файлы

У вас есть 2 готовых конфига:
- `wg_client/env.test` - настройки для теста
- `wg_client/env.prod` - настройки для прода

### Использование

```bash
cd wg_client

# Для тестового режима
cp env.test .env
bash tools/ctl.sh start-all

# ИЛИ сразу
bash tools/ctl.sh start-test  # Автоматически загрузит env.test

# Для продакшн режима
cp env.prod .env
bash tools/ctl.sh start-all

# ИЛИ сразу
bash tools/ctl.sh start-prod  # Автоматически загрузит env.prod
```

---

## 🔍 Различия между режимами

| Параметр | TEST | PROD | Зачем |
|----------|------|------|-------|
| **База данных** | Docker контейнер | Внешний сервер (LAN) | Изоляция данных |
| **DB_HOST** | `db` (контейнер) | `10.0.0.50` (IP) | Разные источники |
| **BATCH_SIZE** | 10 | 100 | Меньше нагрузки в тесте |
| **MAX_WORKERS** | 2 | 8 | Меньше параллелизма в тесте |
| **RETRY_ATTEMPTS** | 3 | 5 | Меньше попыток в тесте |
| **RETRY_DELAY** | 1.0s | 2.0s | Быстрее повтор в тесте |
| **Game Server** | Mock (эмулятор) | Реальный сервер | Безопасность |
| **LOGS_BASE** | `/Users/.../srv/btl_mirror` | `/srv/btl_mirror` | Локальные vs production пути |
| **ADMIN_TOKEN** | `test_admin_token` | `prod_admin_token_secure` | Разные токены |

---

## 🎯 Как работает DB_MODE

### API_Father (оркестратор)

**Файл:** `wg_client/api_father/app/infrastructure/db.py`

```python
def get_dsn_and_db():
    mode = os.getenv("DB_MODE", "test").lower()
    
    if mode == "prod":
        # Продакшн БД
        return {
            "host": os.getenv("DB_PROD_HOST"),
            "port": int(os.getenv("DB_PROD_PORT", 3306)),
            "database": os.getenv("DB_PROD_NAME"),
            "user": os.getenv("DB_PROD_USER"),
            "password": os.getenv("DB_PROD_PASSWORD")
        }
    else:
        # Тестовая БД
        return {
            "host": os.getenv("DB_TEST_HOST", "db"),
            "port": int(os.getenv("DB_TEST_PORT", 3306)),
            "database": os.getenv("DB_TEST_NAME"),
            "user": os.getenv("DB_TEST_USER"),
            "password": os.getenv("DB_TEST_PASSWORD")
        }
```

**Логика:**
- Читает `DB_MODE` из ENV
- Выбирает нужные креды (`DB_TEST_*` или `DB_PROD_*`)
- Подключается к соответствующей БД

### API_4 (битвы и аналитика)

Аналогично использует `DB_MODE` для выбора PostgreSQL:
- **TEST**: `api_4_db` (контейнер)
- **PROD**: `localhost:5432` (внешняя БД)

---

## 🚀 Практические сценарии

### Сценарий 1: Локальная разработка

```bash
cd wg_client

# Используем тестовый режим
bash tools/ctl.sh start-test

# Что запустится:
# ✅ MySQL в Docker (тестовая БД)
# ✅ PostgreSQL в Docker (API_4)
# ✅ Game Server Mock (эмулятор)
# ✅ Все API сервисы
# ✅ Ограниченные ресурсы (2 воркера)
```

**Когда использовать:**
- Разработка на локальной машине
- Тестирование новых функций
- Отладка без риска для продакшн данных

### Сценарий 2: Production сервер

```bash
cd wg_client

# 1. Настроить .env
nano .env
# Изменить:
# DB_MODE=prod
# DB_PROD_HOST=10.0.0.50  # Ваш MySQL сервер
# DB_PROD_PASSWORD=безопасный_пароль

# 2. Запустить
bash tools/ctl.sh start-prod

# Что запустится:
# ✅ Подключение к внешней MySQL (10.0.0.50)
# ✅ Подключение к внешней PostgreSQL
# ✅ Реальный Game Server (10.8.0.20)
# ✅ Все API сервисы
# ✅ Полные ресурсы (8 воркеров)
```

**Когда использовать:**
- Production сервер
- Реальные пользователи
- Максимальная производительность

### Сценарий 3: Переключение между режимами

```bash
cd wg_client

# Сейчас в тесте - хочу в прод
bash tools/ctl.sh stop-all       # Остановить всё

nano .env
# Изменить DB_MODE=test → DB_MODE=prod

bash tools/ctl.sh start-prod     # Запустить в проде

# Проверить режим
bash tools/ctl.sh status
docker logs api_father | grep "DB_MODE"
```

---

## 🔐 Site Agent - режимы

**Site Agent работает ОДИНАКОВО** в обоих режимах, но:

### Тестовый режим (Site Agent)

```bash
cd wg_client/site_agent
nano .env

# Тестовые значения
SITE_WS_URL=ws://localhost:8000/ws/pull  # HTTP для теста
AUTH_JWT=test_jwt_token
HMAC_SECRET=test_hmac_secret
AES_GCM_KEY=test_aes_key_base64

# Локальные API (те же)
LOCAL_REGISTER_URL=http://api_2:8082/register
LOCAL_STATUS_URL=http://api_father:9000/internal/constants
```

### Продакшн режим (Site Agent)

```bash
cd wg_client/site_agent
nano .env

# Production значения
SITE_WS_URL=wss://site.example.com/ws/pull  # WSS для прода
AUTH_JWT=<реальный JWT от сайта>
HMAC_SECRET=<безопасный 64-char hex>
AES_GCM_KEY=<безопасный base64 ключ>

# Локальные API (те же)
LOCAL_REGISTER_URL=http://api_2:8082/register
LOCAL_STATUS_URL=http://api_father:9000/internal/constants
```

**Запуск Site Agent:**
```bash
# В любом режиме
bash tools/ctl.sh site-agent

# ИЛИ вместе со всем
bash tools/ctl.sh start-with-agent
```

---

## 📊 Таблица сервисов по режимам

| Сервис | TEST | PROD | Примечания |
|--------|------|------|------------|
| **MySQL (API_Father)** | Docker контейнер | LAN сервер (10.0.0.50) | Пользователи, telegram |
| **PostgreSQL (API_4)** | Docker контейнер | LAN сервер | Битвы, аналитика |
| **Redis** | Docker контейнер | Docker контейнер | Очереди (одинаково) |
| **Game Server** | Mock (эмулятор) | Реальный (10.8.0.20) | Регистрация персонажей |
| **Site Agent** | WS://localhost | WSS://site.com | Связь с сайтом |
| **API сервисы** | Одинаково | Одинаково | Код не меняется |
| **Workers** | 2 воркера | 8 воркеров | Параллелизм |
| **Batch Size** | 10 | 100 | Размер пакетов |

---

## 🛠️ Команды для каждого режима

### TEST режим

```bash
cd wg_client

# Полный запуск
bash tools/ctl.sh start-test

# Что включено:
# ✅ MySQL тестовая (контейнер db)
# ✅ PostgreSQL тестовая (контейнер api_4_db)
# ✅ Redis (контейнер)
# ✅ Game Server Mock
# ✅ API_Father + API_1-5
# ✅ Workers (2 штуки)
# ✅ XML Workers (для загрузки логов)
# ✅ Monitoring

# Статус
bash tools/ctl.sh status

# Логи
bash tools/ctl.sh logs api_father
```

### PROD режим

```bash
cd wg_client

# 1. НАСТРОИТЬ .env с продакшн креденшалами
nano .env
# DB_MODE=prod
# DB_PROD_HOST=10.0.0.50
# DB_PROD_PASSWORD=безопасный_пароль

# 2. Полный запуск
bash tools/ctl.sh start-prod

# Что включено:
# ✅ Подключение к внешней MySQL
# ✅ Подключение к внешней PostgreSQL
# ✅ Redis (контейнер)
# ✅ Реальный Game Server (10.8.0.20)
# ✅ API_Father + API_1-5
# ✅ Workers (8 штук)
# ✅ XML Workers
# ✅ Monitoring

# Статус
bash tools/ctl.sh status

# Логи
bash tools/ctl.sh logs
```

### С Site Agent

```bash
# Тест с агентом
bash tools/ctl.sh start-with-agent

# ИЛИ добавить агента к уже запущенным сервисам
bash tools/ctl.sh site-agent

# Логи агента
bash tools/ctl.sh site-agent-logs

# Перезапуск агента
bash tools/ctl.sh site-agent-restart
```

---

## 🔧 Переключение режимов

### Вариант A: Через скрипт

```bash
# Сейчас в тесте, нужен прод

# 1. Остановить все
bash tools/ctl.sh stop-all

# 2. Запустить в проде
bash tools/ctl.sh start-prod
```

### Вариант B: Через .env

```bash
# 1. Остановить все
bash tools/ctl.sh stop-all

# 2. Изменить .env
nano .env
# DB_MODE=test → DB_MODE=prod

# 3. Запустить
bash tools/ctl.sh start-all
```

### Вариант C: Копирование конфига

```bash
# 1. Остановить все
bash tools/ctl.sh stop-all

# 2. Скопировать нужный конфиг
cp env.prod .env
# ИЛИ
cp env.test .env

# 3. Запустить
bash tools/ctl.sh start-all
```

---

## ⚠️ Важные моменты

### 1. Миграции БД

**TEST режим:**
```bash
# Автоматические миграции при старте (если MIGRATE_ON_START_TEST=1)
bash tools/ctl.sh start-test

# ИЛИ вручную
bash tools/ctl.sh migrate
```

**PROD режим:**
```bash
# ТОЛЬКО вручную! (безопасность)
bash tools/ctl.sh migrate-prod

# Предварительно проверьте SQL скрипты!
cat wg_client/db/migrations/*.sql
```

### 2. Данные

**TEST:**
- ✅ Можно удалять: `bash tools/ctl.sh down-all` (удалит volumes)
- ✅ Создаются заново при каждом запуске

**PROD:**
- ❌ НЕ удалять volumes без бэкапа!
- ✅ Делать регулярные бэкапы БД
- ✅ Использовать `stop-all` вместо `down-all`

### 3. Секреты

**TEST:**
```bash
# Простые секреты (для удобства)
DB_TEST_PASSWORD=tzpass
ADMIN_API_TOKEN=test_admin_token
```

**PROD:**
```bash
# Безопасные секреты (генерируйте!)
DB_PROD_PASSWORD=$(openssl rand -base64 32)
ADMIN_API_TOKEN=$(openssl rand -base64 32)
```

### 4. Site Agent секреты

**TEST:**
```bash
# wg_client/site_agent/.env
HMAC_SECRET=test_hmac_12345
AES_GCM_KEY=dGVzdF9hZXNfMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=
```

**PROD:**
```bash
# wg_client/site_agent/.env
HMAC_SECRET=$(openssl rand -hex 32)
AES_GCM_KEY=$(openssl rand -base64 32)

# И такие же на сайте (Django)!
```

---

## 🧪 Проверка режима

```bash
# После запуска проверить какой режим активен

# Вариант 1: Через логи
docker logs api_father | grep -i "db_mode"

# Вариант 2: Через переменные
docker exec api_father env | grep DB_MODE

# Вариант 3: Через БД
docker exec api_father env | grep DB_TEST_HOST
docker exec api_father env | grep DB_PROD_HOST

# Вариант 4: Проверить подключение к БД
docker logs api_father | grep -i "connected"
```

---

## 📋 Чеклист для переключения

### Переход TEST → PROD

- [ ] Остановить все сервисы: `bash tools/ctl.sh stop-all`
- [ ] Создать бэкап тестовой БД (опционально)
- [ ] Изменить `.env`: `DB_MODE=prod`
- [ ] Настроить `DB_PROD_HOST`, `DB_PROD_PASSWORD`
- [ ] Настроить `GAME_SERVER_PROD_HOST`
- [ ] Обновить секреты (ADMIN_API_TOKEN)
- [ ] Настроить `site_agent/.env` с prod секретами
- [ ] Запустить: `bash tools/ctl.sh start-prod`
- [ ] Проверить подключение к БД
- [ ] Проверить логи: `bash tools/ctl.sh logs`

### Переход PROD → TEST

- [ ] Остановить все сервисы: `bash tools/ctl.sh stop-all`
- [ ] Изменить `.env`: `DB_MODE=test`
- [ ] Запустить: `bash tools/ctl.sh start-test`
- [ ] Проверить тестовая БД создалась
- [ ] Проверить логи

---

## 🎯 Рекомендации

### Для разработки (локально)

```bash
# Всегда используйте TEST режим
bash tools/ctl.sh start-test

# Быстрая очистка и перезапуск
bash tools/ctl.sh down-all   # Удалит тестовые данные
bash tools/ctl.sh start-test # Создаст заново
```

### Для staging/pre-production

```bash
# Используйте TEST режим с реальными данными
DB_MODE=test
# Но скопируйте dump с прода
docker exec db mysql ... < prod_dump.sql
```

### Для production

```bash
# ВСЕГДА PROD режим
bash tools/ctl.sh start-prod

# Никогда не используйте down-all (удалит данные!)
# Только stop-all для остановки
```

---

## 🔄 Быстрая шпаргалка

```bash
# TEST режим
bash tools/ctl.sh start-test     # Запуск
bash tools/ctl.sh down-all       # Очистка (безопасно)

# PROD режим
bash tools/ctl.sh start-prod     # Запуск
bash tools/ctl.sh stop-all       # Остановка (НЕ удаляет данные!)

# С Site Agent
bash tools/ctl.sh start-with-agent    # Всё + агент
bash tools/ctl.sh site-agent          # Только агент
bash tools/ctl.sh site-agent-logs     # Логи агента

# Проверка
bash tools/ctl.sh status         # Статус всех
bash tools/ctl.sh doctor         # Диагностика
```

---

**Сохранил в:** `РЕЖИМЫ_PROD_TEST.md` для справки! 📖

