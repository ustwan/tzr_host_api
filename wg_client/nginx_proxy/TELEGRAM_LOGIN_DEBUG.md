# 🔍 Отладка Telegram Login

> Почему не работает авторизация через Telegram и не появляется форма регистрации

---

## 🐛 Описание проблемы

**Что происходит:**
1. Пользователь нажимает "Войти через Telegram"
2. Открывается окно авторизации Telegram
3. Окно **сразу закрывается**
4. Возвращает на ту же страницу с кнопкой
5. **Форма регистрации НЕ появляется**

---

## 🔄 Как ДОЛЖЕН работать Telegram Login

### Правильный flow:

```
1. Пользователь нажимает "Войти через Telegram"
   ↓
2. Открывается popup/redirect на oauth.telegram.org
   ↓
3. Telegram проверяет авторизацию:
   • Если авторизован в Telegram → сразу callback
   • Если НЕ авторизован → просит войти
   ↓
4. Пользователь разрешает доступ (или автоматически)
   ↓
5. Telegram возвращает данные на ваш сайт:
   • id (telegram_id)
   • first_name
   • last_name
   • username
   • photo_url
   • auth_date
   • hash (для проверки подлинности)
   ↓
6. Сайт сохраняет telegram_id в localStorage/sessionStorage
   ↓
7. Показывается форма регистрации персонажа:
   • Логин (input)
   • Пароль (input)
   • Пол персонажа (select)
   • telegram_id (скрыт, из localStorage)
   • username (скрыт, из Telegram данных)
   ↓
8. Пользователь заполняет форму и отправляет
   ↓
9. Запрос на API: POST /api/register
```

---

## ❌ Возможные причины проблемы

### 1. **Неправильный callback URL**

Telegram Login Widget требует **корректный домен** в настройках бота.

**Проблема:**
```javascript
// Если сайт на ngrok:
// https://abc123.ngrok-free.app

// А в настройках бота указан:
// https://yoursite.com
```

**Решение:**
```bash
# Обновить домен через @BotFather
/setdomain
# Указать: abc123.ngrok-free.app
```

---

### 2. **Popup блокируется браузером**

Браузер может блокировать popup окно Telegram.

**Проверка:**
- Откройте DevTools → Console
- Ищите: `"Popup blocked"` или `"Popup window was blocked"`

**Решение:**
```javascript
// Вместо popup используйте redirect
<script>
  function telegramLogin() {
    // Redirect вместо popup
    window.location.href = `https://oauth.telegram.org/auth?bot_id=YOUR_BOT_ID&origin=${window.location.origin}&request_access=write&return_to=${window.location.href}`;
  }
</script>
```

---

### 3. **Нет обработчика callback**

После авторизации Telegram возвращает данные, но сайт их не обрабатывает.

**Проблема:**
```javascript
// Telegram вернул данные в URL:
// https://yoursite.com/#id=312660736&first_name=John...

// Но НЕТ кода для обработки этих данных!
```

**Решение:**
```javascript
// При загрузке страницы проверяем URL hash
window.addEventListener('load', () => {
  // Проверяем данные из Telegram
  const hash = window.location.hash.substring(1);
  const params = new URLSearchParams(hash);
  
  if (params.has('id')) {
    const telegramData = {
      id: params.get('id'),
      first_name: params.get('first_name'),
      last_name: params.get('last_name'),
      username: params.get('username'),
      photo_url: params.get('photo_url'),
      auth_date: params.get('auth_date'),
      hash: params.get('hash')
    };
    
    // Сохраняем в localStorage
    localStorage.setItem('telegram_user', JSON.stringify(telegramData));
    
    // Показываем форму регистрации
    showRegistrationForm(telegramData);
    
    // Очищаем hash из URL
    window.history.replaceState(null, null, window.location.pathname);
  }
});

function showRegistrationForm(telegramData) {
  // Скрываем кнопку "Войти через Telegram"
  document.getElementById('telegram-login-btn').style.display = 'none';
  
  // Показываем форму
  document.getElementById('registration-form').style.display = 'block';
  
  // Заполняем скрытые поля
  document.getElementById('telegram_id').value = telegramData.id;
  document.getElementById('telegram_username').value = telegramData.username || '';
}
```

---

### 4. **Используется Telegram Login Widget, но нет data-onauth**

**Проблема:**
```html
<!-- Widget без обработчика -->
<script 
  async 
  src="https://telegram.org/js/telegram-widget.js?22" 
  data-telegram-login="YOUR_BOT_USERNAME" 
  data-size="large" 
  data-request-access="write">
