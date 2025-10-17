# 🌐 API Документация для разработчика сайта

> **Для AI/разработчика сайта:** Этот документ содержит всю информацию для интеграции API регистрации и статуса сервера в ваш сайт.

---

## 📋 Оглавление

1. [Быстрый старт](#быстрый-старт)
2. [Доступные эндпоинты](#доступные-эндпоинты)
3. [Локальная разработка](#локальная-разработка)
4. [Production конфигурация](#production-конфигурация)
5. [Примеры кода](#примеры-кода)
6. [Обработка ошибок](#обработка-ошибок)
7. [Безопасность](#безопасность)

---

## ⚡ Быстрый старт

### Что нужно знать

У вас есть доступ к **2 эндпоинтам**:

1. **`POST /api/register`** - Регистрация пользователя (требует API ключ)
2. **`GET /api/server/status`** - Статус игрового сервера (публичный)

### Различия между окружениями

| Параметр | Локальная разработка | Production |
|----------|---------------------|------------|
| **Base URL** | `http://localhost:8090` | `https://api.yourdomain.com` |
| **API Key** | `dev_api_key_12345` | *Будет предоставлен отдельно* |
| **HTTPS** | ❌ Нет | ✅ Да |
| **CORS** | `*` (все домены) | Только домен сайта |

---

## 🎯 Доступные эндпоинты

### 1. Регистрация пользователя

**Endpoint:** `POST /api/register`

**Требования:**
- ✅ **Обязателен** заголовок `X-API-Key` с API ключом
- ✅ Content-Type: `application/json`
- ✅ Rate limit: 10 запросов/минуту с одного IP

**Request body:**
```json
{
  "login": "string",           // 3-16 символов, русские/английские буквы
  "password": "string",         // 6-20 ASCII символов
  "gender": 0 | 1,             // 0 = женский, 1 = мужской
  "telegram_id": number,        // Обязательное целое число
  "username": "string"          // Опционально, Telegram username
}
```

**Success Response (200):**
```json
{
  "ok": true,
  "message": "Регистрация успешна!",
  "request_id": "uuid"
}
```

**Error Responses:**

| Код | Причина | Описание |
|-----|---------|----------|
| 400 | Validation Error | Неверный формат данных (логин, пароль и т.д.) |
| 403 | Forbidden | API ключ неверный ИЛИ лимит аккаунтов (5 макс) ИЛИ не в Telegram группе |
| 409 | Conflict | Логин уже занят |
| 429 | Too Many Requests | Rate limit превышен |
| 502 | Bad Gateway | Сервер временно недоступен |

---

### 2. Статус сервера

**Endpoint:** `GET /api/server/status`

**Требования:**
- ❌ API ключ **НЕ требуется** (публичный эндпоинт)
- ✅ Rate limit: 30 запросов/минуту

**Success Response (200):**
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
    "ServerStatus": "1 = всем доступен сервер",
    "RateExp": "Опыт",
    "RatePvp": "ПВП",
    "RatePve": "ПВЕ",
    "RateColorMob": "x1",
    "RateSkill": "Скиллы",
    "CLIENT_STATUS": "статус"
  }
}
```

---

## 💻 Локальная разработка

### Конфигурация

```javascript
const API_CONFIG = {
  baseUrl: 'http://localhost:8090',
  apiKey: 'dev_api_key_12345'  // Dev API ключ
};
```

### Пример 1: Регистрация

```javascript
async function registerUser(userData) {
  try {
    const response = await fetch(`${API_CONFIG.baseUrl}/api/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_CONFIG.apiKey,
        'X-Request-Id': crypto.randomUUID() // Опционально, для трекинга
      },
      body: JSON.stringify({
        login: userData.login,
        password: userData.password,
        gender: userData.gender,
        telegram_id: userData.telegramId,
        username: userData.username || null
      })
    });

    const data = await response.json();

    if (response.ok) {
      return { success: true, data };
    } else {
      return { success: false, error: data, status: response.status };
    }
  } catch (error) {
    return { success: false, error: error.message, status: 0 };
  }
}

// Использование
const result = await registerUser({
  login: 'ИгрокПро',
  password: 'mypass123',
  gender: 1,
  telegramId: 999999999,
  username: '@telegram_user'
});

if (result.success) {
  console.log('✅ Регистрация успешна');
} else {
  console.error('❌ Ошибка:', result.error);
}
```

### Пример 2: Статус сервера

```javascript
async function getServerStatus() {
  try {
    const response = await fetch(`${API_CONFIG.baseUrl}/api/server/status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
        // API ключ НЕ требуется!
      }
    });

    const data = await response.json();

    if (response.ok) {
      return { success: true, data };
    } else {
      return { success: false, error: data };
    }
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Использование
const status = await getServerStatus();
if (status.success) {
  console.log('Статус сервера:', status.data.server_status);
  console.log('Рейты:', status.data.rates);
}
```

---

## 🚀 Production конфигурация

### Конфигурация

```javascript
const API_CONFIG = {
  baseUrl: 'https://api.yourdomain.com',  // Замените на реальный домен
  apiKey: 'PROD_API_KEY_WILL_BE_PROVIDED'  // Prod API ключ (будет предоставлен)
};
```

### ⚠️ Важные различия:

1. **HTTPS обязателен** - используйте `https://` в production
2. **API ключ другой** - не используйте dev ключ в production!
3. **CORS ограничен** - только с вашего домена сайта
4. **Rate limiting строже** - следите за количеством запросов

### Переключение между окружениями

```javascript
// Автоматическое определение окружения
const isDevelopment = window.location.hostname === 'localhost';

const API_CONFIG = isDevelopment 
  ? {
      baseUrl: 'http://localhost:8090',
      apiKey: 'dev_api_key_12345'
    }
  : {
      baseUrl: 'https://api.yourdomain.com',
      apiKey: process.env.REACT_APP_API_KEY  // Или из .env
    };
```

### Использование переменных окружения

**React (.env.local):**
```env
REACT_APP_API_BASE_URL=http://localhost:8090
REACT_APP_API_KEY=dev_api_key_12345
```

**React (код):**
```javascript
const API_CONFIG = {
  baseUrl: process.env.REACT_APP_API_BASE_URL,
  apiKey: process.env.REACT_APP_API_KEY
};
```

**Next.js (.env.local):**
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8090
NEXT_PUBLIC_API_KEY=dev_api_key_12345
```

**Next.js (код):**
```javascript
const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
  apiKey: process.env.NEXT_PUBLIC_API_KEY
};
```

---

## 📚 Примеры кода

### Полный класс API клиента

```javascript
class GameAPI {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async register(userData) {
    const response = await fetch(`${this.baseUrl}/api/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
        'X-Request-Id': crypto.randomUUID()
      },
      body: JSON.stringify(userData)
    });

    return this.handleResponse(response);
  }

  async getServerStatus() {
    const response = await fetch(`${this.baseUrl}/api/server/status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    return this.handleResponse(response);
  }

  async handleResponse(response) {
    const data = await response.json();

    if (response.ok) {
      return { success: true, data, status: response.status };
    }

    // Обработка специфичных ошибок
    const errorMap = {
      400: 'Неверные данные. Проверьте логин и пароль.',
      403: this.getError403Message(data),
      409: 'Этот логин уже занят',
      429: 'Слишком много запросов. Попробуйте позже.',
      502: 'Сервер временно недоступен'
    };

    return {
      success: false,
      error: errorMap[response.status] || 'Произошла ошибка',
      details: data,
      status: response.status
    };
  }

  getError403Message(data) {
    if (data.error === 'limit_exceeded') {
      return 'Достигнут лимит аккаунтов (максимум 5 на Telegram ID)';
    }
    if (data.error === 'not_in_telegram_group') {
      return 'Необходимо вступить в Telegram группу';
    }
    if (data.error === 'invalid_api_key') {
      return 'Неверный API ключ';
    }
    return 'Доступ запрещён';
  }
}

// Инициализация
const api = new GameAPI(
  'http://localhost:8090',
  'dev_api_key_12345'
);

// Использование
async function handleRegistration(formData) {
  const result = await api.register({
    login: formData.login,
    password: formData.password,
    gender: formData.gender === 'male' ? 1 : 0,
    telegram_id: parseInt(formData.telegramId),
    username: formData.username
  });

  if (result.success) {
    alert('Регистрация успешна!');
  } else {
    alert(`Ошибка: ${result.error}`);
  }
}
```

### React Hook

```javascript
import { useState, useEffect } from 'react';

const API_CONFIG = {
  baseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8090',
  apiKey: process.env.REACT_APP_API_KEY || 'dev_api_key_12345'
};

export function useServerStatus() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const response = await fetch(`${API_CONFIG.baseUrl}/api/server/status`);
        const data = await response.json();
        setStatus(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Обновлять каждые 30 сек

    return () => clearInterval(interval);
  }, []);

  return { status, loading, error };
}

export async function registerUser(userData) {
  const response = await fetch(`${API_CONFIG.baseUrl}/api/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_CONFIG.apiKey
    },
    body: JSON.stringify(userData)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Registration failed');
  }

  return response.json();
}

// Использование в компоненте
function ServerStatus() {
  const { status, loading, error } = useServerStatus();

  if (loading) return <div>Загрузка...</div>;
  if (error) return <div>Ошибка: {error}</div>;

  return (
    <div>
      <h3>Статус сервера</h3>
      <p>Статус: {status.server_status === 1 ? 'Онлайн' : 'Офлайн'}</p>
      <p>Рейт опыта: x{status.rates.exp}</p>
    </div>
  );
}
```

---

## ⚠️ Обработка ошибок

### Стратегия обработки ошибок

```javascript
async function safeApiCall(apiFunction) {
  try {
    const result = await apiFunction();
    
    if (result.success) {
      return result;
    }

    // Обработка бизнес-ошибок
    switch (result.status) {
      case 400:
        return { error: 'validation', message: 'Неверный формат данных' };
      case 403:
        if (result.details?.error === 'limit_exceeded') {
          return { error: 'limit', message: 'Лимит аккаунтов достигнут' };
        }
        if (result.details?.error === 'not_in_telegram_group') {
          return { error: 'telegram', message: 'Вступите в группу' };
        }
        return { error: 'forbidden', message: 'Доступ запрещён' };
      case 409:
        return { error: 'duplicate', message: 'Логин занят' };
      case 429:
        return { error: 'rate_limit', message: 'Слишком много запросов' };
      case 502:
        return { error: 'server', message: 'Сервер недоступен' };
      default:
        return { error: 'unknown', message: 'Неизвестная ошибка' };
    }
  } catch (error) {
    // Сетевые ошибки
    return { error: 'network', message: 'Ошибка сети: ' + error.message };
  }
}

// Использование
const result = await safeApiCall(() => api.register(userData));

if (result.error) {
  switch (result.error) {
    case 'validation':
      showValidationError(result.message);
      break;
    case 'limit':
      showLimitError(result.message);
      break;
    case 'duplicate':
      showDuplicateError(result.message);
      break;
    case 'rate_limit':
      showRateLimitError(result.message);
      break;
    case 'network':
      showNetworkError(result.message);
      break;
    default:
      showGenericError(result.message);
  }
} else {
  showSuccess('Регистрация успешна!');
}
```

### Валидация на клиенте (перед отправкой)

```javascript
function validateRegistrationData(data) {
  const errors = {};

  // Логин: 3-16 символов, русские/английские буквы, цифры, _, -, пробел
  const loginRegex = /^(?=.*[а-яА-ЯёЁa-zA-Z])[а-яА-ЯёЁa-zA-Z0-9_\-\s]{3,16}$/;
  if (!loginRegex.test(data.login)) {
    errors.login = 'Логин должен быть 3-16 символов (буквы, цифры, _, -, пробел)';
  }

  // Пароль: 6-20 ASCII символов
  const passwordRegex = /^[\x20-\x7E]{6,20}$/;
  if (!passwordRegex.test(data.password)) {
    errors.password = 'Пароль должен быть 6-20 символов (латиница)';
  }

  // Gender: 0 или 1
  if (![0, 1].includes(data.gender)) {
    errors.gender = 'Пол должен быть 0 (женский) или 1 (мужской)';
  }

  // Telegram ID: число
  if (!Number.isInteger(data.telegram_id) || data.telegram_id <= 0) {
    errors.telegram_id = 'Telegram ID должен быть положительным числом';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
}

// Использование
const validation = validateRegistrationData(formData);
if (!validation.isValid) {
  console.error('Ошибки валидации:', validation.errors);
  return;
}

// Данные валидны, отправляем на сервер
const result = await api.register(formData);
```

---

## 🔒 Безопасность

### ⚠️ КРИТИЧЕСКИ ВАЖНО

1. **НЕ коммитьте API ключи в Git!**
   ```javascript
   // ❌ ПЛОХО
   const API_KEY = 'prod_secret_key_12345';

   // ✅ ХОРОШО
   const API_KEY = process.env.REACT_APP_API_KEY;
   ```

2. **Используйте HTTPS в production!**
   ```javascript
   // ❌ ПЛОХО (production)
   const baseUrl = 'http://api.yourdomain.com';

   // ✅ ХОРОШО (production)
   const baseUrl = 'https://api.yourdomain.com';
   ```

3. **Храните API ключи в переменных окружения**
   ```env
   # .env.local (НЕ коммитить!)
   REACT_APP_API_KEY=your_secret_key_here
   ```

4. **Проверяйте данные на клиенте И на сервере**
   - Валидация на клиенте - для UX
   - Валидация на сервере - для безопасности

5. **Обрабатывайте rate limiting**
   ```javascript
   if (response.status === 429) {
     // Показать пользователю сообщение
     // Заблокировать кнопку на 1 минуту
     setTimeout(() => enableSubmitButton(), 60000);
   }
   ```

---

## 🧪 Тестирование

### Тестовые данные для локальной разработки

```javascript
const TEST_DATA = {
  validUser: {
    login: 'ТестИгрок',
    password: 'test123456',
    gender: 1,
    telegram_id: 999999999,
    username: '@test_user'
  },
  invalidLogin: {
    login: 'ab',  // Слишком короткий
    password: 'test123456',
    gender: 1,
    telegram_id: 999999999
  },
  invalidPassword: {
    login: 'ТестИгрок',
    password: '12345',  // Слишком короткий
    gender: 1,
    telegram_id: 999999999
  }
};
```

### Curl команды для тестирования

```bash
# Регистрация (с API ключом)
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{
    "login": "ТестИгрок",
    "password": "test123456",
    "gender": 1,
    "telegram_id": 999999999
  }'

# Статус сервера (без API ключа)
curl http://localhost:8090/api/server/status

# Тест без API ключа (должен вернуть 403)
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -d '{"login": "test"}'
```

---

## 📞 Поддержка

### Что делать если:

**❌ Ошибка CORS:**
- Проверьте что используете правильный домен
- В dev должно работать с любого домена
- В prod - только с домена сайта

**❌ 403 Invalid API Key:**
- Проверьте что передаете заголовок `X-API-Key`
- Убедитесь что используете правильный ключ для окружения

**❌ 429 Rate Limit:**
- Уменьшите частоту запросов
- Добавьте debounce на кнопки
- Кешируйте результаты (особенно server status)

**❌ 502 Bad Gateway:**
- Сервер временно недоступен
- Попробуйте позже
- Покажите пользователю понятное сообщение

---

## 📊 Чеклист интеграции

### Локальная разработка

- [ ] Nginx proxy запущен (`http://localhost:8090`)
- [ ] API ключ настроен (`dev_api_key_12345`)
- [ ] Тесты регистрации проходят
- [ ] Тесты server status проходят
- [ ] Обработка ошибок реализована
- [ ] Валидация на клиенте работает

### Production

- [ ] Production URL настроен (`https://api.yourdomain.com`)
- [ ] Production API ключ получен и настроен
- [ ] API ключ в переменных окружения (НЕ в коде!)
- [ ] HTTPS используется
- [ ] CORS настроен правильно
- [ ] Rate limiting учтён
- [ ] Error handling протестирован
- [ ] Логирование настроено

---

## 🎓 Примеры использования

### Минимальный пример (ванильный JS)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Регистрация</title>
</head>
<body>
    <form id="registerForm">
        <input id="login" placeholder="Логин" required>
        <input id="password" type="password" placeholder="Пароль" required>
        <input id="telegram_id" type="number" placeholder="Telegram ID" required>
        <button type="submit">Зарегистрироваться</button>
    </form>

    <div id="serverStatus"></div>

    <script>
        const API_URL = 'http://localhost:8090';
        const API_KEY = 'dev_api_key_12345';

        // Регистрация
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const response = await fetch(`${API_URL}/api/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': API_KEY
                },
                body: JSON.stringify({
                    login: document.getElementById('login').value,
                    password: document.getElementById('password').value,
                    gender: 1,
                    telegram_id: parseInt(document.getElementById('telegram_id').value)
                })
            });

            const data = await response.json();
            alert(response.ok ? 'Успех!' : 'Ошибка: ' + data.message);
        });

        // Статус сервера
        async function updateServerStatus() {
            const response = await fetch(`${API_URL}/api/server/status`);
            const data = await response.json();
            document.getElementById('serverStatus').textContent = 
                `Статус: ${data.server_status === 1 ? 'Онлайн' : 'Офлайн'}`;
        }

        updateServerStatus();
        setInterval(updateServerStatus, 30000);
    </script>
</body>
</html>
```

---

**Документ готов к использованию!** 🚀

Для вопросов см. полную документацию:
- [QUICKSTART.md](QUICKSTART.md)
- [SITE_INTEGRATION.md](SITE_INTEGRATION.md)
- [ENDPOINTS.md](ENDPOINTS.md)



