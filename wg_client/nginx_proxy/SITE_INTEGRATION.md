# 🌐 Интеграция с сайтом

## 📋 API Ключи

### Локальная разработка

**Dev API Key (для тестирования):**
```
dev_api_key_12345
```

Этот ключ уже настроен в `nginx.dev.fixed.conf` и работает на `http://localhost:8090`

### Production

**Генерация PROD API ключа:**

```bash
# На HOST_SERVER
openssl rand -base64 32

# Пример вывода:
# Kq8xN7vZ+mP5jR2wT9yL3cV6bH4nM1sF8aG0dE7uI2o=
```

**Сохранение ключа:**

```bash
# На HOST_SERVER
sudo mkdir -p /root/.api_keys
echo "ВАШ_СГЕНЕРИРОВАННЫЙ_КЛЮЧ" | sudo tee /root/.api_keys/registration_api_key
sudo chmod 600 /root/.api_keys/registration_api_key

# Запомните этот ключ - он понадобится для сайта!
```

---

## 🎮 Доступные эндпоинты

### 1. Регистрация (POST, требует API Key)
- **URL:** `/api/register`
- **Метод:** POST
- **Auth:** Обязателен заголовок `X-API-Key`
- **Rate limit:** 10 запросов/минуту

### 2. Server Status (GET, публичный)
- **URL:** `/api/server/status`
- **Метод:** GET
- **Auth:** Не требуется
- **Rate limit:** 30 запросов/минуту
- **Описание:** Информация о статусе игрового сервера

---

## 🔧 Интеграция с сайтом (примеры кода)

### JavaScript / Fetch API

**Простой пример:**

```javascript
// API конфигурация
const API_CONFIG = {
    dev: {
        url: 'http://localhost:8090/api/register',
        apiKey: 'dev_api_key_12345'
    },
    prod: {
        url: 'https://api.yourdomain.com/api/register',
        apiKey: 'ВАШ_PROD_API_КЛЮЧ'  // Замените на реальный
    }
};

// Определяем окружение
const ENV = window.location.hostname === 'localhost' ? 'dev' : 'prod';
const config = API_CONFIG[ENV];

// Функция регистрации
async function registerUser(login, password, gender, telegramId, username = null) {
    try {
        const response = await fetch(config.url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': config.apiKey,
                'X-Request-Id': crypto.randomUUID()
            },
            body: JSON.stringify({
                login,
                password,
                gender,
                telegram_id: telegramId,
                username
            })
        });

        const data = await response.json();

        if (response.ok) {
            console.log('✅ Регистрация успешна:', data);
            return { success: true, data };
        } else {
            console.error('❌ Ошибка регистрации:', data);
            return { success: false, error: data };
        }
    } catch (error) {
        console.error('🔥 Сетевая ошибка:', error);
        return { success: false, error: error.message };
    }
}

// Использование регистрации
registerUser('ИгрокПро', 'mypass123', 1, 123456789, '@telegram_user')
    .then(result => {
        if (result.success) {
            alert('Регистрация прошла успешно!');
        } else {
            alert('Ошибка: ' + JSON.stringify(result.error));
        }
    });

// Получение статуса сервера (публичный, без API ключа)
async function getServerStatus() {
    try {
        const response = await fetch(config.url.replace('/register', '/server/status'), {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            console.log('✅ Статус сервера:', data);
            return { success: true, data };
        } else {
            console.error('❌ Ошибка получения статуса:', data);
            return { success: false, error: data };
        }
    } catch (error) {
        console.error('🔥 Сетевая ошибка:', error);
        return { success: false, error: error.message };
    }
}

// Использование
getServerStatus().then(result => {
    if (result.success) {
        console.log('Онлайн игроков:', result.data.online_players);
    }
});
```

**Расширенный пример с обработкой ошибок:**