</script>
<!-- НЕТ data-onauth! -->
```

**Решение:**
```html
<!-- С обработчиком -->
<script 
  async 
  src="https://telegram.org/js/telegram-widget.js?22" 
  data-telegram-login="YOUR_BOT_USERNAME" 
  data-size="large" 
  data-onauth="onTelegramAuth(user)"
  data-request-access="write">
</script>

<script>
  function onTelegramAuth(user) {
    console.log('Telegram user:', user);
    
    // Сохраняем данные
    localStorage.setItem('telegram_user', JSON.stringify(user));
    
    // Показываем форму регистрации
    showRegistrationForm(user);
  }
  
  function showRegistrationForm(user) {
    // Скрыть кнопку Telegram
    document.getElementById('telegram-section').style.display = 'none';
    
    // Показать форму
    document.getElementById('registration-form').style.display = 'block';
    
    // Заполнить поля
    document.getElementById('telegram_id').value = user.id;
    document.getElementById('telegram_username').value = user.username || '';
    
    // Показать приветствие
    document.getElementById('user-greeting').textContent = 
      `Привет, ${user.first_name}! Создайте персонажа:`;
  }
</script>
```

---

### 5. **CSP (Content Security Policy) блокирует iframe**

**Проблема:**
```
Content-Security-Policy: frame-src 'self'
// Блокирует iframe от telegram.org
```

**Решение:**
```html
<meta http-equiv="Content-Security-Policy" 
      content="frame-src 'self' https://oauth.telegram.org;">
```

---

## 🧪 Отладка

### Шаг 1: Откройте DevTools

```
F12 → Console
```

### Шаг 2: Проверьте ошибки

Ищите:
- ❌ `"Popup blocked"`
- ❌ `"CSP violation"`
- ❌ `"Refused to frame"`
- ❌ `"onTelegramAuth is not defined"`
- ❌ `"hash validation failed"`

### Шаг 3: Проверьте Network

```
F12 → Network → фильтр: oauth.telegram.org
```

Смотрите:
- ✅ Запрос на `oauth.telegram.org` успешен (200)
- ✅ В ответе есть данные пользователя
- ✅ Redirect обратно на ваш сайт

### Шаг 4: Проверьте localStorage

```javascript
// В Console:
localStorage.getItem('telegram_user')

// Должно вернуть:
// {"id":312660736,"first_name":"John",...}

// Если null - данные не сохранились!
```

### Шаг 5: Логирование

```javascript
// Добавьте логи везде
window.addEventListener('load', () => {
  console.log('Page loaded');
  console.log('Hash:', window.location.hash);
  console.log('localStorage:', localStorage.getItem('telegram_user'));
});

