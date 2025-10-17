# 📚 Детальное описание API сервисов

## 1️⃣ API 1 - Server Status (Статус сервера)

### Назначение
Предоставляет информацию о состоянии игрового сервера и игровых констант (рейты, статус сервера).

### База данных
- **БД**: MySQL `gamedb`
- **Таблица**: `constants`
- **Доступ**: Через `api_father` (READ ONLY)

### Схема таблицы `constants`
```sql
CREATE TABLE constants (
  my_row_id INT PRIMARY KEY AUTO_INCREMENT,
  Name VARCHAR(64) NOT NULL UNIQUE,
  Value DECIMAL(10,2) NOT NULL DEFAULT 0,
  Description VARCHAR(255) NOT NULL DEFAULT ''
);
```

### Используемые поля
API 1 читает следующие константы из таблицы:
- `ServerStatus` - статус сервера (1 = доступен)
- `RateExp` - множитель опыта
- `RatePvp` - множитель PVP
- `RatePve` - множитель PVE  
- `RateColorMob` - множитель для цветных мобов
- `RateSkill` - множитель скиллов
- `CLIENT_STATUS` - статус клиента (256 = актуальная версия)

### API Endpoints

#### GET /server/status
Возвращает статус сервера и рейты.

**Запрос:**
```bash
curl http://localhost:1010/api/server/status
```

**Ответ:**
```json
{
  "server_status": 1.0,
  "rates": {
    "exp": 1.0,
    "pvp": 1.0,
    "pve": 1.0,
    "color_mob": 1.0,
    "skill": 1.0
  },
  "client_status": 256.0,
  "_meta": {
    "ServerStatus": "1 = всем доступен серв",
    "RateExp": "Опыт",
    "RatePvp": "ПВП",
    "RatePve": "ПВЕ",
    "RateColorMob": "x1",
    "RateSkill": "Скиллы",
    "CLIENT_STATUS": "статус"
  }
}
```

#### GET /healthz
Health check endpoint.

**Запрос:**
```bash
curl http://localhost:1010/api/healthz
```

**Ответ:**
```json
{"status": "ok"}
```

### Архитектура
```
API 1 → api_father → db_bridge (mTLS) → MySQL gamedb.constants
```

### Права доступа
- **Роль**: READ ONLY
- **mTLS пользователь**: `api_readonly` (рекомендуется)
- **SQL операции**: только `SELECT`

### Порт
- **Внутренний**: 8081
- **Внешний**: доступ только через Traefik :1010

---

## 2️⃣ API 2 - Registration (Регистрация)

### Назначение
Регистрация новых пользователей и создание игровых аккаунтов.

### База данных
- **БД**: MySQL `gamedb`
- **Таблицы**: `users`, `tgplayers`
- **Доступ**: Через `api_father` (INSERT + SELECT)

### Схема таблиц

#### Таблица `users`
```sql
CREATE TABLE users (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  login VARCHAR(16) COLLATE utf8mb4_bin NOT NULL UNIQUE,
  gender TINYINT UNSIGNED NULL,
  email VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### Таблица `tgplayers`
```sql
CREATE TABLE tgplayers (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  telegram_id BIGINT UNSIGNED NOT NULL,
  username VARCHAR(64) NULL,
  login VARCHAR(16) COLLATE utf8mb4_bin NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_tgplayers_telegram_id (telegram_id),
  FOREIGN KEY (login) REFERENCES users(login) ON DELETE CASCADE
);
```

### Используемые поля

#### В таблице `users`:
- `id` - уникальный ID пользователя (auto increment)
- `login` - логин игрока (3-16 символов, уникальный)
- `gender` - пол персонажа (0 или 1)
- `email` - email (опционально)
- `created_at` - дата создания

#### В таблице `tgplayers`:
- `id` - уникальный ID записи
- `telegram_id` - ID пользователя Telegram
- `username` - username в Telegram (опционально)
- `login` - связь с таблицей users
- `created_at` - дата создания

### API Endpoints

#### POST /register
Регистрация нового пользователя.

**Запрос:**
```bash
curl -X POST http://localhost:1010/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "login": "player123",
    "password": "secret123",
    "gender": 1,
    "telegram_id": 123456789,
    "username": "player_telegram",
    "user_created_at": "2025-10-01 10:00:00",
    "user_registration_ip": "192.168.1.1",
    "user_Country": "RU",
    "user_registration_type": "telegram"
  }'
```

**Ответ (успех):**
```json
{
  "ok": true,
  "user_id": 12345,
  "login": "player123",
  "message": "Регистрация успешна"
}
```

**Ответ (ошибка):**
```json
{
  "ok": false,
  "error": "login_taken",
  "message": "Ошибка: логин уже занят",
  "fields": {
    "login": "Ошибка: Логин должен быть от 3 до 16 символов"
  }
}
```

#### GET /register/health
Health check.

**Запрос:**
```bash
curl http://localhost:1010/api/register/health
```

### Бизнес-логика

1. **Проверка лимита аккаунтов**: максимум 5 аккаунтов на один telegram_id
   ```sql
   SELECT COUNT(*) FROM tgplayers WHERE telegram_id=?
   ```

2. **Проверка уникальности логина**:
   ```sql
   SELECT 1 FROM users WHERE login=?
   ```

3. **Создание пользователя** (транзакция):
   ```sql
   INSERT INTO users(login, gender, email) VALUES(?,?,?);
   INSERT INTO tgplayers(telegram_id, username, login) VALUES(?,?,?);
   ```

4. **Регистрация на игровом сервере**:
   - Отправка команды через socket на game_server
   - Создание персонажа в игре

5. **Постановка в очередь** (опционально):
   - Добавление задачи в Redis для обработки worker'ом

### Архитектура
```
API 2 → api_father → db_bridge (mTLS) → MySQL gamedb.users + tgplayers
       ↓
       game_server (socket) - создание персонажа
       ↓
       Redis queue → worker (постобработка)
```

### Права доступа
- **Роль**: INSERT + SELECT
- **mTLS пользователь**: `api_register`
- **SQL операции**: 
  - `SELECT` на `users`, `tgplayers`
  - `INSERT` на `users`, `tgplayers`

### Валидация входных данных
- `login`: 3-16 символов, уникальный
- `password`: 6-20 символов
- `gender`: 0 (мужской) или 1 (женский)
- `telegram_id`: обязательное поле (bigint)
- `username`: опционально

### Ограничения
- Максимум 5 аккаунтов на один telegram_id
- Логин уникальный в системе
- Транзакционность: если game_server недоступен, откат в БД

### Порт
- **Внутренний**: 8082
- **Внешний**: доступ только через Traefik :1010

---

## Резюме

### API 1 (Server Status)
- **БД**: MySQL `gamedb`
- **Таблица**: `constants` (READ ONLY)
- **Поля**: Name, Value, Description
- **Роль**: Информационный (статус сервера, рейты)

### API 2 (Registration)
- **БД**: MySQL `gamedb`
- **Таблицы**: `users`, `tgplayers` (INSERT + SELECT)
- **Поля**: login, gender, telegram_id, username, created_at
- **Роль**: Регистрация новых игроков
- **Логика**: Проверка лимитов → вставка в БД → регистрация на game_server → очередь

