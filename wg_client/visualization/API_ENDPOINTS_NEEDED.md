# 🔌 API Endpoints для реализации на бэкенде

Список всех endpoints, которые используют дашборды визуализации.

---

## 🆕 Приоритетные (для новых дашбордов)

### 1. Analytics Heatmap (3 endpoint)

```python
@app.get("/analytics/map/heatmap")
async def get_analytics_heatmap(
    date_from: str,  # YYYY-MM-DD
    date_to: str
):
    """
    Общая аналитическая тепловая карта
    Возвращает: [{"loc": [x, y], "value": N, "battles": N}]
    """
    return {"success": True, "data": [...]}

@app.get("/analytics/pve/top-locations")
async def get_pve_top_locations(
    date_from: str,
    date_to: str,
    limit: int = 100
):
    """
    Топ локаций для PvE контента
    Возвращает: [{"loc": [x, y], "value": N, "location_name": "..."}]
    """
    return {"success": True, "data": [...]}

@app.get("/analytics/map/pvp-hotspots")
async def get_pvp_hotspots(
    date_from: str,
    date_to: str
):
    """
    Горячие точки PvP боёв
    Возвращает: [{"loc": [x, y], "value": N, "battles": N}]
    """
    return {"success": True, "data": [...]}
```

---

### 2. Clan Control (1 endpoint)

```python
@app.get("/analytics/map/clan-control")
async def get_clan_control(days: int = 30):
    """
    Контроль территорий кланами за последние N дней
    
    Возвращает:
    {
      "clans": [
        {
          "clan_tag": "ELITE",
          "clan_name": "Elite Warriors",
          "control_percentage": 45.2,
          "total_battles": 1234,
          "wins": 856,
          "win_rate": 69.4,
          "controlled_locations": ["Old Moscow", "Neva City"],
          "members_count": 45
        }
      ]
    }
    """
    return {"success": True, "data": {...}}
```

---

### 3. Peak Hours (2 endpoints)

```python
@app.get("/analytics/time/peak-hours")
async def get_peak_hours(
    date_from: str,
    date_to: str,
    timezone: str = "UTC"
):
    """
    Пиковые часы активности
    
    Возвращает:
    {
      "hourly_stats": [
        {"hour": 0, "battles": 234, "avg_players": 48},
        ...
      ],
      "peak_hour": {"hour": 20, "battles": 842, "avg_players": 156},
      "min_hour": {"hour": 4, "battles": 45, "avg_players": 12},
      "total_battles": 12345,
      "avg_battles_per_hour": 514,
      "day_of_week_stats": [
        {"day": "Пн", "hourly": [100, 120, 90, ...24 элемента]},
        ...7 дней
      ]
    }
    """
    return {"success": True, "data": {...}}

@app.get("/analytics/time/activity-heatmap")
async def get_activity_heatmap(
    date_from: str,
    date_to: str
):
    """
    Детализированная тепловая карта активности
    
    Возвращает:
    {
      "activity": [
        {
          "date": "2025-10-01",
          "hourly": [50, 60, 45, ...24 элемента]
        },
        ...30 дней
      ]
    }
    """
    return {"success": True, "data": {...}}
```

---

### 4. PvP ELO (1 endpoint)

```python
@app.get("/analytics/pvp/elo")
async def get_pvp_elo(
    date_from: str,
    date_to: str,
    limit: int = 50
):
    """
    PvP ELO рейтинг игроков
    
    Возвращает:
    [
      {
        "rank": 1,
        "account_id": 1000001,
        "nickname": "Player_1",
        "elo": 2850,
        "battles": 456,
        "win_rate": 68.5,
        "kd_ratio": 2.3
      },
      ...
    ]
    """
    return {"success": True, "data": [...]}
```

---

### 5. Профессии (1 endpoint)