function onTelegramAuth(user) {
  console.log('onTelegramAuth called!');
  console.log('User data:', user);
  console.log('Telegram ID:', user.id);
}
```

---

## ✅ Рабочий пример (полный код)

### HTML:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Регистрация персонажа</title>
</head>
<body>

<!-- Секция 1: Авторизация через Telegram -->
<div id="telegram-section">
  <h1>Регистрация персонажа</h1>
  <p>Мы отказались от регистрации через email.</p>
  <p>Для регистрации необходимо войти через Telegram.</p>
  <p>Ваши персонажи будут привязаны к вашему аккаунту Telegram.</p>
  <p>Это быстро и безопасно.</p>
  
  <!-- Telegram Login Widget -->
  <script 
    async 
    src="https://telegram.org/js/telegram-widget.js?22" 
    data-telegram-login="tzr_ernest_bot"
    data-size="large" 
    data-onauth="onTelegramAuth(user)"
    data-request-access="write">
  </script>
  
  <p>После входа вы сможете создать персонажа для игры</p>
</div>

<!-- Секция 2: Форма регистрации персонажа (скрыта по умолчанию) -->
<div id="registration-form" style="display: none;">
  <h2 id="user-greeting">Создайте персонажа:</h2>
  
  <form id="character-form">
    <div>
      <label>Логин (3-16 символов):</label>
      <input type="text" id="login" required minlength="3" maxlength="16">
    </div>
    
    <div>
      <label>Пароль (6-20 символов):</label>
      <input type="password" id="password" required minlength="6" maxlength="20">
    </div>
    
    <div>
      <label>Пол персонажа:</label>
      <select id="gender" required>
        <option value="">-- Выберите --</option>
        <option value="0">Мужской</option>
        <option value="1">Женский</option>
      </select>
    </div>
    
    <!-- Скрытые поля -->
    <input type="hidden" id="telegram_id">
    <input type="hidden" id="telegram_username">
    
    <button type="submit">Создать персонажа</button>
  </form>
  
  <div id="result"></div>
</div>

<script>
  // Конфигурация API
  const API_CONFIG = {
    baseUrl: 'http://localhost:8090',  // Или ngrok URL
    apiKey: 'dev_api_key_12345'
  };

  // Обработчик Telegram авторизации
  function onTelegramAuth(user) {
    console.log('✅ Telegram авторизация успешна!');
    console.log('User data:', user);
    
    // Сохраняем данные пользователя
    localStorage.setItem('telegram_user', JSON.stringify(user));
    
    // Показываем форму регистрации
    showRegistrationForm(user);
  }

  // Показать форму регистрации
  function showRegistrationForm(user) {
    // Скрыть секцию Telegram
    document.getElementById('telegram-section').style.display = 'none';
    
    // Показать форму
    document.getElementById('registration-form').style.display = 'block';
    
    // Заполнить скрытые поля
    document.getElementById('telegram_id').value = user.id;
    document.getElementById('telegram_username').value = user.username || 'unknown';
    
    // Приветствие
    document.getElementById('user-greeting').textContent = 
      `Привет, ${user.first_name}! Создайте персонажа:`;
  }

  // Обработка формы регистрации
  document.getElementById('character-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const resultDiv = document.getElementById('result');
    resultDiv.textContent = 'Создание персонажа...';
    
    const formData = {
      login: document.getElementById('login').value.trim(),
      password: document.getElementById('password').value,
      gender: parseInt(document.getElementById('gender').value),
      telegram_id: parseInt(document.getElementById('telegram_id').value),
      username: document.getElementById('telegram_username').value
    };
    
    console.log('Отправка данных:', formData);
    
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
        document.getElementById('character-form').reset();
      } else {
        // Обработка ошибок
        let errorMsg = 'Ошибка регистрации';
        
        switch (data.detail) {
          case 'limit_exceeded':
            errorMsg = 'У вас уже 5 персонажей. Это максимум.';
            break;
          case 'login_taken':
            errorMsg = 'Этот логин уже занят. Выберите другой.';
            break;
          case 'not_in_telegram_group':
            errorMsg = 'Вступите в Telegram группу игры.';
            break;
          default:
            errorMsg = data.message || data.detail || 'Произошла ошибка';
        }
        
        resultDiv.innerHTML = `<span style="color: red;">❌ ${errorMsg}</span>`;
      }
      
    } catch (error) {
      console.error('Ошибка:', error);
      resultDiv.innerHTML = '<span style="color: red;">❌ Ошибка сети</span>';
    }
  });

  // При загрузке страницы проверяем есть ли сохраненные данные
  window.addEventListener('load', () => {
    const savedUser = localStorage.getItem('telegram_user');
    
    if (savedUser) {
      console.log('Найдены сохраненные данные Telegram');
      const user = JSON.parse(savedUser);
      showRegistrationForm(user);
    }
  });
</script>

</body>
</html>
```

---

## 🔧 Быстрые исправления

### Если popup блокируется:

```javascript
// Замените widget на кнопку с redirect
<button onclick="loginWithTelegram()">
  Войти через Telegram
</button>

<script>
  function loginWithTelegram() {
    const botUsername = 'tzr_ernest_bot';
    const currentUrl = window.location.href;
    window.location.href = `https://oauth.telegram.org/auth?bot_id=8303561821&origin=${window.location.origin}&embed=1&request_access=write&return_to=${encodeURIComponent(currentUrl)}`;
  }
</script>
```

### Если данные не сохраняются:

```javascript
// Проверка и отладка
console.log('localStorage доступен?', typeof(Storage) !== "undefined");
console.log('Данные:', localStorage.getItem('telegram_user'));

// Очистка (если нужно начать заново)
localStorage.removeItem('telegram_user');
```

---

## 📞 Чек-лист отладки

- [ ] Открыл DevTools → Console
- [ ] Нет ошибок при загрузке страницы
- [ ] Telegram widget загружен (iframe виден)
- [ ] Popup не блокируется браузером
- [ ] Функция `onTelegramAuth` определена
- [ ] После авторизации вызывается `onTelegramAuth`
- [ ] Данные сохраняются в `localStorage`
- [ ] Форма регистрации показывается
- [ ] `telegram_id` заполнен в скрытом поле
- [ ] Отправка формы работает
- [ ] API возвращает корректный ответ

---

## 🆘 Если ничего не помогает

Отправьте скриншоты:

1. **Console (F12)** - все ошибки
2. **Network (F12)** - запрос на `oauth.telegram.org`
3. **Application → LocalStorage** - содержимое
4. **HTML код** страницы с формой

Это поможет быстро найти проблему!

---

**Документация:**
- [Telegram Login Widget](https://core.telegram.org/widgets/login)
- [API регистрации](REGISTRATION_API_SPEC.md)
- [Обработка ошибок](ERROR_MESSAGES_FOR_SITE.md)



