# 🤖 Улучшение определения вероятности бота

## 📊 Текущая система

### Voting Ensemble (K-means + Isolation Forest)

**Текущие confidence (фиксированные):**
```python
if kmeans_bot and if_anomaly:
    confidence = 0.95  # Оба метода согласны
elif kmeans_bot:
    confidence = 0.75  # Только K-means
elif if_anomaly:
    confidence = 0.70  # Только Isolation Forest
else:
    confidence = 0.0   # Не бот
```

**Проблема:** Все игроки в категории получают одинаковый score!

---

## ✅ Предлагаемые улучшения

### 1. Динамический bot_probability (0-100%)

**Комбинируем существующие метрики:**

```python
def calculate_bot_probability(self, features, kmeans_result=None):
    """
    Динамический расчёт вероятности бота (0-100%)
    
    Использует:
    - Isolation Forest anomaly score
    - K-means bot_score
    - Индивидуальные признаки
    """
    
    # 1. Isolation Forest score (нормализуем к 0-1)
    if_score = self.if_model.decision_function(features)[0]
    # decision_function: negative = anomaly, positive = normal
    # Нормализуем: score < -0.1 = высокая аномальность
    if_probability = max(0, min(1, (-if_score - 0.05) / 0.2))
    
    # 2. K-means bot_score (уже 0-1)
    kmeans_probability = 0
    if kmeans_result:
        kmeans_probability = kmeans_result.get('bot_detection', {}).get('bot_score', 0)
    
    # 3. Критические признаки (ультра-короткие интервалы)
    ultra_short_ratio = features.get('ultra_short_ratio', 0)
    critical_probability = 0
    if ultra_short_ratio > 0.5:
        critical_probability = 0.95  # 95% - явный бот
    elif ultra_short_ratio > 0.3:
        critical_probability = 0.70  # 70% - подозрителен
    elif ultra_short_ratio > 0.1:
        critical_probability = 0.40  # 40% - возможен
    
    # 4. Взвешенная комбинация
    weights = {
        'critical': 0.50,      # Ультра-короткие интервалы - главный признак
        'isolation_forest': 0.30,  # Аномальность поведения
        'kmeans': 0.20         # Стиль игры
    }
    
    bot_probability = (
        critical_probability * weights['critical'] +
        if_probability * weights['isolation_forest'] +
        kmeans_probability * weights['kmeans']
    )
    
    # Ограничиваем 0-100%
    return round(bot_probability * 100, 1)
```

---

### 2. Детальная классификация

**Вместо бинарного is_bot:**

```json
{
  "player_id": 12345,
  "bot_probability": 87.5,  // 0-100%
  "classification": "high_risk_bot",  // low/medium/high_risk_bot или clean
  "confidence_level": "very_high",  // low/medium/high/very_high
  
  "detection_breakdown": {
    "critical_indicators": 0.95,  // Ультра-короткие интервалы
    "anomaly_score": 0.82,        // Isolation Forest
    "playstyle_score": 0.85,      // K-means
    "weighted_score": 0.875       // Итоговый
  },
  
  "risk_factors": [
    {
      "factor": "ultra_short_intervals",
      "severity": "critical",
      "value": 0.62,  // 62% боёв с интервалом < 0.5 сек
      "impact": 50    // Вклад в итоговый score (%)
    },
    {
      "factor": "extreme_kpm",
      "severity": "high",
      "value": 45.3,  // KPM
      "impact": 15
    },
    {
      "factor": "no_breaks",
      "severity": "high",
      "value": 0.2,   // Макс перерыв 0.2 часа
      "impact": 15
    }
  ],
  
  "reasons": [
    "🔴 КРИТИЧНО: 62% боёв с интервалом < 0.5 сек (ботовая активность)",
    "🟠 Экстремальный KPM: 45.3 (норма 5-15)",
    "🟠 Нет перерывов > 12 минут",
    "🟡 Очень высокий survival rate: 98.7%"
  ]
}
```

---

### 3. Гибкие пороги детекции

```python
# Классификация по probability
if bot_probability >= 85:
    classification = "high_risk_bot"      # Почти точно бот
    confidence_level = "very_high"
elif bot_probability >= 70:
    classification = "medium_risk_bot"    # Вероятный бот
    confidence_level = "high"
elif bot_probability >= 50:
    classification = "low_risk_bot"       # Подозрительный
    confidence_level = "medium"
else:
    classification = "clean"              # Обычный игрок
    confidence_level = "low"
```

---

## 🎯 Дополнительные признаки для улучшения

### Текущие признаки (10):
1. `pvp_ratio` - Доля PvP боёв
2. `kpm` - Убийств за минуту
3. `survival_rate` - Выживаемость
4. `avg_kills_monsters` - Среднее убийств монстров
5. `avg_kills_players` - Среднее убийств игроков
6. `time_regularity` - Регулярность игры
7. `location_diversity` - Разнообразие локаций
8. `total_battles` - Общее количество боёв
9. ✅ `ultra_short_ratio` - **КРИТИЧНО! Интервалы < 0.5 сек**
10. ✅ `max_gap_hours` - Максимальный перерыв

### Возможные дополнения:

11. **`action_diversity`** - Разнообразие действий в бою
    ```sql
    COUNT(DISTINCT (bp.kills->>'type')) / NULLIF(COUNT(*), 0)
    ```

12. **`loot_pattern`** - Паттерн сбора лута (боты собирают всё)
    ```sql
    AVG(jsonb_array_length(bp.loot)) as avg_loot_items
    ```

13. **`movement_variance`** - Вариативность перемещений по карте
    ```sql
    STDDEV(b.loc_x) + STDDEV(b.loc_y) as movement_variance
    ```

14. **`session_length_std`** - Стандартное отклонение длины сессий
    ```sql
    STDDEV(session_duration) / AVG(session_duration)
    ```

15. **`day_of_week_variance`** - Играет ли в разные дни недели
    ```sql
    COUNT(DISTINCT EXTRACT(DOW FROM b.ts))
    ```

---

## 💡 Предложение реализации

### Вариант 1: Быстрое улучшение (30 минут)
- Использовать `decision_function` для динамического scoring
- Комбинировать с `bot_score` из K-means
- Вернуть процент 0-100%

### Вариант 2: Полное обновление (2-3 часа)
- Добавить 5 новых признаков
- Обучить нейросеть (вместо Isolation Forest)
- Калибровка вероятностей
- Детальная breakdown по каждому признаку

### Вариант 3: Экспертная система (5+ часов)
- Правила на основе признаков (if-then)
- Веса для каждого признака
- Fuzzy logic для неопределённых случаев
- Объяснимость каждого решения

---

## 🚀 Рекомендация

**Начать с Варианта 1:**

1. ✅ Уже есть `decision_function` (аномальность)
2. ✅ Уже есть `bot_score` из K-means
3. ✅ Уже есть `ultra_short_ratio` (критичный признак)

**Достаточно:**
- Нормализовать `if_score` к 0-1
- Взвесить все 3 метрики
- Вернуть точный % (0-100)

**Пример:**
```python
bot_probability = (
    ultra_short_ratio * 50 +     # 0-50%
    if_normalized * 30 +          # 0-30%
    kmeans_bot_score * 20         # 0-20%
) = 0-100%
```

---

## ❓ Что реализовать?

**Выбери:**
1. **Быстрое улучшение** - динамический % (30 мин)
2. **Добавить новые признаки** - более точная детекция (2-3 часа)
3. **Оба варианта** - максимальная точность

Какой вариант предпочитаешь? 🤔