```javascript
class RegistrationAPI {
    constructor(apiUrl, apiKey) {
        this.apiUrl = apiUrl;
        this.apiKey = apiKey;
    }

    async register(userData) {
        const requestId = crypto.randomUUID();
        
        try {
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey,
                    'X-Request-Id': requestId
                },
                body: JSON.stringify(userData)
            });

            const data = await response.json();

            // Обработка различных кодов ответа
            switch (response.status) {
                case 200:
                    return {
                        success: true,
                        message: 'Регистрация успешна!',
                        requestId,
                        data
                    };
                
                case 400:
                    return {
                        success: false,
                        error: 'validation_error',
                        message: this.getValidationMessage(data),
                        details: data
                    };
                
                case 403:
                    if (data.error === 'limit_exceeded') {
                        return {
                            success: false,
                            error: 'limit_exceeded',
                            message: 'Достигнут лимит аккаунтов (макс 5 на Telegram ID)'
                        };
                    } else if (data.error === 'not_in_telegram_group') {
                        return {
                            success: false,
                            error: 'not_in_group',
                            message: 'Необходимо вступить в Telegram группу'
                        };
                    }
                    break;
                
                case 409:
                    return {
                        success: false,
                        error: 'login_taken',
                        message: 'Этот логин уже занят'
                    };
                
                case 429:
                    return {
                        success: false,
                        error: 'rate_limit',
                        message: 'Слишком много запросов. Попробуйте позже'
                    };
                
                case 502:
                    return {
                        success: false,
                        error: 'server_unavailable',
                        message: 'Сервер временно недоступен'
                    };
                
                default:
                    return {
                        success: false,
                        error: 'unknown_error',
                        message: 'Произошла ошибка: ' + response.statusText
                    };
            }
        } catch (error) {
            return {
                success: false,
                error: 'network_error',
                message: 'Ошибка сети: ' + error.message
            };
        }
    }

    getValidationMessage(data) {
        if (data.fields) {
            const field = Object.keys(data.fields)[0];
            return `Ошибка в поле "${field}": ${data.fields[field]}`;
        }
        return data.message || 'Неверные данные';
    }
}

// Использование
const api = new RegistrationAPI(
    'http://localhost:8090/api/register',  // Dev
    'dev_api_key_12345'
);

// Пример вызова
async function handleRegistration(formData) {
    const result = await api.register({
        login: formData.login,
        password: formData.password,
        gender: formData.gender,
        telegram_id: formData.telegram_id,
        username: formData.username
    });

    if (result.success) {
        showSuccessMessage(result.message);
    } else {
        showErrorMessage(result.message);
    }
}
```

---

### PHP (curl)

```php
<?php

class RegistrationAPI {
    private $apiUrl;
    private $apiKey;

    public function __construct($apiUrl, $apiKey) {
        $this->apiUrl = $apiUrl;
        $this->apiKey = $apiKey;
    }

    public function register($login, $password, $gender, $telegramId, $username = null) {
        $data = [
            'login' => $login,
            'password' => $password,
            'gender' => $gender,
            'telegram_id' => $telegramId,
            'username' => $username
        ];

        $requestId = uniqid('req_', true);

        $ch = curl_init($this->apiUrl);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($data),
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'X-API-Key: ' . $this->apiKey,
                'X-Request-Id: ' . $requestId
            ],
            CURLOPT_TIMEOUT => 30,
            CURLOPT_CONNECTTIMEOUT => 10
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            return [
                'success' => false,
                'error' => 'network_error',
                'message' => 'Ошибка сети: ' . $error
            ];
        }

        $result = json_decode($response, true);

        switch ($httpCode) {
            case 200:
                return [
                    'success' => true,
                    'message' => 'Регистрация успешна!',
                    'data' => $result,
                    'request_id' => $requestId
                ];

            case 400:
                return [
                    'success' => false,
                    'error' => 'validation_error',
                    'message' => $result['message'] ?? 'Ошибка валидации данных'
                ];

            case 403:
                if (isset($result['detail']) && $result['detail'] === 'limit_exceeded') {
                    return [
                        'success' => false,
                        'error' => 'limit_exceeded',
                        'message' => 'Достигнут лимит аккаунтов (макс 5 на Telegram ID)'
                    ];
                }
                break;

            case 409:
                return [
                    'success' => false,
                    'error' => 'login_taken',
                    'message' => 'Этот логин уже занят'
                ];

            case 429:
                return [
                    'success' => false,
                    'error' => 'rate_limit',
                    'message' => 'Слишком много запросов. Попробуйте позже'
                ];

            default:
                return [
                    'success' => false,
                    'error' => 'unknown_error',
                    'message' => 'Ошибка сервера: HTTP ' . $httpCode
                ];
        }
    }
}

// Использование
$api = new RegistrationAPI(
    'http://localhost:8090/api/register',  // Dev
    'dev_api_key_12345'
);

$result = $api->register(
    'ИгрокПро',
    'mypass123',
    1,
    123456789,
    '@telegram_user'
);

if ($result['success']) {
    echo "✅ " . $result['message'];
} else {
    echo "❌ " . $result['message'];
}
?>
```

---

### Python (requests)

```python
import requests
import uuid
from typing import Dict, Any, Optional

class RegistrationAPI:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

    def register(
        self,
        login: str,
        password: str,
        gender: int,
        telegram_id: int,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """Регистрация пользователя"""
        
        data = {
            'login': login,
            'password': password,
            'gender': gender,
            'telegram_id': telegram_id,
            'username': username
        }

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
            'X-Request-Id': str(uuid.uuid4())
        }

        try:
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=30
            )

            result = response.json()

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Регистрация успешна!',
                    'data': result
                }
            elif response.status_code == 409:
                return {
                    'success': False,
                    'error': 'login_taken',
                    'message': 'Этот логин уже занят'
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'error': 'forbidden',
                    'message': 'Доступ запрещён'
                }
            elif response.status_code == 429:
                return {
                    'success': False,
                    'error': 'rate_limit',
                    'message': 'Слишком много запросов'
                }
            else:
                return {
                    'success': False,
                    'error': 'unknown',
                    'message': f'Ошибка: {response.status_code}'
                }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': 'network_error',
                'message': f'Ошибка сети: {str(e)}'
            }


# Использование
api = RegistrationAPI(
    api_url='http://localhost:8090/api/register',
    api_key='dev_api_key_12345'
)

result = api.register(
    login='ИгрокПро',
    password='mypass123',
    gender=1,
    telegram_id=123456789,
    username='@telegram_user'
)

if result['success']:
    print(f"✅ {result['message']}")
else:
    print(f"❌ {result['message']}")
```

