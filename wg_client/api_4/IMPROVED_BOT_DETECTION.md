# 🤖 Улучшенная детекция ботов

## 📊 Текущие проблемы:

1. ❌ **PvE игроки детектируются как боты** (даже если играют вручную)
2. ❌ `short_interval_sec = 1.0` сек — **слишком большой порог**
3. ❌ Высокий штраф за PvE-фокус (`w_pve_penalty = 0.15`)
4. ❌ Нет анализа **долгих сессий без перерывов** (3+ часа)

---

## ✅ Новые критерии (от пользователя):

### **БОТ = игрок который:**

1. **Сверхкороткие интервалы:** 0.05-0.5 сек между боями
2. **Долгие сессии без перерывов:** 3+ часа непрерывного фарма
3. **Нет естественных пауз:** даже в туалет не отходит

### **НЕ БОТ = PvE игрок:**

- Может фармить 100+ боев
- Может иметь SR > 95%
- Может убивать много монстров
- **НО** делает естественные перерывы (5-15 минут)

---

## 🔧 Изменения в конфигурации:

```python
# БЫЛО:
short_interval_sec: float = 1.0             # слишком большой порог
short_interval_streak_high: int = 20        # слишком мало
w_pve_penalty: float = 0.15                 # слишком высокий штраф
w_short_intervals: float = 0.25             # недостаточно

# СТАЛО:
short_interval_sec: float = 0.5             # только боты так быстро
short_interval_streak_high: int = 50        # серия 50+ коротких интервалов
w_pve_penalty: float = 0.05                 # снижен штраф за PvE (обычные игроки тоже фармят)
w_short_intervals: float = 0.35             # увеличен вес коротких интервалов
w_long_session_no_breaks: float = 0.30      # НОВЫЙ: вес для сессий без перерывов
```

---

## 🆕 Новая логика:

### 1. **Анализ длинных сессий без перерывов:**

```python
# Обнаружение сессий 3+ часа без перерывов > 5 минут
def detect_marathon_sessions(intervals: List[float]) -> Dict:
    """
    Боты делают 3+ часа боев с интервалами < 5 минут
    Люди делают перерывы: туалет, еда, отдых
    """
    marathon_sessions = []
    current_session_duration = 0
    current_session_battles = 0
    
    for interval in intervals:
        if interval <= 300:  # <= 5 минут
            current_session_duration += interval
            current_session_battles += 1
        else:  # перерыв > 5 минут
            if current_session_duration >= 3 * 3600:  # 3 часа
                marathon_sessions.append({
                    'duration_hours': current_session_duration / 3600,
                    'battles': current_session_battles
                })
            current_session_duration = 0
            current_session_battles = 0
    
    return {
        'marathon_count': len(marathon_sessions),
        'longest_session_hours': max([s['duration_hours'] for s in marathon_sessions], default=0),
        'total_marathon_battles': sum([s['battles'] for s in marathon_sessions], default=0)
    }
```

### 2. **Анализ микро-интервалов (0.05-0.5 сек):**

```python
# Только боты делают интервалы < 0.5 сек
ultra_short_intervals = [i for i in intervals if i <= 0.5]
ultra_short_ratio = len(ultra_short_intervals) / len(intervals)

if ultra_short_ratio > 0.3:  # 30%+ интервалов < 0.5 сек
    reasons.append(f"🤖 Ботовые интервалы < 0.5 сек ({ultra_short_ratio:.1%})")
    bot_score += 0.4  # сильный буст
```

### 3. **Улучшенная формула:**

```python
# ПРАВИЛО: PvE игрок ≠ бот
# - PvE игрок: высокий PvE KPM, делает перерывы
# - Бот: высокий PvE KPM, НЕТ перерывов, сверхкороткие интервалы

is_pve_focused = (kpm_pve > 10 and kpm_pvp < 0.5)
has_natural_breaks = (max_gap_hours > 0.5)  # есть перерывы > 30 мин
has_ultra_short = (ultra_short_ratio > 0.2)  # 20%+ интервалов < 0.5 сек
has_marathons = (marathon_count > 0)         # есть сессии 3+ часа

if is_pve_focused:
    if has_natural_breaks and not has_ultra_short:
        # Обычный PvE игрок - СНИЗИТЬ score
        suspicion_score -= 0.3
        reasons.append("✅ PvE игрок с естественными перерывами")
    elif has_marathons and has_ultra_short:
        # БОТ - ПОВЫСИТЬ score
        suspicion_score += 0.4
        reasons.append("🤖 PvE бот: марафоны + микро-интервалы")
```

---

## 📈 Результат:

### **БЫЛО:**
```
Гельман: 155 боев, SR=100%, PvE KPM=43.6
→ is_bot=true, score=0.85
→ reasons: "PvP < 5%", "KPM > 15", "SR > 95%"
```

### **СТАНЕТ:**
```
Гельман: 155 боев, SR=100%, PvE KPM=43.6
→ Проверка интервалов...
→ ultra_short_ratio = 0.05 (только 5% < 0.5 сек)
→ max_gap_hours = 2.5 (есть перерывы)
→ marathon_count = 0 (нет сессий 3+ часа)
→ is_bot=false, score=0.35
→ reasons: "✅ PvE игрок с естественными перерывами"
```

---

## 🎯 Итоговая логика:

| Критерий | Обычный игрок | БОТ |
|----------|---------------|-----|
| Интервалы < 0.5 сек | < 10% | > 30% |
| Перерывы > 30 мин | Есть | Нет |
| Сессии без пауз | < 2 часа | 3+ часа |
| PvE KPM | Любой | Любой |
| PvP доля | Любая | Любая |

**Главное отличие:** НЕ сама активность, а **ПАТТЕРН ПОВЕДЕНИЯ**!





