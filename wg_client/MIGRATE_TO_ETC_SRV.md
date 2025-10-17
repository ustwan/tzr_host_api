# 🔄 Миграция логов в /etc/srv/btl

## 🎯 Проблема

**Текущее состояние:**
- Логи хранятся в `/Users/ii/srv/btl/` (домашняя директория)
- Docker маунты указывают на `/Users/ii/srv/btl/`
- `/etc/srv/btl/` пустой

**Требуется:**
- Логи должны храниться в `/etc/srv/btl/` (системная директория)
- Docker маунты должны указывать на `/etc/srv/btl/`

---

## ✅ Решение

Создан скрипт `migrate_to_etc_srv.sh` который:

1. ✅ Создаёт `/etc/srv/btl/raw` и `/etc/srv/btl/gz`
2. ✅ Копирует существующие логи из `/Users/ii/srv/btl/` в `/etc/srv/btl/`
3. ✅ Обновляет все docker-compose файлы
4. ✅ Перезапускает контейнеры

---

## 🚀 Как запустить

```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client

# Сделать скрипт исполняемым
chmod +x migrate_to_etc_srv.sh

# Запустить миграцию
./migrate_to_etc_srv.sh
```

**Скрипт запросит sudo пароль** для:
- Создания `/etc/srv/btl/`
- Копирования файлов

---

## 📋 Что изменится

### Docker-compose файлы

**БЫЛО:**
```yaml
volumes:
  - /Users/ii/srv/btl:/srv/btl:rw
  - /Users/ii/srv/btl/raw:/srv/btl/raw
```

**СТАНЕТ:**
```yaml
volumes:
  - /etc/srv/btl:/srv/btl:rw
  - /etc/srv/btl/raw:/srv/btl/raw
```

**Изменённые файлы:**
- `HOST_API_SERVICE_HEAVY_WEIGHT_API.yml`
- `HOST_API_SERVICE_LIGHT_WEIGHT_API.yml`
- `HOST_API_SERVICE_XML_WORKERS.yml`

---

## 📊 После миграции

```bash
# Проверить файлы на хосте
ls -l /etc/srv/btl/raw
ls -l /etc/srv/btl/gz

# Должны быть такие же файлы как в:
ls -l /Users/ii/srv/btl/raw
ls -l /Users/ii/srv/btl/gz
```

**Старые файлы** в `/Users/ii/srv/btl/` можно будет удалить вручную после проверки.

---

## 🧪 Тестирование

После миграции:

```bash
# 1. Загрузить новые бои
curl -X POST 'http://localhost:8084/admin/xml-sync/fetch-old?count=10&from_battle_id=3780000'

# 2. Проверить что файлы сохранились в /etc/srv/btl/raw
ls /etc/srv/btl/raw/75/ | head -10

# 3. Спарсить через api_mother
curl -X POST 'http://localhost:8083/process-batch?limit=10&max_parallel=3'

# 4. Проверить что файлы переместились в /etc/srv/btl/gz
ls /etc/srv/btl/gz/75/ | head -10

# 5. Проверить storage_key в БД
curl -s 'http://localhost:8084/battle/3780000' | jq '{storage_key}'
# Должен быть: "/srv/btl/raw/75/3780000.tzb"
```

---

## ⚠️ Важно

1. **Скрипт требует sudo** для работы с `/etc/srv/btl/`
2. **Копирование может занять время** если логов много
3. **Контейнеры будут перезапущены** (downtime ~30 секунд)
4. **Старые файлы НЕ удаляются автоматически** - удалите вручную после проверки

---

## 🔍 Проверка что миграция прошла успешно

```bash
# 1. Проверить маунты в контейнерах
docker inspect host-api-service-api_4-1 | grep -A 3 '"Mounts"'

# Должно быть:
# "Source": "/etc/srv/btl"
# "Destination": "/srv/btl"

# 2. Проверить файлы в контейнере
docker exec host-api-service-api_4-1 ls /srv/btl/raw/75/ | head -5

# 3. Проверить файлы на хосте
ls /etc/srv/btl/raw/75/ | head -5

# Списки должны совпадать!
```

---

## 🆘 Откат миграции

Если что-то пошло не так:

```bash
# 1. Остановить контейнеры
cd /Users/ii/Documents/code/WG_HUB/wg_client
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml down
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml down
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml down

# 2. Вернуть старые маунты в docker-compose файлах
sed -i '' 's|/etc/srv/btl|/Users/ii/srv/btl|g' HOST_API_SERVICE_*.yml

# 3. Запустить контейнеры
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml up -d
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d
```

---

## 📝 Очистка старых файлов (после проверки)

**ТОЛЬКО после того, как убедитесь что всё работает:**

```bash
# Удалить старые логи (ОСТОРОЖНО!)
sudo rm -rf /Users/ii/srv/btl/raw
sudo rm -rf /Users/ii/srv/btl/gz
```

---

## ✅ Готово!

После успешной миграции логи будут храниться в:
- **На хосте:** `/etc/srv/btl/raw` и `/etc/srv/btl/gz`
- **В контейнерах:** `/srv/btl/raw` и `/srv/btl/gz`

**Запускайте скрипт:**
```bash
./migrate_to_etc_srv.sh
```





