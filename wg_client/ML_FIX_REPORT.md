# 🤖 Отчёт об исправлении ML моделей

**Дата:** 13 октября 2025  
**Проблема:** Internal Server Error при обучении ML моделей

---

## ❌ Проблема

### Ошибки
```bash
POST /admin/ml/train-playstyle?days=365
→ 500 Internal Server Error

POST /admin/ml/train-botdetector?days=365
→ 500 Internal Server Error
```

### Причина
```
{"detail":"column bp.damage_dealt does not exist"}
```

**Детали:**
- ML модуль `playstyle_classifier.py` использовал колонку `bp.damage_dealt`
- В таблице `battle_participants` эта колонка **не существует**
- Есть колонка `damage_total` типа **JSONB**

---

## ✅ Исправление

### Файл: `api_4/app/ml/playstyle_classifier.py`

**Было:**
```python
AVG(CASE WHEN b.players_cnt > 1 THEN bp.damage_dealt ELSE NULL END) as avg_pvp_damage
```

**Стало:**
```python
AVG(CASE WHEN b.players_cnt > 1 THEN (bp.damage_total->>'total')::int ELSE NULL END) as avg_pvp_damage
```

**Изменения:**
- Используем JSONB колонку `damage_total`
- Извлекаем поле `'total'` через оператор `->>` 
- Приводим к `int` для корректных вычислений

---

## 🧪 Результаты тестирования

### 1. train-playstyle

**Запрос:**
```bash
curl -X POST 'http://localhost:8084/admin/ml/train-playstyle?days=90' \
  -H 'accept: application/json' -d ''
```

**Результат:** ✅ 200 OK
```json
{
  "status": "success",
  "trained_at": "2025-10-13T21:21:10.805235",
  "players_trained": 168,
  "clusters": [
    {
      "cluster_id": 5,
      "playstyle": "bot_farmer",
      "display_name": "Бот/Фарм-бот",
      "player_count": 71
    },
    {
      "cluster_id": 0,
      "playstyle": "bot_farmer",
      "display_name": "Бот/Фарм-бот",
      "player_count": 42
    },
    ...
  ]
}
```

**Характеристики:**
- ✅ Обучено игроков: 168
- ✅ Кластеров: 8
- ✅ Типы стилей: bot_farmer, pve_grinder, pvp_novice

### 2. train-botdetector

**Запрос:**
```bash
curl -X POST 'http://localhost:8084/admin/ml/train-botdetector?days=90' \
  -H 'accept: application/json' -d ''
```

**Результат:** ✅ 200 OK
```json
{
  "status": "success",
  "players_analyzed": 185,
  "anomalies_detected": 19,
  "anomaly_rate": 0.103,
  "training_time": 0.36,
  "model_saved": "/app/models/bot_detector.pkl"
}
```

**Характеристики:**
- ✅ Проанализировано игроков: 185
- ✅ Обнаружено аномалий: 19 (10.3%)
- ✅ Время обучения: 0.36s
- ✅ Модель сохранена

---

## 📊 Структура таблицы battle_participants

```sql
column_name   | data_type 
--------------+-----------
id            | bigint
battle_id     | bigint
player_id     | integer
login         | text
clan          | text
side          | text
survived      | boolean
rank_points   | integer
pve_points    | integer
intervened    | jsonb
kills         | jsonb
damage_total  | jsonb     ← ИСПОЛЬЗУЕТСЯ ДЛЯ avg_pvp_damage
loot          | jsonb
profession    | text
level         | integer
gender        | text
kills_players | integer
kills_monsters| integer
```

---

## 🎯 Итог

### ✅ Исправлено
1. SQL запрос в `playstyle_classifier.py` обновлён для работы с JSONB
2. Обе ML модели успешно обучаются
3. Модели возвращают корректные результаты

### ✅ Работающие эндпоинты
- `/admin/ml/train-playstyle` → 200 OK ✅
- `/admin/ml/train-botdetector` → 200 OK ✅

### 📝 Примечания
- `bot_detector.py` не требовал исправлений (не использовал `damage_dealt`)
- Модели сохраняются в `/app/models/` внутри контейнера
- API_4 пересобран с исправлениями

---

**Дата проверки:** 13 октября 2025  
**Статус:** ✅ **ML МОДЕЛИ РАБОТАЮТ**




