# 🎯 Полное руководство по регистрации в HOST_API

> **Главный документ проекта** - всегда актуален и содержит полную информацию о регистрации, архитектуре, безопасности и интеграции.

## 📚 Дополнительные документы (детали):
- 🎮 [`GAME_BRIDGE_IMPLEMENTATION_SUMMARY.md`](GAME_BRIDGE_IMPLEMENTATION_SUMMARY.md) - реализация game_bridge
- 🔐 [`DB_BRIDGE_NO_PASSWORDS_SOLUTION.md`](../DB_BRIDGE_NO_PASSWORDS_SOLUTION.md) - БД без паролей
- 📊 [`DB_BRIDGE_LOGGING.md`](../DB_BRIDGE_LOGGING.md) - логирование db_bridge
- 👥 [`DB_USERS_ANALYSIS.md`](../DB_USERS_ANALYSIS.md) - анализ пользователей БД
- 🧪 [`TEST_RESULTS_FINAL.md`](../TEST_RESULTS_FINAL.md) - результаты тестирования

## 📋 Содержание
1. [Архитектура](#архитектура)
2. [Цепочка запрос-ответ](#цепочка-запрос-ответ)
3. [Где находится БД](#где-находится-бд)
4. [Подключение к Game Server через game_bridge](#подключение-к-game-server-через-game_bridge)
5. [Локальная эмуляция vs Продакшн](#локальная-эмуляция-vs-продакшн)
6. [Тестирование](#тестирование)
7. [Резюме](#резюме)
8. [Приложение: Разделение пользователей БД](#приложение-разделение-пользователей-бд-через-mtls)
9. [Ключевые принципы безопасности](#ключевые-принципы-безопасности)

---

## 🌐 Архитектура

### Общая схема (Production)

```
┌─────────────────┐
│ САЙТ/Telegram   │  ← Пользователь отправляет данные
│ (HOST_SITE)     │
└────────┬────────┘
         │ HTTP POST /api/register
         │ {"login": "Игрок123", "password": "mypass123", "gender": 1, "telegram_id": 123456789}
         │
         ↓
┌────────────────────────────────────────────────────────────────────────┐
│ HOST_API (этот проект WG_HUB)                                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ Traefik :1010 (Gateway через VPN)                                │ │
│  │ • PathPrefix('/api/register') → api_2:8082                       │ │
│  │ • Middleware: stripPrefix('/api')                                │ │
│  └──────────────────────────┬───────────────────────────────────────┘ │
│                             │                                          │
│                             ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ API 2 :8082 (Registration Endpoint)                              │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │ Роль: Прием и валидация запросов                                 │ │
│  │                                                                  │ │
│  │ Задачи:                                                          │ │
│  │ 1. ✅ Принять JSON от сайта/бота                                 │ │
│  │ 2. ✅ Валидировать данные (Pydantic):                            │ │
│  │    • login: 3-16 символов, русские/английские + цифры + _- пробел│ │
│  │    • password: 6-20 ASCII символов                               │ │
│  │    • gender: 0 (женский) или 1 (мужской)                         │ │
│  │    • telegram_id: обязательное число                             │ │
│  │ 3. ✅ Proxy запрос к api_father (HTTP)                           │ │
│  │                                                                  │ │
│  │ НЕ делает:                                                       │ │
│  │ ❌ Не обращается к БД                                            │ │
│  │ ❌ Не обращается к game_server                                   │ │
│  │ ❌ Не выполняет бизнес-логику                                    │ │
│  └──────────────────────────┬───────────────────────────────────────┘ │
│                             │ HTTP POST /internal/register            │
│                             ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ API Father :9000 (Main Aggregator)                               │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │ Роль: Вся бизнес-логика регистрации                              │ │
│  │                                                                  │ │
│  │ RegisterUserUseCase.execute():                                   │ │
│  │                                                                  │ │
│  │ ✅ ШАГ 1: Проверка Telegram группы                               │ │
│  │   └─ TelegramGroupChecker                                        │ │
│  │      └─ GET https://api.telegram.org/bot{TOKEN}/getChatMember    │ │
│  │         └─ Если НЕ в группе: ValueError("not_in_group")          │ │
│  │                                                                  │ │
│  │ ✅ ШАГ 2: Проверка лимита (5 аккаунтов на telegram_id)           │ │
│  │   └─ await repo.count_telegram_players(telegram_id)              │ │
│  │      └─ SQL: SELECT COUNT(*) FROM tgplayers WHERE telegram_id=? │ │
│  │         └─ Куда? → HOST_SERVER через db_bridge!                  │ │
│  │            └─ Если >= 5: ValueError("limit_exceeded")            │ │
│  │                                                                  │ │
│  │ ✅ ШАГ 3: Проверка уникальности логина                           │ │
│  │   └─ await repo.is_login_taken(login)                            │ │
│  │      └─ SQL: SELECT 1 FROM tgplayers WHERE login=?              │ │
│  │         └─ Куда? → HOST_SERVER через db_bridge!                  │ │
│  │            └─ Если найдено: ValueError("login_taken")            │ │
│  │                                                                  │ │
│  │ ✅ ШАГ 4: Сохранение в БД (ТРАНЗАКЦИЯ)                           │ │
│  │   └─ await repo.insert_user_and_tgplayer(...)                    │ │
│  │      └─ SQL: INSERT INTO tgplayers (telegram_id, username, login)│ │
│  │         └─ Куда? → HOST_SERVER через db_bridge!                  │ │
│  │                                                                  │ │
│  │ ✅ ШАГ 5: Создание персонажа в игре                              │ │
│  │   └─ await game_server_client.register_user(...)                │ │
│  │      └─ Socket на HOST_SERVER:5191 (game_bridge!)                │ │
│  │         └─ XML: <ADDUSER l="..." p="ENCRYPTED" g="..." m="..."/> │ │
│  │         └─ 📄 Детали: GAME_BRIDGE_IMPLEMENTATION_SUMMARY.md      │ │
│  │                                                                  │ │
│  │ ✅ ШАГ 6: Постановка в очередь (Redis на HOST_API)               │ │
│  │   └─ await queue.enqueue("request_queue", {...})                │ │
│  │                                                                  │ │
│  │ ✅ ШАГ 7: Формирование ответа                                    │ │
│  │   └─ return {"ok": true, "message": "Регистрация успешна!"}      │ │
│  │                                                                  │ │
│  └──────────────┬───────────────┬──────────────────────────────────┘ │
│                │               │                                      │
└────────────────┼───────────────┼──────────────────────────────────────┘
                 │               │
                 │ VPN tunnel    │ VPN tunnel
                 ↓               ↓
┌────────────────────────────────────────────────────────────────────────┐
│ HOST_SERVER (игровой сервер, 10.8.0.20 в VPN)                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ db_bridge :3307 (mTLS Proxy для MySQL)                           │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │ Роль: Безопасный прокси между HOST_API и MySQL                   │ │
│  │                                                                  │ │
│  │ Процесс:                                                         │ │
│  │ 1. ✅ Принимает подключение от api_father через VPN              │ │
│  │ 2. ✅ Проверяет mTLS сертификат (CA подпись)                     │ │
│  │ 3. ✅ Логирует: IP, CN, байты, latency                           │ │
│  │ 4. ✅ Проксирует SSL в MySQL (passthrough, БЕЗ паролей!)         │ │
│  │ 5. ✅ MySQL проверяет CN и подключает к нужному пользователю     │ │
│  │ 6. ✅ Возвращает результат обратно api_father                    │ │
│  │                                                                  │ │
│  │ 📄 Детали: DB_BRIDGE_NO_PASSWORDS_SOLUTION.md (БЕЗ паролей)     │ │
│  │ 📄 Логи: DB_BRIDGE_LOGGING.md (что и как логируется)            │ │
│  │                                                                  │ │
│  └──────────────────────────┬───────────────────────────────────────┘ │
│                             │                                          │
│                             ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ MySQL (unix-socket /var/run/mysqld/mysqld.sock)                  │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │ База: tzserver                                                   │ │
│  │                                                                  │ │
│  │ Таблицы:                                                         │ │
│  │ • constants - игровые константы (ServerStatus, RateExp, etc.)    │ │
│  │ • tgplayers - зарегистрированные игроки                          │ │
│  │                                                                  │ │
│  │ Выполняет:                                                       │ │
│  │ ✅ SELECT COUNT(*) FROM tgplayers WHERE telegram_id=?            │ │
│  │ ✅ SELECT 1 FROM tgplayers WHERE login=?                         │ │
│  │ ✅ INSERT INTO tgplayers (telegram_id, username, login) VALUES...│ │
│  │ ✅ SELECT Name, Value, Description FROM constants                │ │
│  │                                                                  │ │
│  │ ЭТО ЕДИНСТВЕННОЕ МЕСТО где хранятся:                             │ │
│  │ • Все игроки                                                     │ │
│  │ • Все логины                                                     │ │
│  │ • Все игровые данные                                             │ │
│  │                                                                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ game_bridge :5191 (TCP Proxy для Game Server)                   │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │ Роль: Безопасный прокси между HOST_API и Game Server             │ │
│  │                                                                  │ │
│  │ Процесс:                                                         │ │
│  │ 1. ✅ Принимает socket подключение от api_father через VPN       │ │
│  │ 2. ✅ Проверяет IP (whitelist: только 10.8.0.1)                  │ │
│  │ 3. ✅ Логирует запрос (client_ip, timestamp, size)               │ │
│  │ 4. ✅ Проксирует на localhost:5190                               │ │
│  │ 5. ✅ Получает ответ от Game Server                              │ │
│  │ 6. ✅ Возвращает ответ обратно api_father                        │ │
│  │                                                                  │ │
│  │ Технология: nginx stream (как db_bridge)                        │ │
│  │ Преимущества:                                                    │ │
│  │ • Game Server изолирован (только localhost)                      │ │
│  │ • Логирование всех запросов                                      │ │
│  │ • IP filtering встроен                                           │ │
│  │ • Rate limiting (опционально)                                    │ │
│  │                                                                  │ │
│  │ 📄 Детали: GAME_BRIDGE_IMPLEMENTATION_SUMMARY.md                │ │
│  │ 📄 Предложение: GAME_BRIDGE_PROPOSAL.md (зачем нужен)           │ │
│  │                                                                  │ │
│  └──────────────────────────┬───────────────────────────────────────┘ │
│                             │                                          │
│                             │ localhost (НЕ в VPN!)                   │
│                             ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ Game Server :5190 (127.0.0.1, Socket)                            │ │
│  ├──────────────────────────────────────────────────────────────────┤ │
│  │ Роль: Создание персонажей в игровом мире                         │ │
│  │                                                                  │ │
│  │ Слушает: ТОЛЬКО localhost:5190 (НЕ доступен из VPN!)             │ │
│  │                                                                  │ │
│  │ Процесс:                                                         │ │
│  │ 1. ✅ Принимает подключение от game_bridge (localhost)           │ │
│  │ 2. ✅ Читает XML: <ADDUSER l="Игрок123" p="ENCRYPTED" g="1" ... />│ │
│  │ 3. ✅ Парсит: login, encrypted_password, gender                  │ │
│  │ 4. ✅ Расшифровывает и проверяет пароль                          │ │
│  │ 5. ✅ Создает персонажа в игровом мире                           │ │
│  │    • Стартовая локация                                           │ │
│  │    • Начальные характеристики                                    │ │
│  │    • Стартовый инвентарь                                         │ │
│  │ 6. ✅ Возвращает ответ:                                          │ │
│  │    • <OK id="новый_id_персонажа"/> - успех                       │ │
│  │    • <ERROR msg="причина"/> - ошибка                             │ │
│  │                                                                  │ │
│  │ КТО подключается: game_bridge (localhost) ← api_father (VPN)     │ │
│  │                                                                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Цепочка запрос-ответ

### Полный поток (туда и обратно):

```
ЗАПРОС (Туда) ──────────────────────────────────────────────────▶

1. Сайт/Bot
   │ POST /api/register
   │ {"login": "Игрок123", "password": "mypass123", "gender": 1, "telegram_id": 123456789}
   ↓
2. Traefik (HOST_API)
   │ Маршрутизация: /api/register → api_2:8082
   ↓
3. API 2 (HOST_API)
   │ Валидация:
   │  ✅ login: паттерн ^(?=.*[а-яА-ЯёЁ])[а-яА-ЯёЁ0-9_\-\ ]{3,16}$
   │  ✅ password: паттерн ^[\x20-\x7E]{6,20}$
   │  ✅ gender: 0 или 1
   │ Proxy → api_father
   ↓
4. API Father (HOST_API)
   │ 
   │ ШАГ 1: Проверка Telegram группы
   │ ┌──────────────────────────────────────────────┐
   │ │ TelegramGroupChecker                         │
   │ │ → GET https://api.telegram.org/bot{}/getChatMember│
   │ │ → Если НЕ в группе: error("not_in_group")    │
   │ └──────────────────────────────────────────────┘
   │
   │ ШАГ 2: Проверка лимита
   │ ┌──────────────────────────────────────────────┐
   │ │ await repo.count_telegram_players(123456789) │
   │ │ ↓ pymysql.connect(host="10.8.0.20", port=3307)│
   │ │ ↓ SELECT COUNT(*) FROM tgplayers WHERE...   │
   ↓ └──────────────────────┬───────────────────────┘
                           │ SQL через VPN
                           ↓
5. db_bridge (HOST_SERVER :3307)
   │ ✅ Принимает подключение от api_father
   │ ✅ Проверяет mTLS сертификат (api_register)
   │ ✅ Проксирует SQL в MySQL unix-socket
   ↓
6. MySQL (HOST_SERVER, unix-socket)
   │ База: tzserver
   │ Выполняет: SELECT COUNT(*) FROM tgplayers WHERE telegram_id = 123456789
   │ Результат: count = 2

◀─ ОТВЕТ (Обратно) ──────────────────────────────────────────────

6. MySQL
   │ Результат: 2
   ↓
5. db_bridge
   │ Получает результат от MySQL
   │ Возвращает через mTLS обратно api_father
   │ через VPN
   ↓
4. API Father (HOST_API)
   │ Получает: count = 2
   │ Проверяет: 2 < 5? ✅ ДА
   │
   │ ШАГ 3: Проверка логина
   │ ┌──────────────────────────────────────────────┐
   │ │ await repo.is_login_taken("Игрок123")        │
   │ │ ↓ SELECT 1 FROM tgplayers WHERE login=?      │
   │ │ ↓ через db_bridge → MySQL → db_bridge        │
   │ │ ↓ Результат: не найдено (логин свободен)     │
   │ └──────────────────────────────────────────────┘
   │
   │ ШАГ 4: Сохранение
   │ ┌──────────────────────────────────────────────┐
   │ │ await repo.insert_user_and_tgplayer(...)     │
   │ │ ↓ BEGIN TRANSACTION;                         │
   │ │ ↓ INSERT INTO tgplayers (telegram_id, username, login)│
   │ │ ↓ COMMIT;                                    │
   │ │ ↓ через db_bridge → MySQL → db_bridge        │
   │ │ ↓ Результат: запись создана, id=3            │
   │ └──────────────────────────────────────────────┘
   │
   │ ШАГ 5: Создание персонажа
   │ ┌──────────────────────────────────────────────┐
   │ │ await game_server_client.register_user(...)  │
   │ │ ↓ Шифрование: encrypt_password("mypass123")  │
   │ │ ↓ XML: <ADDUSER l="Игрок123" p="ENCRYPTED" g="1"/>│
   │ │ ↓ socket.connect(("10.8.0.20", 5191))        │
   │ │   ↓ Подключается к game_bridge!              │
   │ │ ↓ sock.sendall(xml)                          │
   ↓ └──────────────────┬───────────────────────────┘
                       │ Socket через VPN
                       ↓
7. game_bridge (HOST_SERVER :5191)
   │ ✅ Принимает socket от api_father
   │ ✅ Проверяет IP (10.8.0.1)
   │ ✅ Логирует запрос
   │ ✅ Проксирует на localhost:5190
   ↓
8. Game Server (HOST_SERVER 127.0.0.1:5190)
   │ ✅ Принимает от game_bridge (localhost)
   │ ✅ Создает персонажа в игре
   │ ✅ Отправляет: <OK id="12345"/>
   ↓
◀──┴─────────────────────────────────────────────────────────────

8. Game Server → game_bridge → api_father
   │ Ответ: <OK id="12345"/>
   ↓
4. API Father
   │ Получает OK
   │ 
   │ ШАГ 6: Очередь
   │ └─ await queue.enqueue(...)
   │    └─ Redis (на HOST_API)
   │
   │ ШАГ 7: Формирование ответа
   │ └─ return {"ok": true, "message": "Регистрация успешна!"}
   ↓
3. API 2
   │ Получает {"ok": true}
   │ Возвращает как есть
   ↓
2. Traefik
   │ Проксирует ответ
   ↓
1. Сайт/Bot
   └─ Показывает: "✅ Регистрация успешна!"
```

### Упрощенная цепочка:

```
Сайт → API 2 → api_father → db_bridge → MySQL
                    ↓                      ↓
                    ↓                   результат
                    ↓                      ↓
                    ↓           ◀──────────┘
                    ↓
              game_bridge :5191 → Game Server :5190 (localhost)
                    ↓                     ↓
                    ↓                  <OK/>
                    ↓                     ↓
                    ↓           ◀─────────┘
       ◀────────────┴────────────────────────
                    ↓
Сайт ◀── API 2 ◀── {"ok": true}
```

**Ключевое изменение:** 
- api_father → game_bridge:5191 (в VPN)
- game_bridge → Game Server:5190 (localhost, изолирован)

---

## 🗄️ Где находится БД

### В ПРОДАКШНЕ:

```
┌────────────────────────────────────┐     ┌────────────────────────────┐
│ HOST_API (10.8.0.1)                │     │ HOST_SERVER (10.8.0.20)    │
├────────────────────────────────────┤     ├────────────────────────────┤
│                                    │     │                            │
│ ❌ НЕТ MySQL с игровыми данными    │     │ ✅ MySQL tzserver          │
│ ❌ НЕТ tgplayers                   │     │ ✅ tgplayers (ВСЕ игроки)  │
│ ❌ НЕТ constants                   │     │ ✅ constants (настройки)   │
│                                    │     │                            │
│ ✅ PostgreSQL api4_battles         │     │ ❌ НЕТ аналитики           │
│    (только аналитика боев)         │     │                            │
│                                    │     │                            │
│ ✅ Redis (очереди)                 │     │ ❌ НЕТ Redis               │
│                                    │     │                            │
└────────────────────────────────────┘     └────────────────────────────┘
```

### Таблица распределения данных:

| Тип данных | HOST_API | HOST_SERVER |
|------------|----------|-------------|
| **Игроки (tgplayers)** | ❌ НЕТ | ✅ tzserver.tgplayers |
| **Константы (constants)** | ❌ НЕТ | ✅ tzserver.constants |
| **Персонажи в игре** | ❌ НЕТ | ✅ Game Server |
| **Логи боев (исходные .tzb)** | ❌ НЕТ | ✅ /home/zero/logs/btl |
| **Аналитика боев (витрины)** | ✅ PostgreSQL api4_battles | ❌ НЕТ |
| **Сжатые логи (.gz)** | ✅ xml/gz/ | ❌ НЕТ |
| **Очереди задач** | ✅ Redis | ❌ НЕТ |

### Как api_father подключается к БД:

```python
# wg_client/api_father/app/infrastructure/db.py

def get_dsn_and_db():
    mode = os.getenv("DB_MODE")
    
    if mode == "production":
        # ПРОДАКШН - подключение к HOST_SERVER!
        return dict(
            host="10.8.0.20",      # ← HOST_SERVER через VPN
            port=3307,             # ← db_bridge (mTLS)
            user="api_register",   # ← mTLS пользователь
            password="...",
            database="tzserver",   # ← БД на HOST_SERVER
            charset='utf8mb4'
        ), "tzserver"
    
    else:  # mode == "test"
        # ЛОКАЛ - подключение к mock БД
        return dict(
            host="db",             # ← Локальный контейнер
            port=3306,
            user="tzuser",
            password="tzpass",
            database="tzserver",   # ← Та же схема, но ДРУГАЯ БД
            charset='utf8mb4'
        ), "tzserver"
```

### Ключевые моменты:

✅ **В ПРОДЕ на HOST_API НЕТ игровой БД**
- Только PostgreSQL для аналитики
- Только Redis для очередей

✅ **ВСЯ игровая БД на HOST_SERVER**
- tzserver.tgplayers
- tzserver.constants
- Все игровые таблицы

✅ **api_father подключается УДАЛЕННО**
- Через VPN (10.8.0.1 → 10.8.0.20)
- Через db_bridge:3307 (mTLS)
- К MySQL на HOST_SERVER

---

## 🎮 Подключение к Game Server через game_bridge

### 🔒 НОВАЯ АРХИТЕКТУРА: Изоляция через game_bridge

**КТО обращается?**
- **API Father** (контейнер на HOST_API) → **game_bridge** (HOST_SERVER) → **Game Server** (localhost)

### Почему game_bridge?

✅ **Безопасность:**
- Game Server изолирован (только localhost)
- Порт :5190 НЕ доступен в VPN
- IP whitelist (только 10.8.0.1 = HOST_API)

✅ **Единообразие:**
- db_bridge (MySQL) + game_bridge (Game Server)
- Единый подход для всех внешних сервисов

✅ **Мониторинг:**
- Логирование всех запросов
- Метрики (latency, errors)
- Rate limiting (опционально)

> 📄 **Детальное обоснование:** [`GAME_BRIDGE_PROPOSAL.md`](GAME_BRIDGE_PROPOSAL.md)  
> 📄 **Реализация:** [`GAME_BRIDGE_IMPLEMENTATION_SUMMARY.md`](GAME_BRIDGE_IMPLEMENTATION_SUMMARY.md)

### Код подключения:

```python
# wg_client/api_father/app/usecases/register_user.py (строка 52)

await self._gs.register_user(
    host=game_server_host,   # "10.8.0.20" (game_bridge!) в проде
    port=game_server_port,   # 5191 (game_bridge порт!)
    login=login,
    password=password,
    gender=gender,
)
```

### Реализация адаптера:

```python
# wg_client/api_father/app/adapters/socket_game_server_client.py

class SocketGameServerClient:
    def _encrypt(self, psw: str, key: str) -> str:
        """Шифрование пароля: SHA1 с перемешиванием по индексам"""
        s = (psw[0] + key[:10] + psw[1:] + key[10:]).replace(" ", "")
        h = hashlib.sha1(s.encode("ascii")).hexdigest().upper()
        indices = [30,26,24,39,2,15,1,4,5,18,27,38,10,19,33,17,7,36,34,31,
                   8,14,23,21,29,3,32,25,37,20,28,11,22,16,35,0,6,9,13,12]
        return "".join(h[i] for i in indices)
    
    async def register_user(self, *, host: str, port: int, login: str, password: str, gender: int) -> None:
        # 1. Шифрование пароля
        encrypted = self._encrypt(password, "0123456789ABCDEF0123456789ABCDEF")
        
        # 2. Формирование XML (формат из example/register.py)
        xml = f'<ADDUSER l="{login}" p="{encrypted}" g="{gender}" m="test@test.ru"/>\x00'
        
        # 3. Socket подключение
        with socket.create_connection((host, port), timeout=5.0) as sock:
            # 4. Отправка XML
            sock.sendall(xml.encode("utf-8"))
            
            # 5. Чтение ответа
            sock.settimeout(5.0)
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\x00" in data:
                    msg, _ = data.split(b"\x00", 1)
                    txt = msg.decode("utf-8", "replace")
                    
                    # 6. Проверка ответа
                    if txt.startswith("<OK"):
                        return  # ✅ Успех!
                    
                    raise RuntimeError("game_server_error")  # ❌ Ошибка
```

### Сетевое подключение:

**В ПРОДАКШНЕ (через game_bridge):**
```
api_father (HOST_API, 10.8.0.1)
    ↓
socket.connect(("10.8.0.20", 5191))  ← game_bridge порт!
    ↓ через VPN туннель WireGuard
    ↓
game_bridge (HOST_SERVER, 10.8.0.20:5191)
    ├─ Проверяет IP (whitelist: 10.8.0.1)
    ├─ Логирует запрос
    └─ Проксирует на localhost:5190
        ↓ localhost (НЕ в VPN!)
        ↓
    Game Server (127.0.0.1:5190)
        ├─ Слушает ТОЛЬКО localhost
        ├─ Обработка XML
        ├─ Создание персонажа
        └─ Ответ <OK id="123"/>
        ↓
game_bridge ← возврат
    ↓ через VPN обратно
    ↓
api_father ← возврат

БЕЗОПАСНОСТЬ: Game Server полностью изолирован!
```

**В ЛОКАЛЕ (mock, без game_bridge):**
```
api_father (контейнер)
    ↓
socket.connect(("game_server_mock", 5190))
    ↓ через Docker network "backnet"
    ↓
game_server_mock (контейнер на той же машине)
    ↓ эмуляция: всегда <OK/>
    ↓
api_father ← возврат

ПРИМЕЧАНИЕ: В локале можно без game_bridge для простоты
```

---

## 🔀 Локальная эмуляция vs Продакшн

### Что меняется при переходе на продакшн?

```
┌────────────────────────────┬─────────────────────────────┬────────────────────────┐
│ Компонент                  │ ЛОКАЛ (тесты)               │ ПРОД                   │
├────────────────────────────┼─────────────────────────────┼────────────────────────┤
│ Сайт/Источник запросов     │ curl/Postman (ручные тесты) │ Реальный сайт/бот      │
│                            │                             │                        │
│ VPN                        │ НЕТ (Docker networks)       │ WireGuard 10.8.0.0/24  │
│                            │                             │                        │
│ Traefik                    │ localhost:1010              │ 10.8.0.1:8081 (в VPN)  │
│                            │                             │                        │
│ API 2, API Father          │ Те же контейнеры            │ Те же контейнеры ✅    │
│                            │                             │                        │
│ MySQL (игровая БД)         │ db:6006 (локальная)         │ HOST_SERVER (удаленная)│
│                            │ host="db"                   │ host="10.8.0.20"       │
│                            │ port=3306                   │ port=3307              │
│                            │                             │                        │
│ db_bridge                  │ mock_db_bridge:3307         │ Реальный :3307 (mTLS)  │
│                            │ (без проверки сертификатов) │ (строгая проверка)     │
│                            │                             │                        │
│ game_bridge                │ НЕТ (прямое подключение)    │ Реальный :5191 (proxy) │
│                            │                             │ IP filter + логи       │
│                            │                             │                        │
│ Game Server                │ game_server_mock:5190       │ 127.0.0.1:5190         │
│                            │ (прямо из api_father)       │ (через game_bridge!)   │
│                            │ (всегда <OK/>)              │ (изолирован)           │
│                            │                             │                        │
│ Telegram проверка группы   │ Пропускается (токен пустой) │ Работает (реальный API)│
│                            │                             │                        │
│ Redis                      │ Тот же контейнер            │ Тот же контейнер ✅    │
│                            │                             │                        │
│ Файлы логов                │ mock_btl_rsyncd + xml/      │ HOST_SERVER /home/zero │
│                            │                             │                        │
│ Переключение               │ .env: ENVIRONMENT=local     │ .env: ENVIRONMENT=prod │
│                            │ DB_MODE=test                │ DB_MODE=production     │
└────────────────────────────┴─────────────────────────────┴────────────────────────┘
```

### Что НЕ меняется:

✅ **Код** - полностью одинаковый  
✅ **Docker образы** - те же самые  
✅ **API endpoints** - те же  
✅ **Логика** - та же  

### Что меняется:

📝 **Только переменные окружения в .env:**

```bash
# Локал
DB_TEST_HOST=db
GAME_SERVER_TEST_HOST=game_server_mock
GAME_SERVER_TEST_PORT=5190  # прямо к mock
TELEGRAM_BOT_TOKEN=  # пусто

# Прод
DB_PROD_HOST=10.8.0.20
DB_PROD_PORT=3307  # db_bridge
GAME_SERVER_PROD_HOST=10.8.0.20
GAME_SERVER_PROD_PORT=5191  # game_bridge!
TELEGRAM_BOT_TOKEN=реальный_токен
```

**Ключевое изменение:**
- `GAME_SERVER_PROD_PORT=5191` ← game_bridge порт вместо 5190!

---

## 🧪 Тестирование

> 📄 **Полные результаты тестов:** [`TEST_RESULTS_FINAL.md`](../TEST_RESULTS_FINAL.md)  
> 📄 **Скрипт тестирования:** [`test_api2_registration.sh`](../test_api2_registration.sh)

### Локальный тест (прямо сейчас):

```bash
# Регистрация с русским логином
curl -X POST http://localhost:1010/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "login": "Игрок123",
    "password": "mypass123",
    "gender": 1,
    "telegram_id": 999888777,
    "username": "test_player"
  }'

# Ожидаемый ответ:
{
  "ok": true,
  "message": "Регистрация успешна!"
}

# Проверка в локальной БД:
docker exec wg_client-db-1 mysql -uroot -prootpass tzserver \
  -e "SELECT telegram_id, username, login FROM tgplayers;"
```

### Тест лимита (5 аккаунтов):

```bash
# Создать 5 аккаунтов для telegram_id=111222333
for i in {1..5}; do
  curl -s -X POST http://localhost:1010/api/register \
    -H "Content-Type: application/json" \
    -d "{
      \"login\":\"Player${i}\",
      \"password\":\"pass${i}123\",
      \"gender\":$((i % 2)),
      \"telegram_id\":111222333
    }" | jq '.ok'
done

# Попытка создать 6-й аккаунт (должна быть ошибка):
curl -s -X POST http://localhost:1010/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "login":"Player6",
    "password":"pass6123",
    "gender":0,
    "telegram_id":111222333
  }' | jq '.'

# Ожидаемый ответ:
{
  "ok": false,
  "error": "limit_exceeded",
  "message": "Достигнут лимит: максимум 5 аккаунтов"
}
```

### Тест дубликата логина:

```bash
# Зарегистрировать "TestPlayer"
curl -X POST http://localhost:1010/api/register \
  -d '{"login":"TestPlayer","password":"pass123","gender":0,"telegram_id":555}'

# Попытка дубликата с другим telegram_id:
curl -X POST http://localhost:1010/api/register \
  -d '{"login":"TestPlayer","password":"another","gender":1,"telegram_id":666}'

# Ожидаемый ответ:
{
  "ok": false,
  "error": "login_taken",
  "message": "Этот логин уже занят"
}
```

---

## 📋 Резюме

> 📄 **Общая архитектура:** [`BRAIN_integration.md`](../../BRAIN_integration.md)  
> 📄 **Глобальная схема:** [`BRAIN_2.md`](../../BRAIN_2.md)

### ✅ api_father делает:
1. Обращается к **db_bridge:3307 на HOST_SERVER** (SQL через VPN + mTLS, БЕЗ паролей)
2. Получает **ответ от db_bridge** (результаты SQL запросов)
3. Обращается к **game_bridge:5191 на HOST_SERVER** (socket через VPN)
4. Получает **ответ от game_bridge** → Game Server → (<OK/> или <ERROR/>)
5. Формирует итоговый ответ
6. Возвращает в **API 2**
7. **API 2 возвращает** на сайт

> 📄 **Детали bridge:** см. ссылки выше в разделах db_bridge и game_bridge

### ✅ db_bridge - это прокси с разделением пользователей:
- **Туда:** принимает подключение от api_father
- **Проверяет:** mTLS сертификат (CA подпись) ✅
- **Логирует:** IP, CN, timestamp, байты, latency ✅
- **Проксирует:** SSL соединение в MySQL (passthrough)
- **MySQL:** сам извлекает CN и делает маппинг → user
  ```
  CN=api_register → пользователь api_register (SELECT, INSERT)
  CN=api_status   → пользователь api_status (SELECT только)
  ```
- **Обратно:** результат через db_bridge → api_father

**Важно:** 
- Параметр `user="api_register"` в pymysql должен = CN в сертификате!
- db_bridge НЕ хранит пароли ✅
- MySQL делает аутентификацию по сертификату БЕЗ ПАРОЛЯ ✅

**Логирование:**
- db_bridge логирует: IP, CN, байты, время
- db_bridge НЕ логирует: SQL запросы (безопасность)
- SQL логи (если нужно): включить на MySQL

### ✅ В ПРОДЕ на HOST_API:
- ❌ НЕТ игровой БД MySQL
- ❌ НЕТ tgplayers
- ✅ Только PostgreSQL (аналитика)
- ✅ Только Redis (очереди)

### ✅ ВСЕ игровые данные на HOST_SERVER:
- tzserver.tgplayers (игроки)
- tzserver.constants (настройки)
- Game Server (персонажи в игре)

**Ваше понимание идеально! 🎉**

---

## 🔐 Приложение: Разделение пользователей БД через mTLS

### Механизм безопасности

Каждый API использует свой mTLS сертификат → свой пользователь БД → свои права!

### Таблица разделения прав:

| API | Сертификат (CN) | MySQL User | Права | Таблицы | Примеры запросов |
|-----|----------------|------------|-------|---------|------------------|
| **API 2** (регистрация) | `api_register` | `api_user_register` | SELECT, INSERT | tgplayers, constants | SELECT COUNT(*), INSERT INTO tgplayers |
| **API 1** (статус/бонусы) | `api_status` | `api_user_status` | SELECT | constants, tgplayers | SELECT FROM constants |
| **API 3** (информация) | `api_status` | `api_user_status` | SELECT | constants, tgplayers | SELECT FROM tgplayers |
| **API 4** (аналитика) | - | - | - | PostgreSQL | Использует свою БД api4_battles |

**Итого: 2 MySQL пользователя** (api_user_register, api_user_status)

### Как работает маппинг:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. api_father отправляет запрос с сертификатом              │
│    ssl={'cert': '/certs/api_register.crt'}                  │
│    CN в сертификате: "api_register"                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. db_bridge получает подключение                           │
│    • Проверяет подпись CA ✅                                │
│    • Извлекает CN = "api_register"                          │
│    • Маппинг: CN → MySQL user                               │
│      "api_register" → "api_user_register"                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. db_bridge проксирует SSL соединение в MySQL              │
│    • БЕЗ расшифровки (SSL passthrough)                      │
│    • БЕЗ хранения паролей ✅                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 3.5. MySQL получает SSL соединение с сертификатом           │
│    • Проверяет подпись CA ✅                                │
│    • Извлекает CN = "api_register" ✅                       │
│    • Находит пользователя "api_register" ✅                 │
│    • Проверяет REQUIRE SUBJECT ✅                           │
│    • Подключение БЕЗ ПАРОЛЯ! ✅                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. MySQL выполняет запрос                                   │
│    От имени: api_register (пользователь БД)                 │
│    Права: SELECT, INSERT на tgplayers ✅                    │
│    SELECT COUNT(*) FROM tgplayers... ✅ РАЗРЕШЕНО           │
└─────────────────────────────────────────────────────────────┘

**Ключевой момент:** 
- db_bridge НЕ хранит пароли! ✅
- MySQL сам проверяет сертификат и делает маппинг CN → user
- Имя пользователя БД = CN из сертификата (для простоты)
```

### Безопасность:

**Сценарий атаки (если взломан API 1):**
```
1. Хакер получает сертификат api_status.crt
2. Подключается к db_bridge
3. db_bridge: CN=api_status → api_user_status
4. MySQL: api_user_status имеет ТОЛЬКО SELECT
5. Попытка: DELETE FROM tgplayers
6. MySQL ответ: ERROR 1142 (42000): 
   DELETE command denied to user 'api_user_status'
7. ✅ Атака отражена!
```

### Пользователи БД (создаются на HOST_SERVER):

```sql
-- 1. Для регистрации (API 2) - БЕЗ ПАРОЛЯ!
CREATE USER 'api_register'@'localhost'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API/OU=Registration'
  AND ISSUER '/CN=CA/O=HOST_API';

GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_register'@'localhost';
GRANT SELECT ON tzserver.constants TO 'api_register'@'localhost';
FLUSH PRIVILEGES;

-- 2. Для чтения статуса и бонусов (API 1, API 3) - БЕЗ ПАРОЛЯ!
CREATE USER 'api_status'@'localhost'
REQUIRE SUBJECT '/CN=api_status/O=HOST_API/OU=Status'
  AND ISSUER '/CN=CA/O=HOST_API';

GRANT SELECT ON tzserver.constants TO 'api_status'@'localhost';
GRANT SELECT ON tzserver.tgplayers TO 'api_status'@'localhost';
FLUSH PRIVILEGES;

-- Примечания:
-- • Аутентификация через SSL сертификат (БЕЗ ПАРОЛЯ!)
-- • Имя пользователя БД = CN из сертификата
-- • API 4 использует PostgreSQL api4_battles, MySQL пользователь НЕ нужен
```

**Проверка прав:**
```sql
-- Проверить пользователей
SHOW GRANTS FOR 'api_register'@'localhost';
SHOW GRANTS FOR 'api_status'@'localhost';

-- Проверить SSL требования
SELECT user, host, ssl_type, x509_subject 
FROM mysql.user 
WHERE user LIKE 'api_%';

-- Должно показать REQUIRE SUBJECT для каждого пользователя
```

### Сертификаты (создаются на HOST_API):

```bash
# Структура /certs/
/certs/
├── ca.crt                # CA для проверки
├── ca.key
├── api_register.crt      # CN=api_register (API 2 - регистрация)
├── api_register.key
├── api_status.crt        # CN=api_status (API 1, API 3 - статус/бонусы)
└── api_status.key

# Примечание: api_analytics.crt НЕ нужен, 
# т.к. API 4 использует PostgreSQL, а не MySQL tzserver
```

**Команды для генерации:**
```bash
# 1. Сертификат для регистрации (API 2)
openssl req -new -key api_register.key -out api_register.csr \
    -subj "/CN=api_register/O=HOST_API/OU=Registration"
openssl x509 -req -in api_register.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out api_register.crt -days 365

# 2. Сертификат для статуса (API 1, API 3)
openssl req -new -key api_status.key -out api_status.csr \
    -subj "/CN=api_status/O=HOST_API/OU=Status"
openssl x509 -req -in api_status.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out api_status.crt -days 365
```

### Текущий статус реализации:

⚠️ **В локальных тестах (сейчас):**
- mock_db_bridge БЕЗ маппинга пользователей
- Один пользователь БД (`tzuser`) для всех API
- Подходит для разработки и тестирования

✅ **В продакшне (требуется):**
- db_bridge С маппингом CN → MySQL user
- **2 пользователя БД:** `api_user_register`, `api_user_status`
- **2 сертификата:** `api_register.crt`, `api_status.crt`
- Минимальные права для каждого (принцип наименьших привилегий)

### Реализация маппинга (для прода):

**УПРОЩЕННОЕ РЕШЕНИЕ:** MySQL делает маппинг сам!

```
db_bridge = простой SSL passthrough (nginx stream)
MySQL = проверяет сертификат и делает CN → user автоматически
```

**НЕ требуется:**
- ❌ Python/Go proxy
- ❌ Хранение паролей в db_bridge
- ❌ Сложный маппинг в коде

**Требуется:**
- ✅ MySQL с SSL сертификатами
- ✅ Пользователи БД с `REQUIRE SUBJECT`
- ✅ Простой nginx stream (passthrough)

**Детали:** См. `DB_BRIDGE_NO_PASSWORDS_SOLUTION.md`

---

## 🔧 Настройка MySQL для входа БЕЗ пароля (Production)

### Шаг 1: Настроить MySQL с SSL сертификатами

#### 1.1. Создать сертификаты для MySQL сервера (на HOST_SERVER):

```bash
# Перейти в директорию с сертификатами
cd /etc/mysql/certs

# CA уже должен быть создан (тот же, что для клиентов)
# Если нет:
openssl genrsa 2048 > ca.key
openssl req -new -x509 -nodes -days 3650 -key ca.key -out ca.crt \
    -subj "/CN=CA/O=HOST_API"

# Создать серверный ключ и сертификат для MySQL
openssl req -newkey rsa:2048 -nodes -days 3650 -keyout mysql_server.key \
    -out mysql_server.csr \
    -subj "/CN=mysql_server/O=HOST_SERVER"

openssl x509 -req -in mysql_server.csr -days 3650 \
    -CA ca.crt -CAkey ca.key -set_serial 01 -out mysql_server.crt

# Права доступа
chown mysql:mysql ca.crt mysql_server.crt mysql_server.key
chmod 600 mysql_server.key
chmod 644 ca.crt mysql_server.crt
```

#### 1.2. Настроить MySQL (my.cnf или /etc/mysql/mysql.conf.d/mysqld.cnf):

```ini
[mysqld]
# Базовые настройки
bind-address = 127.0.0.1  # Слушать ТОЛЬКО localhost
port = 3306

# SSL сертификаты (включить SSL, но НЕ требовать для всех!)
ssl-ca=/etc/mysql/certs/ca.crt
ssl-cert=/etc/mysql/certs/mysql_server.crt
ssl-key=/etc/mysql/certs/mysql_server.key

# НЕ используем require_secure_transport=ON !
# Это требует SSL для ВСЕХ пользователей (включая существующих)

# Вместо этого: требование SSL на уровне ОТДЕЛЬНЫХ пользователей
# через REQUIRE SUBJECT при CREATE USER

# Опционально: разрешить только TLSv1.2 и TLSv1.3
tls-version=TLSv1.2,TLSv1.3
```

**Важно:** 
- ❌ **НЕ включать** `require_secure_transport=ON` - это затронет всех пользователей!
- ✅ **Включить только SSL** (ssl-ca, ssl-cert, ssl-key) - делает SSL доступным
- ✅ **Требование SSL** устанавливается на уровне отдельных пользователей

#### 1.3. Перезапустить MySQL:

```bash
systemctl restart mysql
# или
service mysql restart
```

#### 1.4. Проверить SSL:

```sql
-- Подключиться к MySQL
mysql -uroot -p

-- Проверить статус SSL
SHOW VARIABLES LIKE '%ssl%';

-- Должно показать:
-- have_ssl: YES
-- ssl_ca: /etc/mysql/certs/ca.crt
-- ssl_cert: /etc/mysql/certs/mysql_server.crt
-- ssl_key: /etc/mysql/certs/mysql_server.key

-- Проверить текущее подключение
SHOW STATUS LIKE 'Ssl_cipher';

-- Должно показать используемый cipher (например: TLS_AES_256_GCM_SHA384)
```

---

### Шаг 2: Создать пользователей БД БЕЗ паролей

#### 2.1. Пользователь для регистрации (API 2):

```sql
-- Создать пользователя с требованием SSL сертификата (БЕЗ пароля!)
CREATE USER 'api_register'@'localhost'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API/OU=Registration'
  AND ISSUER '/CN=CA/O=HOST_API';

-- Проверка: пользователь создан БЕЗ пароля!
-- Аутентификация ТОЛЬКО через SSL сертификат
-- Другие пользователи БД НЕ затронуты!

-- Выдать права для регистрации
GRANT SELECT, INSERT ON tzserver.tgplayers TO 'api_register'@'localhost';
GRANT SELECT ON tzserver.constants TO 'api_register'@'localhost';

-- Применить
FLUSH PRIVILEGES;
```

**Важно:** Этот пользователь требует SSL, но **остальные пользователи БД** (например, root, tzuser, gameuser и т.д.) **продолжат работать с паролями как раньше**!

> 📄 **Детали сосуществования:** [`MYSQL_SSL_COEXISTENCE.md`](../MYSQL_SSL_COEXISTENCE.md) - как SSL и обычные пользователи работают вместе

#### 2.2. Пользователь для чтения статуса (API 1, API 3):

```sql
-- Создать пользователя с требованием SSL сертификата
CREATE USER 'api_status'@'localhost'
REQUIRE SUBJECT '/CN=api_status/O=HOST_API/OU=Status'
  AND ISSUER '/CN=CA/O=HOST_API';

-- Выдать права только на чтение
GRANT SELECT ON tzserver.constants TO 'api_status'@'localhost';
GRANT SELECT ON tzserver.tgplayers TO 'api_status'@'localhost';

-- Применить
FLUSH PRIVILEGES;
```

#### 2.3. Проверить созданных пользователей:

```sql
-- Список пользователей с SSL требованиями
SELECT user, host, ssl_type, x509_issuer, x509_subject, password_expired
FROM mysql.user
WHERE user LIKE 'api_%';

-- Должно показать:
-- user: api_register, host: localhost
-- ssl_type: SPECIFIED
-- x509_issuer: /CN=CA/O=HOST_API
-- x509_subject: /CN=api_register/O=HOST_API/OU=Registration
-- password_expired: N

-- Проверить права
SHOW GRANTS FOR 'api_register'@'localhost';
SHOW GRANTS FOR 'api_status'@'localhost';

-- Проверить, что старые пользователи НЕ затронуты
SELECT user, host, ssl_type FROM mysql.user;

-- Должно показать:
-- root       | localhost | (пусто или ANY) ← работает с паролем
-- tzuser     | %         | (пусто или ANY) ← работает с паролем
-- gameuser   | localhost | (пусто или ANY) ← работает с паролем
-- api_register | localhost | SPECIFIED     ← требует SSL!
-- api_status   | localhost | SPECIFIED     ← требует SSL!
```

---

#### 2.4. Примеры: как существующие пользователи продолжат работать

```sql
-- Существующий пользователь с паролем (НЕ затронут)
-- Пример: tzuser, root, gameuser

-- Подключение с паролем (как раньше):
mysql -utzuser -ptzpass tzserver
-- ✅ Работает! Пароль принят, SSL НЕ требуется

-- Новый пользователь api_register (требует SSL):
mysql -uapi_register tzserver
-- ❌ Ошибка! Access denied (нужен SSL сертификат)

mysql -uapi_register --ssl-cert=/certs/api_register.crt \
  --ssl-key=/certs/api_register.key --ssl-ca=/certs/ca.crt tzserver
-- ✅ Работает! SSL сертификат принят, пароль НЕ нужен
```

---

### Шаг 3: Создать клиентские сертификаты (на HOST_API)

#### 3.1. Сертификат для API 2 (регистрация):

```bash
cd /path/to/certs

# Создать ключ
openssl genrsa 2048 > api_register.key

# Создать CSR (Certificate Signing Request)
openssl req -new -key api_register.key -out api_register.csr \
    -subj "/CN=api_register/O=HOST_API/OU=Registration"

# Подписать CA (тот же CA, что на MySQL сервере!)
openssl x509 -req -in api_register.csr -days 3650 \
    -CA ca.crt -CAkey ca.key -set_serial 02 -out api_register.crt

# Проверить сертификат
openssl x509 -in api_register.crt -text -noout | grep Subject

# Должно показать:
# Subject: CN=api_register, O=HOST_API, OU=Registration

# Права доступа
chmod 600 api_register.key
chmod 644 api_register.crt
```

#### 3.2. Сертификат для API 1, API 3 (статус):

```bash
# Создать ключ
openssl genrsa 2048 > api_status.key

# Создать CSR
openssl req -new -key api_status.key -out api_status.csr \
    -subj "/CN=api_status/O=HOST_API/OU=Status"

# Подписать CA
openssl x509 -req -in api_status.csr -days 3650 \
    -CA ca.crt -CAkey ca.key -set_serial 03 -out api_status.crt

# Проверить
openssl x509 -in api_status.crt -text -noout | grep Subject

# Права доступа
chmod 600 api_status.key
chmod 644 api_status.crt
```

#### 3.3. Итоговая структура сертификатов:

```
HOST_API: /certs/
├── ca.crt                # CA (общий для MySQL и клиентов)
├── api_register.crt      # CN=api_register (для API 2)
├── api_register.key
├── api_status.crt        # CN=api_status (для API 1, 3)
└── api_status.key

HOST_SERVER: /etc/mysql/certs/
├── ca.crt                # Тот же CA!
├── mysql_server.crt      # Серверный сертификат MySQL
└── mysql_server.key
```

---

### Шаг 4: Настроить api_father для подключения БЕЗ пароля

#### 4.1. Обновить код подключения:

```python
# wg_client/api_father/app/infrastructure/db.py

import os
import pymysql

def get_dsn_and_db():
    mode = os.getenv("DB_MODE", "test")
    
    if mode == "production":
        # ПРОДАКШН - подключение через db_bridge БЕЗ ПАРОЛЯ!
        return dict(
            host="10.8.0.20",      # HOST_SERVER через VPN
            port=3307,             # db_bridge
            user="api_register",   # Имя = CN в сертификате!
            # password - НЕ УКАЗЫВАЕМ! БЕЗ ПАРОЛЯ!
            database="tzserver",
            charset='utf8mb4',
            use_unicode=True,
            ssl={
                'ca': '/certs/ca.crt',
                'cert': '/certs/api_register.crt',  # CN=api_register
                'key': '/certs/api_register.key',
                'check_hostname': False,
                'verify_mode': ssl.CERT_REQUIRED,
            }
        ), "tzserver"
    
    else:  # mode == "test"
        # ЛОКАЛ - обычное подключение с паролем
        return dict(
            host="db",
            port=3306,
            user="tzuser",
            password="tzpass",  # В локале пароль есть
            database="tzserver",
            charset='utf8mb4',
            use_unicode=True,
        ), "tzserver"
```

#### 4.2. Переменные окружения (.env):

```bash
# Продакшн (БЕЗ пароля!)
DB_MODE=production
DB_PROD_HOST=10.8.0.20
DB_PROD_PORT=3307
DB_PROD_NAME=tzserver
DB_PROD_USER=api_register
# DB_PROD_PASSWORD - НЕ НУЖЕН!

# SSL сертификаты (примонтировать в Docker)
DB_SSL_CA=/certs/ca.crt
DB_SSL_CERT=/certs/api_register.crt
DB_SSL_KEY=/certs/api_register.key
```

#### 4.3. Docker Compose (монтирование сертификатов):

```yaml
# HOST_API_SERVICE_FATHER_API.yml

services:
  api_father:
    # ...
    volumes:
      # Монтируем SSL сертификаты
      - ./certs/ca.crt:/certs/ca.crt:ro
      - ./certs/api_register.crt:/certs/api_register.crt:ro
      - ./certs/api_register.key:/certs/api_register.key:ro
    environment:
      - DB_MODE=production
      - DB_PROD_HOST=10.8.0.20
      - DB_PROD_PORT=3307
      - DB_PROD_USER=api_register
      # БЕЗ DB_PROD_PASSWORD!
```

---

### Шаг 5: Тестирование подключения БЕЗ пароля

#### 5.1. Тест из командной строки MySQL:

```bash
# Подключение с SSL сертификатом БЕЗ пароля
mysql \
  --host=127.0.0.1 \
  --port=3306 \
  --user=api_register \
  --ssl-ca=/etc/mysql/certs/ca.crt \
  --ssl-cert=/path/to/api_register.crt \
  --ssl-key=/path/to/api_register.key \
  --ssl-mode=REQUIRED \
  tzserver

# Если подключение успешно - все работает!
# Если ошибка: проверить REQUIRE SUBJECT в пользователе
```

#### 5.2. Проверить текущее подключение:

```sql
-- После подключения
SELECT USER(), CURRENT_USER();
-- Должно показать: api_register@localhost

-- Проверить SSL статус
\s
-- Или:
SHOW STATUS LIKE 'Ssl_cipher';
-- Должно показать cipher (например: TLS_AES_256_GCM_SHA384)

-- Проверить права
SHOW GRANTS;
-- Должно показать только разрешенные операции
```

#### 5.3. Тест запросов:

```sql
-- Разрешенные операции для api_register:
SELECT COUNT(*) FROM tgplayers WHERE telegram_id = 12345;  ✅
SELECT 1 FROM tgplayers WHERE login = 'Test';  ✅
INSERT INTO tgplayers (telegram_id, username, login) VALUES (999, 'user', 'Test');  ✅

-- Запрещенные операции:
DELETE FROM tgplayers WHERE telegram_id = 12345;  ❌
UPDATE tgplayers SET login = 'hacked' WHERE telegram_id = 12345;  ❌
DROP TABLE tgplayers;  ❌

-- Ожидаемая ошибка:
-- ERROR 1142 (42000): DELETE command denied to user 'api_register'@'localhost' for table 'tgplayers'
```

---

### Шаг 6: Настроить db_bridge (на HOST_SERVER)

#### 6.1. Простой вариант (SSL passthrough):

```nginx
# /etc/nginx/db_bridge/nginx.conf

stream {
    # Формат лога с CN из сертификата
    log_format db_proxy '$remote_addr - $ssl_client_s_dn [$time_local] '
                        '$protocol $status '
                        'sent:$bytes_sent recv:$bytes_received '
                        'time:${session_time}s '
                        'upstream:"$upstream_addr"';
    
    access_log /var/log/nginx/db_bridge.log db_proxy;
    error_log  /var/log/nginx/db_bridge_error.log warn;
    
    server {
        listen 3307;
        
        # Просто проксируем TCP в MySQL
        # MySQL сам проверит SSL и сделает аутентификацию
        proxy_pass 127.0.0.1:3306;
        
        # Таймауты
        proxy_connect_timeout 5s;
        proxy_timeout 10s;
    }
}

events {
    worker_connections 1024;
}
```

#### 6.2. С проверкой сертификата на уровне db_bridge:

```nginx
stream {
    log_format db_proxy '$remote_addr - $ssl_client_s_dn [$time_local] '
                        '$protocol $status '
                        'sent:$bytes_sent recv:$bytes_received '
                        'time:${session_time}s';
    
    access_log /var/log/nginx/db_bridge.log db_proxy;
    error_log  /var/log/nginx/db_bridge_error.log warn;
    
    server {
        listen 3307 ssl;
        
        # Сертификаты db_bridge
        ssl_certificate     /etc/nginx/certs/db_bridge_server.crt;
        ssl_certificate_key /etc/nginx/certs/db_bridge_server.key;
        
        # Проверка клиентского сертификата
        ssl_client_certificate /etc/nginx/certs/ca.crt;
        ssl_verify_client on;
        ssl_verify_depth 2;
        
        # Проксируем в MySQL
        proxy_pass 127.0.0.1:3306;
        
        # MySQL получит уже "чистое" подключение
        # Нужно передать сертификат клиента в MySQL
        # Это требует SSL re-wrapping (сложно)
    }
}
```

**Рекомендация:** Использовать вариант 6.1 (простой passthrough) для начала.

---

### Шаг 7: Проверить подключение через db_bridge

#### 7.1. Тест с хоста (HOST_API):

```bash
# С HOST_API подключиться к db_bridge на HOST_SERVER
mysql \
  --host=10.8.0.20 \
  --port=3307 \
  --user=api_register \
  --ssl-ca=/certs/ca.crt \
  --ssl-cert=/certs/api_register.crt \
  --ssl-key=/certs/api_register.key \
  --ssl-mode=REQUIRED \
  tzserver

# Если подключение успешно:
mysql> SELECT USER(), CURRENT_USER();
+---------------------------+---------------------------+
| USER()                    | CURRENT_USER()            |
+---------------------------+---------------------------+
| api_register@10.8.0.1     | api_register@localhost    |
+---------------------------+---------------------------+

# ✅ Успех! Подключение БЕЗ ПАРОЛЯ через db_bridge!
```

#### 7.2. Проверить логи db_bridge:

```bash
# На HOST_SERVER
tail -f /var/log/nginx/db_bridge.log

# Должно показать:
# 10.8.0.1 - CN=api_register,O=HOST_API,OU=Registration [01/Oct/2025:10:30:00 +0000] TCP 200 sent:256 recv:512 time:0.123s upstream:"127.0.0.1:3306"
```

---

### Шаг 8: Troubleshooting

#### Проблема 1: "Access denied for user"

```bash
# Проверить требования SSL в пользователе
mysql -uroot -p
SELECT user, host, ssl_type, x509_subject FROM mysql.user WHERE user='api_register';

# Если ssl_type пустое:
ALTER USER 'api_register'@'localhost' 
REQUIRE SUBJECT '/CN=api_register/O=HOST_API/OU=Registration';
FLUSH PRIVILEGES;
```

#### Проблема 2: "SSL connection error"

```bash
# Проверить сертификаты
openssl verify -CAfile ca.crt api_register.crt
# Должно показать: api_register.crt: OK

# Проверить что CN совпадает
openssl x509 -in api_register.crt -noout -subject
# Subject: CN=api_register, O=HOST_API, OU=Registration
```

#### Проблема 3: "Certificate doesn't match"

```sql
-- Проверить точное соответствие SUBJECT
SELECT x509_subject FROM mysql.user WHERE user='api_register';

-- Должно быть:
-- /CN=api_register/O=HOST_API/OU=Registration

-- Если не совпадает - пересоздать пользователя с правильным SUBJECT
DROP USER 'api_register'@'localhost';
CREATE USER 'api_register'@'localhost'
REQUIRE SUBJECT '/CN=api_register/O=HOST_API/OU=Registration';
```

---

### Шаг 9: Финальная проверка

#### 9.1. Чеклист:

```
✅ MySQL настроен с SSL (ssl-ca, ssl-cert, ssl-key)
✅ MySQL требует SSL (require_secure_transport=ON)
✅ Пользователи созданы с REQUIRE SUBJECT
✅ Клиентские сертификаты созданы и подписаны CA
✅ CN в сертификате = имя пользователя БД
✅ db_bridge проксирует на MySQL
✅ Тест подключения через db_bridge успешен
✅ Логи db_bridge показывают CN
✅ Запрещенные операции блокируются
```

#### 9.2. Итоговая схема:

```
api_father (HOST_API)
    ├─ Сертификат: api_register.crt (CN=api_register)
    ├─ БЕЗ пароля!
    ↓
db_bridge:3307 (HOST_SERVER)
    ├─ Проверяет CA подпись ✅
    ├─ Логирует: IP, CN, байты
    ├─ Проксирует в MySQL
    ↓
MySQL:3306 (localhost)
    ├─ Проверяет SSL сертификат ✅
    ├─ Извлекает CN = "api_register"
    ├─ Находит пользователя "api_register"
    ├─ Проверяет REQUIRE SUBJECT ✅
    ├─ Подключение БЕЗ ПАРОЛЯ! ✅
    └─ Выполняет запрос с правами api_register
```

---

### 📝 Команды для быстрого старта:

```bash
# 1. На HOST_SERVER: Настроить MySQL SSL
vim /etc/mysql/mysql.conf.d/mysqld.cnf
# Добавить ssl-ca, ssl-cert, ssl-key, require_secure_transport=ON
systemctl restart mysql

# 2. На HOST_SERVER: Создать пользователей БЕЗ паролей
mysql -uroot -p < create_ssl_users.sql

# 3. На HOST_API: Создать клиентские сертификаты
./generate_client_certs.sh

# 4. На HOST_API: Обновить api_father код
# Убрать password из DSN, добавить ssl={'cert': ...}

# 5. Тест подключения
mysql --host=10.8.0.20 --port=3307 --user=api_register \
  --ssl-cert=/certs/api_register.crt --ssl-key=/certs/api_register.key \
  --ssl-ca=/certs/ca.crt tzserver

# 6. ✅ Готово!
```

---

**Важно:** В локальных тестах можно оставить подключение с паролем для простоты. В продакшне ОБЯЗАТЕЛЬНО использовать SSL сертификаты БЕЗ паролей!

---

## 🔑 Ключевые принципы безопасности

### 1. БЕЗ паролей ✅
- db_bridge НЕ хранит пароли БД
- api_father НЕ знает пароли БД
- MySQL аутентификация через SSL сертификат

### 2. Разделение прав ✅
- api_register (API 2): SELECT, INSERT
- api_status (API 1, 3): SELECT только

### 3. Упрощенная архитектура ✅
- db_bridge = простой TCP/SSL passthrough
- MySQL делает маппинг CN → user сам
- Меньше кода = меньше уязвимостей

### 4. Принцип наименьших привилегий ✅
- Каждый API имеет минимально необходимые права
- Взлом одного API НЕ дает доступ к другим операциям

---

**Обновлено:** 2025-10-01 
- Добавлен раздел о разделении пользователей БД
- Исправлено: БЕЗ хранения паролей в db_bridge
- Добавлена информация о game_bridge
