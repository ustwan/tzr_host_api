# 📋 API Регистрации - Полная спецификация

> Детальное описание эндпоинта `/api/register` для регистрации новых игроков

---

## 📍 Эндпоинт

```
POST /api/register
```

**Доступ:**
- **Локально:** `http://localhost:8090/api/register`
- **Ngrok:** `https://your-ngrok-url.ngrok-free.app/api/register`
- **Production:** `https://api.yourdomain.com/api/register`

---

## 🔑 Аутентификация

**API ключ ОБЯЗАТЕЛЕН!**

### Заголовки:

```http
Content-Type: application/json
X-API-Key: dev_api_key_12345
```

| Заголовок | Обязательный | Значение (dev) | Значение (prod) |
|-----------|--------------|----------------|-----------------|
| `Content-Type` | ✅ Да | `application/json` | `application/json` |
| `X-API-Key` | ✅ Да | `dev_api_key_12345` | Ваш PROD ключ |
| `X-Request-Id` | ❌ Нет | UUID (опционально) | UUID (опционально) |

---

## 📥 Тело запроса (Request Body)

### JSON Schema:

```json
{
  "login": "string",
  "password": "string",
  "gender": 0 | 1,
  "telegram_id": integer,
  "username": "string" (optional)
}
```

### Детальное описание полей:

| Поле | Тип | Обязательное | Валидация | Описание |
|------|-----|--------------|-----------|----------|
| `login` | `string` | ✅ Да | `3-16` символов | Имя игрока (уникальное) |
| `password` | `string` | ✅ Да | `6-20` символов | Пароль для входа |
| `gender` | `integer` | ✅ Да | `0` или `1` | Пол персонажа: `0` = мужской, `1` = женский |
| `telegram_id` | `integer` | ✅ Да | Положительное число | ID пользователя Telegram |
| `username` | `string` | ❌ Нет | Любая строка | Имя пользователя в Telegram (опционально) |

### ⚠️ Важные ограничения:

1. **`login`:**
   - Минимум **3 символа**
   - Максимум **16 символов**
   - Должен быть **уникальным** (проверяется в БД)
   - Используется для входа в игру

2. **`password`:**
   - Минимум **6 символов**
   - Максимум **20 символов**
   - Передается на game server для создания аккаунта

3. **`gender`:**
   - Только `0` (мужской) или `1` (женский)
   - Определяет модель персонажа в игре

