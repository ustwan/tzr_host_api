# 🚨 Сообщения об ошибках для сайта

> Правильные сообщения для каждого кода ошибки API регистрации

---

## ⚠️ ВАЖНО!

API возвращает **коды ошибок** в поле `detail`.  
Сайт должен **правильно интерпретировать** каждый код и показать понятное сообщение пользователю.

---

## 📋 Таблица ошибок

| HTTP | `detail` | Что произошло | Сообщение для пользователя |
|------|----------|---------------|----------------------------|
| **403** | `limit_exceeded` | У пользователя уже 5 аккаунтов | **"У вас уже зарегистрировано 5 аккаунтов. Это максимум на один Telegram ID."** |
| **403** | `not_in_telegram_group` | Пользователь не состоит в Telegram группе | **"Для регистрации нужно вступить в Telegram группу игры."** |
| **403** | `invalid_api_key` | API ключ неверный или отсутствует | **"Ошибка доступа. Обратитесь к администратору."** |
| **409** | `login_taken` | Логин уже занят другим игроком | **"Этот логин уже занят. Выберите другой."** |
| **400** | `validation_error` | Неверное заполнение полей | **"Проверьте правильность заполнения полей."** |
| **422** | Массив ошибок | Ошибки валидации Pydantic | См. `detail[]` для деталей |
| **429** | - | Слишком много запросов | **"Слишком много попыток. Подождите минуту и попробуйте снова."** |
| **500** | `internal_error` | Внутренняя ошибка сервера | **"Произошла ошибка сервера. Попробуйте позже."** |
| **502** | `game_server_error...` | Игровой сервер недоступен | **"Игровой сервер временно недоступен. Попробуйте позже."** |

---

## 💻 Готовый код для JavaScript

### Вариант 1: Объект с сообщениями

```javascript
const ERROR_MESSAGES = {
  // 403 Forbidden
  'limit_exceeded': 'У вас уже зарегистрировано 5 аккаунтов. Это максимум на один Telegram ID.',
  'not_in_telegram_group': 'Для регистрации нужно вступить в Telegram группу игры.',
  'invalid_api_key': 'Ошибка доступа. Обратитесь к администратору.',
  
  // 409 Conflict
  'login_taken': 'Этот логин уже занят. Выберите другой.',
  
  // 400 Bad Request
  'validation_error': 'Проверьте правильность заполнения полей.',
  'bad_request': 'Некорректные данные. Проверьте все поля.',
  
  // 500/502 Server Errors
  'internal_error': 'Произошла ошибка сервера. Попробуйте позже.',
  
  // Default
  'default': 'Произошла ошибка. Попробуйте снова или обратитесь к администратору.'
};

// Использование
function getErrorMessage(errorCode) {
  return ERROR_MESSAGES[errorCode] || ERROR_MESSAGES['default'];
}
```

### Вариант 2: Полная обработка с кодами HTTP

```javascript
async function register(login, password, gender, telegramId) {
  try {
    const response = await fetch('/api/register', {
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

    // Успешная регистрация
    if (response.ok) {
      return {
        success: true,
        message: data.message || 'Регистрация успешна!'
      };
    }

    // Обработка ошибок
    let errorMessage;

    switch (response.status) {
      case 403:
        switch (data.detail) {
          case 'limit_exceeded':
            errorMessage = 'У вас уже зарегистрировано 5 аккаунтов. Это максимум на один Telegram ID.';
            break;
          case 'not_in_telegram_group':
            errorMessage = 'Для регистрации нужно вступить в Telegram группу игры.';
            break;
          case 'invalid_api_key':
            errorMessage = 'Ошибка доступа. Обратитесь к администратору.';
            break;
          default:
            errorMessage = 'Доступ запрещен.';
        }
        break;

      case 409:
        errorMessage = 'Этот логин уже занят. Выберите другой.';
        break;

      case 400:
        if (data.error === 'validation_error' && data.fields) {
          // Показываем конкретные ошибки полей
          const fieldErrors = Object.values(data.fields).join('. ');
          errorMessage = fieldErrors;
        } else {
          errorMessage = 'Проверьте правильность заполнения полей.';
        }
        break;

      case 422:
        // Ошибки валидации Pydantic
        if (Array.isArray(data.detail)) {
          const errors = data.detail.map(err => err.msg).join('. ');
          errorMessage = errors;
        } else {
          errorMessage = 'Проверьте правильность заполнения полей.';
        }
        break;

      case 429:
        errorMessage = 'Слишком много попыток. Подождите минуту и попробуйте снова.';
        break;

      case 500:
      case 502:
      case 503:
        errorMessage = 'Сервер временно недоступен. Попробуйте позже.';
        break;

      default:
        errorMessage = data.detail || 'Произошла ошибка. Попробуйте снова.';
    }

    return {
      success: false,
      message: errorMessage
    };

  } catch (error) {
    return {
      success: false,
      message: 'Ошибка сети. Проверьте подключение к интернету.'
    };
  }
}

// Использование
const result = await register('Player', 'pass123', 0, 312660736);

if (result.success) {
  showSuccess(result.message);
} else {
  showError(result.message);
}
```

