# 📱 Проверка членства в Telegram группе при регистрации

## 🔍 Как это работает сейчас

### Логика проверки

При регистрации нового пользователя система **опционально** проверяет, состоит ли он в указанной Telegram группе.

**Файл:** `api_father/app/usecases/register_user.py` (строки 35-38)

```python
# Проверка членства в Telegram группе (если настроено)
if self._tg_checker is not None:
    if not await self._tg_checker.is_user_in_group(telegram_id):
        raise ValueError("not_in_group")
```

### Реализация проверки

**Файл:** `api_father/app/adapters/telegram_group_checker.py`

```python
async def is_user_in_group(self, telegram_id: int) -> bool:
    """
    Проверяет, состоит ли пользователь в требуемой группе через Telegram Bot API
    
    Использует метод getChatMember:
    https://api.telegram.org/bot<TOKEN>/getChatMember
    
    Параметры:
    - chat_id: ID группы/канала
    - user_id: telegram_id пользователя
    
    Возвращает True если статус: member, administrator, creator
    """
```

---

## ⚙️ Конфигурация

### Переменные окружения

Для работы проверки нужно установить **2 переменные окружения**:

1. **`TELEGRAM_BOT_TOKEN`** - токен Telegram бота
2. **`TELEGRAM_REQUIRED_GROUP_ID`** - ID группы/канала

### Текущее состояние

```bash
$ docker exec host-api-service-api_father-1 env | grep TELEGRAM
# Пусто - переменные НЕ установлены
```

**Вывод:** ✅ Проверка **ОТКЛЮЧЕНА** (по умолчанию)

---

## 🎯 Режимы работы

### 1. Проверка ОТКЛЮЧЕНА (текущий режим)

**Когда:** Переменные `TELEGRAM_BOT_TOKEN` или `TELEGRAM_REQUIRED_GROUP_ID` не установлены

**Поведение:**
```python
if not self.bot_token or not self.required_group_id:
    # Пропускаем проверку (для локальных тестов)
    return True
```

**Результат:** ✅ Все регистрации проходят без проверки группы

---

### 2. Проверка ВКЛЮЧЕНА

**Когда:** Обе переменные установлены

**Поведение:**
1. Запрос к Telegram Bot API: `getChatMember`
2. Проверка статуса пользователя в группе
3. Разрешенные статусы: `member`, `administrator`, `creator`
4. Если статус другой или пользователь не найден → **блокировка регистрации**

**Результат:** 
- ✅ Пользователь в группе → регистрация разрешена
- ❌ Пользователя нет в группе → ошибка `403 not_in_telegram_group`

---

## 🛠️ Как включить проверку

### Шаг 1: Создать Telegram бота

```bash
# В Telegram найдите @BotFather и создайте бота:
/newbot

# Получите токен (формат):
# 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### Шаг 2: Добавить бота в группу

1. Создайте Telegram группу (или используйте существующую)
2. Добавьте бота в группу как администратора (или обычного участника)
3. Получите ID группы:

```bash
# Вариант 1: Через @getidsbot
# Добавьте бота в группу и получите chat_id

# Вариант 2: Через Bot API
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"
# В ответе найдите chat.id вашей группы
```

**Формат ID группы:**
- Публичная группа: `@groupname`
- Приватная группа: `-1001234567890` (отрицательное число)
- Супергруппа: `-100` + цифры

### Шаг 3: Настроить переменные окружения

**Добавьте в `HOST_API_SERVICE.yml`:**

```yaml
services:
  api_father:
    environment:
      # ... существующие переменные
      - TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
      - TELEGRAM_REQUIRED_GROUP_ID=-1001234567890  # ID вашей группы
```

**Или через `.env` файл:**

```env
# .env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_REQUIRED_GROUP_ID=-1001234567890
```

### Шаг 4: Перезапустить api_father

```bash
docker compose -f HOST_API_SERVICE.yml restart api_father

# Проверка что переменные установлены
docker exec host-api-service-api_father-1 env | grep TELEGRAM
```

---

## 🧪 Тестирование

### Проверить что бот работает

```bash
# Замените YOUR_BOT_TOKEN на реальный токен
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getMe"

# Ожидается:
{
  "ok": true,
  "result": {
    "id": 1234567890,
    "is_bot": true,
    "first_name": "YourBot",
    "username": "yourbot"
  }
}
```

### Проверить доступ к группе

```bash
# Замените на ваши значения
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getChatMember?chat_id=YOUR_GROUP_ID&user_id=YOUR_TELEGRAM_ID"

# Успех (пользователь в группе):
{
  "ok": true,
  "result": {
    "user": {...},
    "status": "member"  // или "administrator", "creator"
  }
}

