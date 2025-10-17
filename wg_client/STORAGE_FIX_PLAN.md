# 🔧 План централизации хранилища логов

## ❌ ПРОБЛЕМА

Логи боёв разбросаны по разным путям:

### Текущая архитектура (ХАОС):
```
1. XML Workers    → /Users/ii/srv/btl/raw → /srv/btl_raw
2. api_mother     → /Users/ii/srv/btl/raw → /srv/btl/raw
                  → /Users/ii/srv/btl/gz → /srv/btl/gz
3. api_mother (2) → ./xml/gz → /srv/btl_store/gz (дубликат!)
4. API_4          → /Users/ii/srv/btl → /srv/btl (read-only)
5. Старая система → ./xml/mirror → /srv/btl_mirror
```

**Проблемы:**
- XML Workers сохраняют в `/srv/btl_raw` (не `/srv/btl/raw`)
- api_mother имеет 2 монтирования для gz-файлов
- Разные контейнеры видят разные пути
- Нет централизованного хранилища

---

## ✅ РЕШЕНИЕ: Централизация в `/Users/ii/srv/btl`

### Целевая структура:
```
/Users/ii/srv/btl/
├── raw/        # Сырые .tzb файлы от XML Workers
│   ├── 0/      # Шарды по battle_id % 1000
│   ├── 1/
│   └── ...
└── gz/         # Сжатые .gz файлы от api_mother
    ├── 0/
    ├── 1/
    └── ...
```

### Маунты для всех сервисов:
```yaml
xml_worker_1..6:
  volumes:
    - /Users/ii/srv/btl/raw:/srv/btl/raw  # ✅ Единый путь

api_mother:
  volumes:
    - /Users/ii/srv/btl:/srv/btl:rw       # ✅ Один маунт для raw и gz
  environment:
    - LOGS_RAW=/srv/btl/raw
    - LOGS_STORE=/srv/btl/gz

api_4:
  volumes:
    - /Users/ii/srv/btl:/srv/btl:ro       # ✅ Read-only доступ
```

---

## 📝 НЕОБХОДИМЫЕ ИЗМЕНЕНИЯ

### 1. XML Worker (`xml_worker/app/main.py`)
```python
# БЫЛО:
output_dir = "/srv/btl_raw"

# ДОЛЖНО БЫТЬ:
output_dir = "/srv/btl/raw"
```

### 2. XML Workers Docker Compose (`HOST_API_SERVICE_XML_WORKERS.yml`)
```yaml
# БЫЛО:
volumes:
  - /Users/ii/srv/btl/raw:/srv/btl_raw

# ДОЛЖНО БЫТЬ:
volumes:
  - /Users/ii/srv/btl/raw:/srv/btl/raw
```

### 3. api_mother Docker Compose (`HOST_API_SERVICE_LIGHT_WEIGHT_API.yml`)
```yaml
# УБРАТЬ дубликат:
# - ${LOGS_STORE:-./xml/gz}:/srv/btl_store/gz  # ❌ УДАЛИТЬ

# ОСТАВИТЬ ТОЛЬКО:
volumes:
  - /Users/ii/srv/btl:/srv/btl:rw  # ✅
environment:
  - LOGS_RAW=/srv/btl/raw
  - LOGS_STORE=/srv/btl/gz
```

### 4. API_4 (уже правильно)
```yaml
volumes:
  - /Users/ii/srv/btl:/srv/btl:ro  # ✅ OK
```

---

## 🚀 МИГРАЦИЯ

### Шаг 1: Создать структуру
```bash
mkdir -p /Users/ii/srv/btl/raw
mkdir -p /Users/ii/srv/btl/gz
```

### Шаг 2: Перенести существующие файлы (если есть)
```bash
# Из старых мест в новые
mv /Users/ii/srv/btl_raw/* /Users/ii/srv/btl/raw/ 2>/dev/null || true
mv ./xml/gz/* /Users/ii/srv/btl/gz/ 2>/dev/null || true
```

### Шаг 3: Применить изменения
1. Обновить `xml_worker/app/main.py`
2. Обновить `HOST_API_SERVICE_XML_WORKERS.yml`
3. Обновить `HOST_API_SERVICE_LIGHT_WEIGHT_API.yml`
4. Пересобрать контейнеры

### Шаг 4: Перезапуск
```bash
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml down
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml down api_mother
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml down api_4

# Rebuild
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml build
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml build api_mother

# Start
docker compose -f HOST_API_SERVICE_XML_WORKERS.yml up -d
docker compose -f HOST_API_SERVICE_LIGHT_WEIGHT_API.yml up -d api_mother
docker compose -f HOST_API_SERVICE_HEAVY_WEIGHT_API.yml up -d api_4
```

---

## ✅ РЕЗУЛЬТАТ

После миграции:
- ✅ Все логи в `/Users/ii/srv/btl/{raw,gz}`
- ✅ Единые пути для всех контейнеров
- ✅ Нет дубликатов маунтов
- ✅ Легко бэкапить: `rsync -av /Users/ii/srv/btl/ backup/`
- ✅ Прозрачная работа api_mother: raw → gz
- ✅ API_4 видит все файлы