---

## 🎨 Рекомендации по UI/UX

### 1. Разные типы уведомлений для разных ошибок

```javascript
function showNotification(type, message) {
  switch (type) {
    case 'limit_exceeded':
    case 'not_in_telegram_group':
      // Показываем INFO (можно исправить)
      showInfoNotification(message, {
        action: type === 'not_in_telegram_group' 
          ? 'Вступить в группу' 
          : 'Удалить старый аккаунт'
      });
      break;

    case 'login_taken':
      // Показываем WARNING (нужно изменить логин)
      showWarningNotification(message, {
        focusField: 'login'
      });
      break;

    case 'validation_error':
      // Показываем ERROR у конкретных полей
      showFieldErrors(message);
      break;

    default:
      // Общая ошибка
      showErrorNotification(message);
  }
}
```

### 2. Помощь пользователю

```javascript
const ERROR_HELP = {
  'limit_exceeded': {
    message: 'У вас уже зарегистрировано 5 аккаунтов.',
    help: 'Удалите один из старых аккаунтов через профиль или обратитесь к администратору.',
    canRetry: false
  },
  
  'not_in_telegram_group': {
    message: 'Для регистрации нужно вступить в Telegram группу игры.',
    help: 'Вступите в группу и попробуйте снова через минуту.',
    action: {
      text: 'Открыть группу',
      url: 'https://t.me/your_game_group'
    },
    canRetry: true
  },
  
  'login_taken': {
    message: 'Этот логин уже занят.',
    help: 'Попробуйте добавить цифры или символы к логину.',
    canRetry: true
  }
};
```

---

## ❌ Типичные ошибки на сайте

### ❌ НЕПРАВИЛЬНО:

```javascript
// Плохо: одно сообщение для всех ошибок
if (!response.ok) {
  alert('Ошибка регистрации');
}

// Плохо: неверная интерпретация кодов
if (data.detail === 'limit_exceeded') {
  alert('Вступите в группу'); // ← НЕПРАВИЛЬНО!
}

// Плохо: показываем техническую ошибку
alert(data.detail); // "limit_exceeded" ← непонятно пользователю
```

### ✅ ПРАВИЛЬНО:

```javascript
// Хорошо: разные сообщения для разных ошибок
if (data.detail === 'limit_exceeded') {
  showError('У вас уже 5 аккаунтов. Это максимум.');
}

// Хорошо: понятные сообщения
const userMessage = ERROR_MESSAGES[data.detail] || 'Ошибка';
showError(userMessage);

// Хорошо: помощь пользователю
showErrorWithHelp(userMessage, helpText, canRetryAction);
```

---

## 🧪 Тестирование обработки ошибок

Протестируйте каждый код ошибки:

```bash
# 1. Лимит аккаунтов (зарегистрируйте 5 аккаунтов, затем 6-й)
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{"login":"Test1", "password":"pass123", "gender":0, "telegram_id":312660736}'

# 2. Занятый логин (используйте существующий логин)
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{"login":"ExistingLogin", "password":"pass123", "gender":0, "telegram_id":999999}'

# 3. Неверный API ключ
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: wrong_key" \
  -d '{"login":"Test", "password":"pass123", "gender":0, "telegram_id":999999}'

# 4. Короткий пароль (валидация)
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{"login":"Test", "password":"123", "gender":0, "telegram_id":999999}'
```

Убедитесь что **каждая ошибка** показывает **правильное** сообщение!

---

## 📚 См. также

- [Полная спецификация API](REGISTRATION_API_SPEC.md) - все коды ошибок
- [Краткий справочник](ERROR_CODES_QUICK_REF.md) - таблица кодов
- [Интеграция с сайтом](API_FOR_WEBSITE.md) - примеры кода

---

## ✅ Чеклист для разработчика

- [ ] Создал объект `ERROR_MESSAGES` с правильными сообщениями
- [ ] Обрабатываю каждый код ошибки отдельно
- [ ] Показываю понятные сообщения пользователю (не технические коды)
- [ ] Для ошибок валидации показываю какие поля неверны
- [ ] Даю пользователю подсказки как исправить ошибку
- [ ] Тестировал все типы ошибок
- [ ] Логирую ошибки в консоль для отладки

---

**Помните:** Хорошая обработка ошибок = хороший UX! 🎯



