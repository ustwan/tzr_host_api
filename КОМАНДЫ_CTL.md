# 🎮 Все команды ctl.sh - Шпаргалка

## ⚡ Самые важные команды

### Обновить всё с GitHub и перезапустить

```bash
sudo bash tools/ctl.sh update
```

**Делает всё автоматически:**
1. Останавливает сервисы
2. Обновляет код с GitHub
3. Пересобирает образы
4. Запускает заново
5. Показывает статус

### Полная переустановка (если что-то сломалось)

```bash
sudo bash tools/ctl.sh fresh-start
```

**Делает:**
1. Останавливает и удаляет всё (включая volumes)
2. Пересобирает образы
3. Запускает заново

⚠️ **Удалит тестовые данные!**

---

## 🚀 Запуск

```bash
# Запустить всё (API без WG_HUB)
sudo bash tools/ctl.sh start-all

# Запустить ВСЁ (API + WG_HUB)
sudo bash tools/ctl.sh start-full

# Запустить в PROD режиме
sudo bash tools/ctl.sh start-prod

# Запустить в TEST режиме
sudo bash tools/ctl.sh start-test

# Запустить с Site Agent
sudo bash tools/ctl.sh start-with-agent
```

---

## 🛑 Остановка

```bash
# Остановить всё (данные сохранятся)
sudo bash tools/ctl.sh stop-all

# Остановить и удалить (включая volumes)
sudo bash tools/ctl.sh down-all
```

---

## 🔧 Управление отдельными сервисами

### WG_HUB (VPN)

```bash
sudo bash tools/ctl.sh wg-hub              # Запустить
sudo bash tools/ctl.sh wg-hub-stop         # Остановить
sudo bash tools/ctl.sh wg-hub-logs         # Логи
sudo bash tools/ctl.sh wg-hub-status       # Статус
sudo bash tools/ctl.sh wg-hub-ui           # URL админки
```

### Site Agent

```bash
sudo bash tools/ctl.sh site-agent          # Запустить
sudo bash tools/ctl.sh site-agent-logs     # Логи
sudo bash tools/ctl.sh site-agent-restart  # Перезапустить
```

### API сервисы

```bash
# Перезапустить конкретный API
sudo bash tools/ctl.sh restart api_father
sudo bash tools/ctl.sh restart api_2
sudo bash tools/ctl.sh restart api_4

# Логи конкретного API
sudo bash tools/ctl.sh logs api_father
sudo bash tools/ctl.sh logs api_2
```

---

## 🔄 Обновление и пересборка

```bash
# Обновить с GitHub и перезапустить ВСЁ (одна команда!)
sudo bash tools/ctl.sh update

# Только пересборка образов
sudo bash tools/ctl.sh rebuild

# Быстрая пересборка только API
sudo bash tools/ctl.sh rebuild-api

# Полная переустановка (осторожно!)
sudo bash tools/ctl.sh fresh-start
```

---

## 📊 Мониторинг

```bash
# Статус всех контейнеров
sudo bash tools/ctl.sh status

# Логи всех сервисов
sudo bash tools/ctl.sh logs

# Логи конкретного сервиса
sudo bash tools/ctl.sh logs api_father

# Диагностика
sudo bash tools/ctl.sh doctor

# Проверка сетей
sudo bash tools/ctl.sh networks
```

---

## 🗄️ База данных

```bash
# Применить миграции
sudo bash tools/ctl.sh migrate
```

---

## 🧹 Очистка

```bash
# Очистить неиспользуемые образы/volumes
sudo bash tools/ctl.sh prune
```

---

## 🎯 Типичные сценарии

### Первый запуск на сервере

```bash
cd /mnt/docker/tzr_host_api/wg_client
sudo cp env.example .env
sudo bash tools/ctl.sh start-full
sudo bash tools/ctl.sh status
```

### Обновление после изменений в коде

```bash
cd /mnt/docker/tzr_host_api/wg_client
sudo bash tools/ctl.sh update
```

**Одна команда - всё обновится и перезапустится!**

### Что-то сломалось - полная переустановка

```bash
cd /mnt/docker/tzr_host_api/wg_client
sudo bash tools/ctl.sh fresh-start
```

### Перезапустить упавший сервис

```bash
sudo bash tools/ctl.sh logs api_4  # Посмотреть ошибку
sudo bash tools/ctl.sh restart api_4  # Перезапустить
```

### Доступ к VPN админке

```bash
sudo bash tools/ctl.sh wg-hub-ui
# Покажет URL: http://172.16.16.117:2019
```

---

## 📋 Полный список команд

| Команда | Что делает |
|---------|------------|
| `start-all` | Запустить все API |
| `start-full` | Запустить ВСЁ (API + VPN) |
| `start-prod` | PROD режим |
| `start-test` | TEST режим |
| `stop-all` | Остановить всё |
| `status` | Статус контейнеров |
| `logs` | Логи всех/конкретного |
| `restart [svc]` | Перезапуск сервиса |
| **`update`** | ⭐ **Обновить с GitHub** |
| **`rebuild`** | Пересобрать образы |
| **`fresh-start`** | Чистая установка |
| `wg-hub` | Запустить VPN |
| `wg-hub-ui` | URL админки VPN |
| `site-agent` | Запустить агента |
| `migrate` | Миграции БД |
| `doctor` | Диагностика |

---

## 🎯 ГЛАВНАЯ КОМАНДА

**Для обновления всего проекта:**

```bash
sudo bash tools/ctl.sh update
```

**Всё остальное делается автоматически!** 🚀

---

## 🌐 Доступ из VPN

После подключения к VPN (`http://172.16.16.117:2019`):

```
http://10.8.0.1:9107   - Swagger
http://10.8.0.1:9100   - Portainer
http://10.8.0.1:1010   - Traefik
http://10.8.0.1:8082   - API_2
http://10.8.0.1:9000   - API_Father
```

**По IP VPN интерфейса (10.8.0.1), а не локальному IP!** ✅