---

## 🧪 Локальное тестирование

### 1. Убедитесь что nginx proxy запущен

```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client
docker compose -f nginx_proxy/docker-compose.yml ps

# Должен быть running
```

### 2. Тест с curl

```bash
# Health check
curl http://localhost:8090/api/register/health

# Регистрация с API ключом
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{
    "login": "ТестИгрок",
    "password": "test123456",
    "gender": 1,
    "telegram_id": 999999999
  }' | jq
```

### 3. Откройте тестовую страницу в браузере

```bash
# Откройте файл в браузере
open wg_client/nginx_proxy/test_page.html
```

Эта страница автоматически настроена на `http://localhost:8090` с API ключом `dev_api_key_12345`

### 4. Интеграция с вашим локальным сайтом

**Просто добавьте в ваш JS:**

```javascript
const API_URL = 'http://localhost:8090/api/register';
const API_KEY = 'dev_api_key_12345';

fetch(API_URL, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    },
    body: JSON.stringify({
        login: 'Test',
        password: 'test123',
        gender: 1,
        telegram_id: 123456789
    })
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## 🚀 Production деплой

### 1. На HOST_SERVER установите nginx

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y
```

### 2. Сгенерируйте PROD API ключ

```bash
# Генерируем секретный ключ
PROD_API_KEY=$(openssl rand -base64 32)
echo "Ваш PROD API ключ:"
echo "$PROD_API_KEY"

# СОХРАНИТЕ ЕГО! Понадобится для сайта
```

### 3. Настройте nginx

```bash
# Скопируйте продакшн конфиг
sudo cp nginx_proxy/nginx.prod.conf /etc/nginx/sites-available/api-proxy

# Отредактируйте конфиг
sudo nano /etc/nginx/sites-available/api-proxy
```

**Замените в конфиге:**

1. **`api.yourdomain.com`** → ваш домен
2. **`REPLACE_WITH_YOUR_SECRET_API_KEY_HERE`** → ваш сгенерированный PROD API ключ
3. **`https://yourwebsite.com`** → домен вашего сайта (для CORS)
4. **`server 10.8.0.2:80`** → IP вашего WG_CLIENT в VPN

### 4. Получите SSL сертификат

```bash
# Активируйте конфиг
sudo ln -s /etc/nginx/sites-available/api-proxy /etc/nginx/sites-enabled/

# Тест
sudo nginx -t

# Получите SSL
sudo certbot --nginx -d api.yourdomain.com

# Перезапуск
sudo systemctl restart nginx
```

### 5. Обновите конфиг сайта

**На вашем PROD сайте:**

```javascript
const API_URL = 'https://api.yourdomain.com/api/register';
const API_KEY = 'ВАШ_PROD_API_КЛЮЧ';  // Из шага 2

fetch(API_URL, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    },
    body: JSON.stringify({...})
})
```

### 6. Тест с PROD

```bash
# С любого публичного сервера
curl -X POST https://api.yourdomain.com/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ВАШ_PROD_API_КЛЮЧ" \
  -d '{
    "login": "ТестИгрок",
    "password": "test123456",
    "gender": 1,
    "telegram_id": 123456789
  }'
```

---

## 🔒 Безопасность

### ⚠️ ВАЖНО: Никогда не коммитьте API ключи в Git!

**Правильный подход:**

**`.env` файл на сервере:**
```bash
# На вашем сайте создайте .env
API_REGISTRATION_URL=https://api.yourdomain.com/api/register
API_REGISTRATION_KEY=ВАШ_СЕКРЕТНЫЙ_КЛЮЧ
```

**В коде используйте переменные окружения:**

```javascript
// Не делайте так:
const API_KEY = 'my_secret_key_123';  // ❌ ПЛОХО!

// Делайте так:
const API_KEY = process.env.API_REGISTRATION_KEY;  // ✅ ХОРОШО!
```

**PHP:**
```php
// Загружаем из .env
$apiKey = getenv('API_REGISTRATION_KEY');
```

---

## 📊 Мониторинг и логи

**Локально:**
```bash
# Real-time логи
docker compose -f nginx_proxy/docker-compose.yml logs -f

# Файлы логов
tail -f wg_client/nginx_proxy/logs/access.log
tail -f wg_client/nginx_proxy/logs/error.log
```

**Production:**
```bash
# Логи nginx
sudo tail -f /var/log/nginx/api-access.log
sudo tail -f /var/log/nginx/api-error.log

# Статистика
sudo awk '{print $9}' /var/log/nginx/api-access.log | sort | uniq -c | sort -rn
```

---

**Полная документация:** [README.md](README.md)