4. **`telegram_id`:**
   - Используется для:
     - Проверки членства в Telegram группе (если включено)
     - Лимита регистраций (максимум **5 аккаунтов** на 1 Telegram ID)
   - Получить можно через [@userinfobot](https://t.me/userinfobot)

5. **`username`:**
   - Опциональное поле
   - Сохраняется в БД для удобства (например, для отображения в админ-панели)

---

## ✅ Успешный ответ

### HTTP Status: `200 OK`

```json
{
  "ok": true,
  "message": "Регистрация успешна!",
  "request_id": "uuid-string-or-null"
}
```

### Что происходит при успешной регистрации:

1. ✅ Создается запись в БД (`MySQL → players`)
2. ✅ Создается связь `telegram_id ↔ player_id`
3. ✅ Отправляется команда на **game server** для создания аккаунта
4. ✅ (Опционально) Добавляется в очередь Redis для последующей обработки

---

## ❌ Коды ошибок

### Таблица всех возможных ошибок:

| HTTP Status | `detail` | Причина | Решение |
|-------------|----------|---------|---------|
| **400** | `Bad Request` | Невалидный JSON или не хватает обязательных полей | Проверьте структуру JSON |
| **400** | `bad_request` | Неизвестная ошибка валидации | Проверьте все поля на соответствие требованиям |
| **403** | `invalid_api_key` | API ключ отсутствует или неверный | Передайте корректный `X-API-Key` в заголовке |
| **403** | `limit_exceeded` | У пользователя уже **5 аккаунтов** | Удалите один из старых аккаунтов или используйте другой Telegram ID |
| **403** | `not_in_telegram_group` | Пользователь не состоит в обязательной Telegram группе | Вступите в группу и попробуйте снова |
| **409** | `login_taken` | Логин уже занят другим игроком | Выберите другой логин |
| **422** | Validation Error | Ошибка валидации полей (Pydantic) | См. детали ошибки в `detail` |
| **429** | Too Many Requests | Превышен лимит запросов (**10 req/min**) | Подождите минуту и попробуйте снова |
| **500** | `internal_error` | Внутренняя ошибка сервера | Обратитесь к администратору |
| **502** | `game_server error: ...` | Ошибка подключения к game server | Проверьте что game server доступен |
| **502** | `unexpected_error: ...` | Неожиданная ошибка | Обратитесь к администратору |
| **503** | `service unavailable` | Сервис временно недоступен | Попробуйте позже |

---

## 📝 Примеры ошибок (детально)

### 1️⃣ **400 Bad Request** - Невалидный JSON

**Запрос:**
```bash
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{invalid json'
```

**Ответ:**
```json
{
  "detail": "Bad Request"
}
```

---

### 2️⃣ **403 Forbidden** - Неверный API ключ

**Запрос:**
```bash
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: wrong_key" \
  -d '{...}'
```

**Ответ:**
```json
{
  "error": "invalid_api_key",
  "message": "API key is missing or invalid"
}
```

---

### 3️⃣ **403 Forbidden** - Лимит аккаунтов исчерпан

**Запрос:**
```json
{
  "login": "Player6",
  "password": "pass123",
  "gender": 0,
  "telegram_id": 123456789
}
```

**Ответ (если у `telegram_id: 123456789` уже есть 5 аккаунтов):**
```json
{
  "detail": "limit_exceeded"
}
```

**Причина:** 
- Каждому Telegram пользователю разрешено максимум **5 игровых аккаунтов**
- Это защита от спама и злоупотреблений

**Решение:**
- Удалите один из старых аккаунтов через админ-панель
- Или используйте другой Telegram аккаунт

---

### 4️⃣ **403 Forbidden** - Пользователь не в Telegram группе

**Запрос:**
```json
{
  "login": "NewPlayer",
  "password": "pass123",
  "gender": 1,
  "telegram_id": 999999999
}
```

**Ответ:**
```json
{
  "detail": "not_in_telegram_group"
}
```

**Причина:**
- Регистрация требует членства в Telegram группе
- Пользователь с `telegram_id: 999999999` не состоит в группе

**Решение:**
- Вступите в обязательную Telegram группу
- Подождите 1-2 минуты (кеш обновляется)
- Попробуйте снова

**Примечание:**
- Эта проверка **опциональна**
- Включается через `TELEGRAM_BOT_TOKEN` и `TELEGRAM_REQUIRED_GROUP_ID` в `.env`
- Подробнее: [TELEGRAM_GROUP_CHECK.md](TELEGRAM_GROUP_CHECK.md)

---

### 5️⃣ **409 Conflict** - Логин уже занят

**Запрос:**
```json
{
  "login": "ExistingPlayer",
  "password": "newpass",
  "gender": 0,
  "telegram_id": 111111111
}
```

**Ответ:**
```json
{
  "detail": "login_taken"
}
```

**Причина:**
- Логин `ExistingPlayer` уже зарегистрирован в БД

**Решение:**
- Выберите другой логин

---

### 6️⃣ **422 Unprocessable Entity** - Ошибка валидации

**Запрос (пароль слишком короткий):**
```json
{
  "login": "Player",
  "password": "123",
  "gender": 0,
  "telegram_id": 123456789
}
```

**Ответ:**
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 6 characters",
      "input": "123",
      "ctx": {
        "min_length": 6
      }
    }
  ]
}
```

**Другие примеры валидации:**

| Ошибка | Поле | Причина |
|--------|------|---------|
| `string_too_short` | `login` | Логин < 3 символов |
| `string_too_long` | `login` | Логин > 16 символов |
| `string_too_short` | `password` | Пароль < 6 символов |
| `string_too_long` | `password` | Пароль > 20 символов |
| `less_than_equal` | `gender` | `gender < 0` |
| `greater_than_equal` | `gender` | `gender > 1` |
| `int_parsing` | `telegram_id` | Не целое число |
| `missing` | `login` | Поле отсутствует |

---

### 7️⃣ **429 Too Many Requests** - Rate Limiting

**Запрос (11-й запрос за минуту):**
```bash
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{...}'
```

**Ответ:**
```json
{
  "detail": "Too Many Requests"
}
```

**Лимиты:**
- **10 запросов в минуту** с одного IP
- **Burst:** до 3 дополнительных запросов (всего 13)
- После превышения: блокировка на 1 минуту

**Решение:**
- Подождите 60 секунд
- Не отправляйте много запросов подряд

---

### 8️⃣ **502 Bad Gateway** - Ошибка game server

**Запрос:**
```json
{
  "login": "Player",
  "password": "pass123",
  "gender": 0,
  "telegram_id": 123456789
}
```

**Ответ:**
```json
{
  "detail": "game_server error: Connection refused"
}
```

**Причина:**
- Game server недоступен
- Неверные настройки подключения
- Сервер перегружен

**Решение:**
- Обратитесь к администратору
- Проверьте статус game server

---

## 🧪 Примеры запросов

### ✅ Минимальный корректный запрос

**cURL:**
```bash
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{
    "login": "Player1",
    "password": "mypass123",
    "gender": 0,
    "telegram_id": 123456789
  }'
