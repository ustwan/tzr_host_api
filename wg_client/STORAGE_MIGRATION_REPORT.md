# 📦 Отчёт о миграции хранилища

## ✅ Что сделано

### 1. Централизация хранилища
- **Новое расположение:** `./data/btl/` (в корне проекта)
- **Структура:**
  - `./data/btl/raw/` - временные .tzb файлы (после парсинга → удаляются)
  - `./data/btl/gz/` - постоянное хранилище .tzb.gz (сжатие ~10x)

### 2. Обновлены Docker Compose файлы
Все сервисы используют единый маппинг: `./data/btl → /srv/btl`

- ✅ `HOST_API_SERVICE_XML_WORKERS.yml`: `./data/btl/raw:/srv/btl/raw`
- ✅ `HOST_API_SERVICE_HEAVY_WEIGHT_API.yml`: `./data/btl:/srv/btl:rw`
- ✅ `HOST_API_SERVICE_LIGHT_WEIGHT_API.yml`: `./data/btl:/srv/btl:rw`

### 3. Исправлены пути в коде
**Удалены устаревшие пути:**
- ❌ `/home/zero/logs/btl` → ✅ `/srv/btl/raw`
- ❌ `/srv/btl_mirror` → ✅ `/srv/btl/raw`
- ❌ `/Users/ii/srv/btl` → ✅ `./data/btl`
- ❌ `/etc/srv/btl` → ✅ `./data/btl`

**Файлы с исправлениями:**
- `api_4/app/interfaces/http/routes.py`
- `api_4/app/xml_sync_worker.py`

### 4. Исправлен `/battle/{id}/raw`
**Новый приоритет поиска:**
1. `/srv/btl/gz/{shard}/{battle_id}.tzb.gz` ← **ОСНОВНОЕ ХРАНИЛИЩЕ**
2. `/srv/btl/raw/{shard}/{battle_id}.tzb` ← Временное (если ещё не сжато)
3. `storage_key` из БД
4. GZ-версия `storage_key` (raw → gz)

**Разархивация на лету:**
```python
if cand.endswith('.gz'):
    with gzip.open(cand, 'rb') as f:
        data = f.read()  # ← В памяти
```

### 5. Права доступа
```bash
chmod -R 2775 ./data/btl  # БЕЗ sudo! ✅
```

### 6. `.gitignore` создан
Данные не попадут в Git:
```
./data/.gitignore
```

---

## 📊 Статистика

### Текущее состояние:
- **RAW файлов:** 47,543 (4.9GB)
- **GZ файлов:** 31,839 (317MB)
- **Сжатие:** ~15x меньше размер

### Процесс миграции:
- ✅ Все файлы перенесены из `/Users/ii/srv/btl/` → `./data/btl/`
- 🔄 Идёт сжатие RAW → GZ (параллельно, 8 потоков)
- ✅ Старые папки удалены

---

## 🔧 Архитектура хранения

```
┌─────────────────────────────────────┐
│  1. XML Workers                     │
│     Скачивают → /srv/btl/raw/       │
│     (маппится на ./data/btl/raw/)   │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  2. api_mother/process-batch        │
│     • Парсит через API_4            │
│     • Сжимает → /srv/btl/gz/        │
│     • УДАЛЯЕТ из /srv/btl/raw/ ✅   │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  3. Постоянное хранилище            │
│     /srv/btl/gz/{shard}/ID.tzb.gz   │
│     (./data/btl/gz/ на хосте)       │
│     Размер: ~317MB (сжатие x15)     │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  4. API /battle/{id}/raw            │
│     • Ищет .gz файл                 │
│     • gzip.decompress() в памяти    │
│     • Возвращает XML                │
└─────────────────────────────────────┘
```

---

## ✅ Проверка эндпоинтов

### Работают:
- ✅ `/healthz` - Health check
- ✅ `/docs` - Swagger UI
- ✅ `/analytics/stats` - Общая статистика
- ✅ `/analytics/battles/player/{login}` - История игрока
- ✅ `/analytics/meta/balance` - Баланс мета
- ✅ `/analytics/meta/professions` - Статистика профессий
- ✅ `/analytics/players/top` - Топ игроков
- ✅ `/battle/{id}` - Метаданные боя
- ✅ `/battle/{id}/raw` - RAW XML (из GZ!)
- ✅ `/analytics/time/activity-heatmap` - Тепловая карта активности
- ✅ `/analytics/time/peak-hours` - Пиковые часы
- ✅ `/analytics/map/heatmap` - Карта боёв

### Требуют доработки:
- ⚠️ `/players/by-profession` - Ошибка 400 (требуется проверка параметров)
- ⚠️ `/battle/search` - Ошибка 405 (POST → GET?)

---

## 📝 Следующие шаги

1. **Дождаться завершения сжатия** RAW → GZ (~47K файлов)
2. **Очистить RAW папку** после полного сжатия
3. **Проверить storage_key в БД** (должны указывать на `/srv/btl/`)
4. **Исправить проблемные эндпоинты** (2 штуки)

---

## 🎯 Итог

### ✅ Достигнуто:
- Единое хранилище в проекте: `./data/btl/`
- Никаких sudo-прав
- Сжатие x15 (экономия места)
- API читает GZ на лету
- Все пути централизованы

### 📦 Размер данных:
- **Было:** 4.9GB (RAW) + 317MB (GZ) = 5.2GB
- **Будет:** ~500MB (только GZ после сжатия всех файлов)
- **Экономия:** ~4.7GB! 🎉

---

**Дата:** 13 октября 2025  
**Версия:** 3.3