# Ошибка (не в группе):
{
  "ok": false,
  "error_code": 400,
  "description": "Bad Request: user not found"
}
```

### Тест регистрации

**Пользователь НЕ в группе:**
```bash
curl -X POST http://localhost:8090/api/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_api_key_12345" \
  -d '{
    "login": "Test",
    "password": "test123",
    "gender": 1,
    "telegram_id": 999999999
  }'

# Ожидается:
{
  "detail": "not_in_telegram_group"
}
# HTTP 403 Forbidden
```

**Пользователь В группе:**
```bash
# Та же команда с telegram_id пользователя который В группе
# Ожидается:
{
  "ok": true,
  "message": "Регистрация успешна!"
}
# HTTP 200 OK
```

---

## 🔧 Обработка ошибок

### В коде адаптера

```python
try:
    # Запрос к Telegram API
    ...
except Exception as e:
    # При ошибке API (сеть, таймаут) - НЕ блокируем регистрацию
    print(f"Warning: Telegram group check failed: {e}")
    return True  # пропускаем в случае ошибки
```

**Политика:** При технических ошибках (таймаут, сеть) регистрация **НЕ блокируется**

### Статус-коды

| Код | Причина | Решение |
|-----|---------|---------|
| 200 | Успех | Проверить статус пользователя |
| 400 | User not found | Пользователь не в группе |
| 401 | Unauthorized | Неверный bot token |
| 404 | Chat not found | Неверный group_id |

---

## 📋 Чеклист настройки

### Для включения проверки:

- [ ] Создан Telegram бот через @BotFather
- [ ] Получен bot token
- [ ] Бот добавлен в группу
- [ ] Получен ID группы
- [ ] Переменные `TELEGRAM_BOT_TOKEN` и `TELEGRAM_REQUIRED_GROUP_ID` установлены
- [ ] api_father перезапущен
- [ ] Проверен запрос `getMe` (бот работает)
- [ ] Проверен запрос `getChatMember` (доступ к группе есть)
- [ ] Протестирована регистрация (пользователь в группе)
- [ ] Протестирована регистрация (пользователь НЕ в группе)

### Для отключения проверки:

- [ ] Удалить переменные `TELEGRAM_BOT_TOKEN` и `TELEGRAM_REQUIRED_GROUP_ID`
- [ ] Перезапустить api_father
- [ ] Проверить что регистрация работает без проверки группы

---

## 💡 Рекомендации

### Development (локальная разработка)

**Рекомендация:** ✅ **Отключить** проверку

Причины:
- Упрощает тестирование
- Не нужны реальные Telegram ID
- Не зависит от внешних API

### Production (боевой сервер)

**Рекомендация:** ⚠️ **Включить** проверку

Причины:
- Защита от спама
- Контроль аудитории
- Возможность модерации через Telegram группу

### Безопасность токена

**⚠️ ВАЖНО:** Храните `TELEGRAM_BOT_TOKEN` в секрете!

```bash
# ❌ ПЛОХО - токен в коде
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHI

# ✅ ХОРОШО - токен в .env (не коммитить!)
# .env
TELEGRAM_BOT_TOKEN=реальный_токен

# .gitignore
.env
.env.local
```

---

## 🐛 Troubleshooting

### Проблема: "User not found"

**Причина:** Пользователь не состоит в группе

**Решение:** Пользователь должен сначала вступить в группу

---

### Проблема: "Chat not found"

**Причина:** Неверный `TELEGRAM_REQUIRED_GROUP_ID`

**Решение:** 
1. Проверьте ID группы через @getidsbot
2. Убедитесь что бот добавлен в группу
3. Для приватных групп используйте полный ID (`-100...`)

---

### Проблема: "Unauthorized"

**Причина:** Неверный `TELEGRAM_BOT_TOKEN`

**Решение:**
1. Проверьте токен через `getMe`
2. Убедитесь что токен скопирован полностью
3. Проверьте что нет лишних пробелов

---

### Проблема: Проверка не срабатывает

**Возможные причины:**

1. Переменные не установлены:
```bash
docker exec host-api-service-api_father-1 env | grep TELEGRAM
```

2. api_father не перезапущен после изменений:
```bash
docker compose -f HOST_API_SERVICE.yml restart api_father
```

3. Бот не в группе:
```bash
# Проверьте доступ бота к группе через getChatMember
```

---

## 📚 Полезные ссылки

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [getChatMember method](https://core.telegram.org/bots/api#getchatmember)
- [@BotFather](https://t.me/botfather) - создание ботов
- [@getidsbot](https://t.me/getidsbot) - получение ID

---

## 📊 Текущая конфигурация

```
Проверка Telegram группы: ❌ ОТКЛЮЧЕНА
Причина: Переменные TELEGRAM_BOT_TOKEN и TELEGRAM_REQUIRED_GROUP_ID не установлены
Поведение: Все регистрации проходят БЕЗ проверки членства в группе
```

**Чтобы включить проверку:** См. раздел "Как включить проверку" выше