```

**JavaScript (fetch):**
```javascript
fetch('http://localhost:8090/api/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'dev_api_key_12345'
  },
  body: JSON.stringify({
    login: 'Player1',
    password: 'mypass123',
    gender: 0,
    telegram_id: 123456789
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

**Python:**
```python
import requests

response = requests.post(
    'http://localhost:8090/api/register',
    headers={
        'Content-Type': 'application/json',
        'X-API-Key': 'dev_api_key_12345'
    },
    json={
        'login': 'Player1',
        'password': 'mypass123',
        'gender': 0,
        'telegram_id': 123456789
    }
)

print(response.json())
```

---

### ✅ Полный запрос (со всеми полями)

**cURL:**
```bash
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -H "X-Request-Id: $(uuidgen)" \
  -d '{
    "login": "Player1",
    "password": "mypass123",
    "gender": 1,
    "telegram_id": 123456789,
    "username": "@player1_tg"
  }'
```

**JavaScript (с генерацией UUID):**
```javascript
const requestId = crypto.randomUUID();

fetch('http://localhost:8090/api/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'dev_api_key_12345',
    'X-Request-Id': requestId
  },
  body: JSON.stringify({
    login: 'Player1',
    password: 'mypass123',
    gender: 1,
    telegram_id: 123456789,
    username: '@player1_tg'
  })
})
.then(async res => {
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail);
  }
  return res.json();
})
.then(data => {
  console.log('✅ Регистрация успешна!', data);
})
.catch(error => {
  console.error('❌ Ошибка:', error.message);
});
```

---

## 🔍 Обработка ошибок (Best Practices)

### JavaScript пример с полной обработкой:

```javascript
async function registerUser(login, password, gender, telegramId) {
  try {
    const response = await fetch('http://localhost:8090/api/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'dev_api_key_12345'
      },
      body: JSON.stringify({
        login,
        password,
        gender,
        telegram_id: telegramId
      })
    });

    const data = await response.json();

    // Проверка статуса
    if (response.ok) {
      return {
        success: true,
        message: data.message
      };
    }

    // Обработка разных ошибок
    switch (data.detail) {
      case 'invalid_api_key':
        return {
          success: false,
          message: 'Ошибка конфигурации. Обратитесь к администратору.'
        };

      case 'login_taken':
        return {
          success: false,
          message: 'Этот логин уже занят. Выберите другой.'
        };

      case 'limit_exceeded':
        return {
          success: false,
          message: 'Вы уже зарегистрировали максимальное количество аккаунтов (5).'
        };

      case 'not_in_telegram_group':
        return {
          success: false,
          message: 'Для регистрации нужно состоять в Telegram группе.'
        };

      default:
        // Валидация Pydantic (422)
        if (Array.isArray(data.detail)) {
          const errors = data.detail.map(err => err.msg).join(', ');
          return {
            success: false,
            message: `Ошибка валидации: ${errors}`
          };
        }

        return {
          success: false,
          message: `Ошибка: ${data.detail}`
        };
    }

  } catch (error) {
    return {
      success: false,
      message: 'Ошибка сети. Проверьте подключение.'
    };
  }
}

// Использование
const result = await registerUser('Player1', 'mypass123', 0, 123456789);

if (result.success) {
  alert(result.message);  // "Регистрация успешна!"
} else {
  alert(result.message);  // Сообщение об ошибке
}
```

---

## 📊 Workflow регистрации

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Клиент отправляет POST /api/register                    │
│    + JSON с login, password, gender, telegram_id            │
│    + X-API-Key в заголовке                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Nginx Proxy проверяет:                                   │
│    ✓ API ключ валидный?                                     │
│    ✓ Rate limit не превышен?                                │
│    ✓ CORS заголовки                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. API_Father (FastAPI) валидирует:                         │
│    ✓ JSON структура корректна?                              │
│    ✓ Все обязательные поля есть?                            │
│    ✓ Значения в допустимых пределах?                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Business Logic проверяет:                                │
│    ✓ Пользователь в Telegram группе? (если включено)        │
│    ✓ У telegram_id < 5 аккаунтов?                           │
│    ✓ Логин свободен?                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Создание аккаунта:                                       │
│    ✓ Запись в MySQL (players, telegram_players)             │
│    ✓ Отправка на game server (socket)                       │
│    ✓ (Опционально) Очередь Redis                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Ответ клиенту:                                           │
│    {"ok": true, "message": "Регистрация успешна!"}          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Как получить Telegram ID

### Метод 1: Используйте бота [@userinfobot](https://t.me/userinfobot)

1. Откройте Telegram
2. Найдите бота `@userinfobot`
3. Отправьте `/start`
4. Бот вернет ваш ID:

```
Id: 123456789
First: John
...
```

### Метод 2: Используйте JavaScript в Telegram Web App

```javascript
// В Telegram Mini App
const user = Telegram.WebApp.initDataUnsafe.user;
console.log(user.id);  // 123456789
```

### Метод 3: Получите через API

```bash
# Замените YOUR_BOT_TOKEN
curl https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

---

## 🧑‍💻 Интеграция на сайте (полный пример)

### HTML форма:

```html
<form id="registerForm">
  <input type="text" id="login" placeholder="Логин (3-16 символов)" required>
  <input type="password" id="password" placeholder="Пароль (6-20 символов)" required>
  
  <select id="gender" required>
    <option value="">-- Выберите пол --</option>
    <option value="0">Мужской</option>
    <option value="1">Женский</option>
  </select>
  
  <input type="number" id="telegram_id" placeholder="Telegram ID" required>
  <input type="text" id="username" placeholder="Telegram username (опционально)">
  
  <button type="submit">Зарегистрироваться</button>
</form>

<div id="result"></div>
```

### JavaScript обработка:

```javascript
const API_CONFIG = {
  baseUrl: 'http://localhost:8090',  // или ngrok URL
  apiKey: 'dev_api_key_12345'
};

document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const formData = {
    login: document.getElementById('login').value.trim(),
    password: document.getElementById('password').value,
    gender: parseInt(document.getElementById('gender').value),
    telegram_id: parseInt(document.getElementById('telegram_id').value),
    username: document.getElementById('username').value.trim() || undefined
  };
  
  const resultDiv = document.getElementById('result');
  resultDiv.textContent = 'Регистрация...';
  
  try {
    const response = await fetch(`${API_CONFIG.baseUrl}/api/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_CONFIG.apiKey
      },
      body: JSON.stringify(formData)
    });
    
    const data = await response.json();
    
    if (response.ok) {
      resultDiv.innerHTML = `<span style="color: green;">✅ ${data.message}</span>`;
      document.getElementById('registerForm').reset();
    } else {
      // Читаемые сообщения об ошибках
      const errorMessages = {
        'login_taken': 'Логин уже занят',
        'limit_exceeded': 'Достигнут лимит аккаунтов (5 на Telegram ID)',
        'not_in_telegram_group': 'Необходимо вступить в Telegram группу',
        'invalid_api_key': 'Ошибка конфигурации'
      };
      
      const errorMsg = errorMessages[data.detail] || data.detail;
      resultDiv.innerHTML = `<span style="color: red;">❌ ${errorMsg}</span>`;
    }
    
  } catch (error) {
    resultDiv.innerHTML = `<span style="color: red;">❌ Ошибка сети</span>`;
    console.error(error);
  }
});
```

---

## 📚 Связанная документация

- [Быстрый старт](QUICKSTART.md)
- [Production Setup](PRODUCTION_SETUP.md)
- [Ngrok тестирование](NGROK_TESTING.md)
- [Интеграция с сайтом](API_FOR_WEBSITE.md)
- [Telegram Group Check](TELEGRAM_GROUP_CHECK.md)
- [Список всех эндпоинтов](ENDPOINTS.md)

---

## ✅ Чеклист для разработчика

- [ ] Получил API ключ (`dev_api_key_12345` для локальной разработки)
- [ ] Знаю формат запроса (JSON с 4 обязательными полями)
- [ ] Добавил обработку всех кодов ошибок
- [ ] Протестировал с невалидными данными
- [ ] Протестировал rate limiting
- [ ] Добавил валидацию на фронте (3-16 символов для логина, 6-20 для пароля)
- [ ] Добавил проверку Telegram ID
- [ ] Создал читаемые сообщения об ошибках для пользователя
- [ ] Протестировал с ngrok (если сайт публичный)

---

**Вопросы?** См. [API_FOR_WEBSITE.md](API_FOR_WEBSITE.md) или обратитесь к администратору.



