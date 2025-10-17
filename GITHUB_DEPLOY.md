# 🚀 Деплой на GitHub

## ✅ Что сделано

1. ✅ Создана папка `govno_archive/` со старыми файлами
2. ✅ Подключен репозиторий https://github.com/ustwan/tzr_host_api
3. ✅ Обновлен `.gitignore`
4. ✅ Создан `QUICKSTART.md` - быстрый старт
5. ✅ Обновлен `README.md` - главная страница

## 📦 Что будет залито

```
tzr_host_api/
├── wg_client/              # Весь код проекта ✅
│   ├── api_1/ - api_5/    # API сервисы
│   ├── site_agent/        # WebSocket агент ⭐
│   ├── nginx_proxy/       # Публичный шлюз
│   └── *.yml              # Docker Compose
├── scripts/               # Утилиты ✅
├── README.md              # Главная ✅
├── QUICKSTART.md          # Быстрый старт ✅
├── MAIN_README.md         # Полная документация ✅
└── .gitignore             # Обновлен ✅
```

**НЕ будет залито (в .gitignore):**
- `govno_archive/` - старые файлы
- `.env`, секреты
- Данные (*.tzb, *.gz)
- Модели ML (*.pkl)

## 🚀 Команды для заливки

### Вариант 1: Первый раз (с полной историей)

```bash
cd /Users/ii/Documents/code/WG_HUB

# Добавить все файлы
git add .

# Коммит
git commit -m "Initial commit: TZR Host API v1.0

- Микросервисная архитектура (API 1-5)
- Site Agent для WebSocket связи с сайтом
- Clean Architecture
- ML/AI для детекции ботов
- Docker Compose конфигурации
- Полная документация"

# Залить (main ветка)
git push -u origin main
```

### Вариант 2: Свежий старт (без истории)

```bash
cd /Users/ii/Documents/code/WG_HUB

# Удалить старую историю
rm -rf .git

# Инициализировать заново
git init
git add .
git commit -m "Initial commit: TZR Host API v1.0"

# Подключить репозиторий
git remote add origin https://github.com/ustwan/tzr_host_api.git

# Залить (force, т.к. репозиторий пустой)
git branch -M main
git push -u origin main --force
```

## ⚠️ Перед заливкой проверить

```bash
# 1. Проверить что нет секретов
git status | grep -E "\.env$|secret|password|key"

# 2. Проверить размер репозитория
du -sh .git

# 3. Проверить .gitignore
cat .gitignore

# 4. Проверить что site_agent включен
ls -la wg_client/site_agent/
```

## 📋 Чеклист

- [x] Старые файлы в `govno_archive/`
- [x] Обновлен `.gitignore`
- [x] Создан `QUICKSTART.md`
- [x] Обновлен `README.md`
- [x] Подключен remote `origin`
- [ ] Проверены секреты (нет .env)
- [ ] Git add + commit
- [ ] Git push

## 🎯 После заливки

### 1. Проверить на GitHub

Перейти: https://github.com/ustwan/tzr_host_api

Убедиться что есть:
- ✅ README.md красиво отображается
- ✅ wg_client/ полностью залит
- ✅ site_agent/ присутствует
- ✅ QUICKSTART.md доступен

### 2. Клонировать и протестировать

```bash
# На чистой машине
git clone https://github.com/ustwan/tzr_host_api.git
cd tzr_host_api

# Следовать QUICKSTART.md
cat QUICKSTART.md
```

### 3. Настроить GitHub репозиторий

**Settings → General:**
- Description: "Микросервисная архитектура игрового сервера с WebSocket агентом"
- Website: (если есть)
- Topics: `python`, `docker`, `fastapi`, `clean-architecture`, `websocket`, `microservices`

**Settings → Security:**
- ✅ Включить Dependabot alerts
- ✅ Включить Secret scanning

## 🔐 Важно

**НЕ коммитить:**
- `.env` файлы
- Секреты (HMAC_SECRET, AES_GCM_KEY, JWT)
- Сертификаты (*.key, *.crt, *.pem)
- Данные (*.tzb, *.gz)
- Логи (*.log)

**Все секреты настраиваются через ENV на production сервере!**

## 📞 Если что-то пошло не так

### Откат коммита

```bash
# Если еще не запушили
git reset --soft HEAD~1

# Если уже запушили
git revert HEAD
git push
```

### Удалить случайно залитый файл из истории

```bash
# Удалить файл из истории (например .env)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch wg_client/.env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push
git push origin --force --all
```

---

**Готов к заливке!** 🚀

**Следующий шаг:** Выполнить команды из раздела "Команды для заливки"