```python
@app.get("/players/by-profession")
async def get_players_by_profession(
    date_from: str,
    date_to: str,
    profession: str = None  # tank, dd, healer, support или None (все)
):
    """
    Игроки по профессиям
    
    Возвращает:
    [
      {
        "account_id": 2000001,
        "nickname": "Player_1",
        "profession": "tank",  # tank, dd, healer, support
        "battles": 234,
        "win_rate": 55.2,
        "avg_damage": 1850
      },
      ...
    ]
    """
    return {"success": True, "data": [...]}
```

---

### 6. Churn Prediction (1 endpoint)

```python
@app.get("/analytics/predictions/churn")
async def get_churn_prediction(
    date_from: str,
    date_to: str,
    risk_threshold: int = 0,  # 0-100 (минимальный % риска)
    limit: int = 50
):
    """
    Предсказание оттока игроков
    
    Возвращает:
    {
      "players": [
        {
          "account_id": 1000001,
          "nickname": "Player_1",
          "churn_probability": 85.3,  # % вероятности ухода
          "last_battle_days_ago": 15,
          "battles_last_30d": 12,
          "win_rate": 45.2,
          "avg_damage": 1234,
          "factors": {
            "inactivity": 0.85,
            "declining_performance": 0.45,
            "low_engagement": 0.72
          }
        },
        ...
      ]
    }
    """
    return {"success": True, "data": {...}}
```

---

## 📋 Итого новых endpoints: 9

1. ✅ `/analytics/map/heatmap` — общая аналитика
2. ✅ `/analytics/pve/top-locations` — PvE локации
3. ✅ `/analytics/map/pvp-hotspots` — PvP hotspots
4. ✅ `/analytics/map/clan-control` — контроль кланов
5. ✅ `/analytics/time/peak-hours` — пиковые часы
6. ✅ `/analytics/time/activity-heatmap` — activity heatmap
7. ✅ `/analytics/pvp/elo` — PvP рейтинг
8. ✅ `/players/by-profession` — игроки по профессиям
9. ✅ `/analytics/predictions/churn` — предсказание оттока

---

## 🎯 Приоритет реализации

### Высокий (обязательно)
1. `/analytics/map/heatmap` — используется в analytics-heatmap
2. `/analytics/time/peak-hours` — основной дашборд
3. `/analytics/pvp/elo` — рейтинг

### Средний (желательно)
4. `/analytics/map/clan-control` — контроль кланов
5. `/players/by-profession` — профессии
6. `/analytics/predictions/churn` — предсказание оттока

### Низкий (дополнительно)
7. `/analytics/pve/top-locations` — PvE
8. `/analytics/map/pvp-hotspots` — PvP hotspots
9. `/analytics/time/activity-heatmap` — детализированная активность

---

## 🔄 Формат ответов

Все endpoints возвращают единообразный формат:

```json
{
  "success": true,
  "data": { ... } или [ ... ]
}
```

При ошибке:

```json
{
  "success": false,
  "error": "Описание ошибки"
}
```

---

## ⚡ Быстрый старт для бэкенда

### 1. Скопировать шаблоны выше в API5

### 2. Реализовать SQL запросы

Пример для `/analytics/map/heatmap`:

```sql
SELECT 
  loc_x as x, 
  loc_y as y, 
  COUNT(*) as battles
FROM battles
WHERE battle_time BETWEEN :date_from AND :date_to
GROUP BY loc_x, loc_y
ORDER BY battles DESC
LIMIT 500;
```

### 3. Адаптировать формат данных

```python
# Преобразовать в нужный формат
data = [
  {"loc": [row.x, row.y], "value": row.battles, "battles": row.battles}
  for row in results
]
return {"success": True, "data": data}
```

### 4. Протестировать

```bash
curl "http://localhost:8005/analytics/map/heatmap?date_from=2025-10-01&date_to=2025-10-11"
```

---

**Готово!** Реализуйте endpoints на бэкенде и дашборды заработают с реальными данными. 🚀









