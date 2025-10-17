# ✅ Интеграция новых метрик в ML детектор - ГОТОВО!

## 📊 **Что сделано:**

### **1. Добавлены новые фичи в BotDetector:**

| Фича | Описание | Значение для ботов |
|------|----------|-------------------|
| **ultra_short_ratio** | Доля интервалов < 0.5 сек | > 0.3 = БОТ! |
| **max_gap_hours** | Максимальный перерыв (часы) | < 0.5 = БОТ! |

---

## 🔧 **Изменения в коде:**

### **1. `_get_player_features` (строки 204-266):**

```python
# ДОБАВЛЕНО в SQL запрос:
-- НОВОЕ: Ультра-короткие интервалы (< 0.5 сек)
SUM(CASE WHEN gap_seconds <= 0.5 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(gap_seconds), 0) as ultra_short_ratio,
-- НОВОЕ: Максимальный разрыв
MAX(gap_seconds) / 3600.0 as max_gap_hours

# ДОБАВЛЕНО в features dict:
'ultra_short_ratio': float(result['ultra_short_ratio'] or 0),  # 0-1
'max_gap_hours': min(float(result['max_gap_hours'] or 24), 48),  # cap at 48 hours
```

### **2. `_explain_anomaly` (строки 268-300):**

```python
# НОВОЕ: Проверка ультра-коротких интервалов
ultra_short_ratio = features.get('ultra_short_ratio', 0)
if ultra_short_ratio > 0.3:
    reasons.append(f"🤖 Ботовые интервалы < 0.5 сек: {ultra_short_ratio:.1%}")
elif ultra_short_ratio > 0.1:
    reasons.append(f"⚠️ Много коротких интервалов < 0.5 сек: {ultra_short_ratio:.1%}")

# НОВОЕ: Проверка отсутствия перерывов
max_gap_hours = features.get('max_gap_hours', 24)
if max_gap_hours < 0.5:
    reasons.append(f"🤖 Нет перерывов (макс {max_gap_hours*60:.0f} минут)")
```

### **3. `train_bot_detector` (строки 303-403):**

```python
# ДОБАВЛЕНО в SQL запрос при обучении:
player_regularity AS (
    SELECT 
        player_id,
        STDDEV(gap_seconds) / NULLIF(AVG(gap_seconds), 0) as time_regularity,
        -- НОВОЕ: Ультра-короткие интервалы
        SUM(CASE WHEN gap_seconds <= 0.5 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(gap_seconds), 0) as ultra_short_ratio,
        -- НОВОЕ: Максимальный разрыв
        MAX(gap_seconds) / 3600.0 as max_gap_hours
    FROM player_gaps
    ...
)

# ДОБАВЛЕНО в features array:
features = [
    ... # старые фичи
    # НОВЫЕ ФИЧИ:
    float(r['ultra_short_ratio'] or 0),  # 0-1
    min(float(r['max_gap_hours'] or 24), 48),  # 0-48
]
```

---

## 📈 **Теперь ML детектор использует 10 фичей:**

| # | Фича | Старая/Новая | Важность |
|---|------|--------------|----------|
| 1 | pvp_ratio | Старая | Средняя |
| 2 | kpm | Старая | Средняя |
| 3 | survival_rate | Старая | Средняя |
| 4 | avg_kills_monsters | Старая | Низкая |
| 5 | avg_kills_players | Старая | Низкая |
| 6 | time_regularity | Старая | Высокая |
| 7 | location_diversity | Старая | Средняя |
| 8 | total_battles | Старая | Низкая |
| 9 | **ultra_short_ratio** | **НОВАЯ** | ⭐ **КРИТИЧЕСКАЯ!** |
| 10 | **max_gap_hours** | **НОВАЯ** | ⭐ **КРИТИЧЕСКАЯ!** |

---

## 🚀 **Как применить:**

### **Шаг 1: Перезапустить API 4**
```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client
docker restart host-api-service-api_4-1
```

### **Шаг 2: ПЕРЕОБУЧИТЬ модель (ОБЯЗАТЕЛЬНО!)**

⚠️ **ВАЖНО:** Старая модель обучена на 8 фичах, новая использует 10!

```bash
# Через Swagger UI:
open http://localhost:9107
# → API 4 → POST /ml/bot-detector/train

# Или через curl:
curl -X POST "http://localhost:8084/ml/bot-detector/train?days=90"
```

### **Шаг 3: Проверить результаты**
```bash
# Проверка кандидатов с новыми метриками:
curl "http://localhost:8084/analytics/antibot/candidates?days=7&limit=5"
```

---

## 📊 **Ожидаемый результат:**

### **БЫЛО (без новых метрик):**
```json
{
  "login": "Гельман",
  "is_bot": true,
  "reasons": [
    "K-means: стиль 'PvP новичок' подозрителен",
    "PvP < 5% (0.0%)",
    "KPM > 15 (43.6)",
    "SR > 95% (100.0%)"
  ]
}
```

### **СТАНЕТ (с новыми метриками):**

**Если обычный PvE игрок:**
```json
{
  "login": "Гельман",
  "is_bot": false,  // ИЗМЕНЕНО!
  "reasons": [
    "PvE игрок с естественными перерывами",
    "⚠️ Много коротких интервалов < 0.5 сек: 5%"  // Низкий процент
  ],
  "ultra_short_ratio": 0.05,
  "max_gap_hours": 2.5
}
```

**Если настоящий бот:**
```json
{
  "login": "Art-LA",
  "is_bot": true,
  "reasons": [
    "🤖 Ботовые интервалы < 0.5 сек: 35%",  // НОВОЕ!
    "🤖 Нет перерывов (макс 15 минут)",     // НОВОЕ!
    "Isolation Forest: аномальное поведение (score=-0.01)",
    "Экстремальный KPM: 30.0",
    "Очень высокий SR: 99.7%"
  ],
  "ultra_short_ratio": 0.35,
  "max_gap_hours": 0.25
}
```

---

## ✅ **Итог:**

1. ✅ **Новые метрики добавлены** в `bot_detector.py`
2. ✅ **SQL запросы обновлены** для извлечения `ultra_short_ratio` и `max_gap_hours`
3. ✅ **Объяснения аномалий** используют новые метрики
4. ⚠️ **ТРЕБУЕТСЯ ПЕРЕОБУЧЕНИЕ** модели после перезапуска API 4

**Теперь ML детектор различает PvE игроков и ботов по ВРЕМЕННЫМ ПАТТЕРНАМ!** 🎯





