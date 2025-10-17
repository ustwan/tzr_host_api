# 📊 WG_HUB Visualization — Все дашборды (полный гайд)

## 🌐 Главная страница

**URL:** http://localhost:14488

Навигация между всеми 10 дашбордами. Быстрый поиск игрока по нику.

---

## 1. 🗺️ Heatmap (Редактор локаций)

**URL:** http://localhost:14488/heatmap.html

### Функции
- Интерактивная карта мира (-180..180)
- Редактор локаций (купола, шахты, фарм-точки)
- Загрузка из файла или API
- Tooltip с информацией о локации при наведении

### Предустановленные локации (3 купола)
- **Old Moscow:** (0,-1), (0,0), (1,-1), (1,0), (2,-1), (2,0)
- **Neva City:** (-33,-56), (-33,-57), (-33,-55), (-34,-56), (-34,-57), (-34,-55)
- **Oasis:** (56,33), (56,34), (56,35), (55,33), (55,34), (55,35)

### Управление
- Колесо мыши — зум
- Перетаскивание — панорамирование
- ✏️ **Режим редактора** — добавление/редактирование локаций
- Клик на карте в режиме редактора — добавить ячейку

---

## 2. 👤 Players (Поиск игроков)

**URL:** http://localhost:14488/players.html

### Функции
- Поиск по никнейму
- Детальная статистика
- Графики (Chart.js)
- Антибот флаги
- ML кластер стиля игры
- Табы: Обзор, Графики, Танки, История

### API Endpoints
- `/player/search?nickname=...`
- `/player/{id}/stats`
- `/antibot/check?account_id=...`
- `/ml/cluster?account_id=...`

---

## 3. 🤖 Antibot (Мониторинг)

**URL:** http://localhost:14488/antibot.html

### Функции
- Real-time поток проверок (SSE)
- Таблица последних проверок
- Статистика за 24ч
- Топ подозрительных игроков
- Фильтр по уровню риска

### API Endpoints
- `/antibot/stream` (SSE)
- `/antibot/recent?limit=100`
- `/antibot/suspicious?limit=10`
- `/antibot/stats/24h`

---

## 4. 🎯 ML Clusters (Кластеры)

**URL:** http://localhost:14488/ml-clusters.html

### Функции
- 3D scatter plot (Plotly.js)
- 7 кластеров стилей игры
- Выбор осей X/Y/Z
- Карточки кластеров с метриками
- Клик на кластер — детали

### API Endpoints
- `/ml/clusters/stats`
- `/ml/cluster/{id}/players`
- `/ml/clusters/centroids`

---

## 5. 🔥 Analytics Heatmap (Аналитические карты)

**URL:** http://localhost:14488/analytics-heatmap.html

### Функции
**3 источника данных:**
- 📊 **Analytics Heatmap** — общая аналитика
- 🏰 **PvE Top Locations** — топ локаций для PvE
- ⚔️ **PvP Hotspots** — горячие точки PvP

### Фильтры
- Дата от/до
- Источник данных (dropdown)
- Радиус точек
- Прозрачность

### API Endpoints
- `/analytics/map/heatmap?date_from=...&date_to=...`
- `/analytics/pve/top-locations?date_from=...&date_to=...&limit=100`
- `/analytics/map/pvp-hotspots?date_from=...&date_to=...`

---

## 6. 🗺️ Clan Control (Контроль кланов)

**URL:** http://localhost:14488/analytics-clan-control.html

### Функции
- Топ кланов по % контроля территорий
- Статистика по каждому клану
- Контролируемые локации
- Экспорт в CSV

### Фильтры
- Период (7, 14, 30, 60, 90 дней)
- Минимум боёв

### API Endpoint
- `/analytics/map/clan-control?days=30`

**Формат ответа:**
```json
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
```

---

## 7. ⏰ Peak Hours (Пиковые часы)

**URL:** http://localhost:14488/analytics-peak-hours.html

### Функции
- График активности по 24 часам (столбцы/линия)
- Тепловая карта: День недели × Час
- 🆕 **Activity Heatmap:** детализация по дням (30 дней × 24 часа)
- Инсайты и рекомендации
- Статистика: пиковый час, средняя активность

### Фильтры
- Дата от/до
- Часовой пояс (UTC, МСК, Лондон, Нью-Йорк)
- День недели (все/будни/выходные)

### API Endpoints
- `/analytics/time/peak-hours?date_from=...&date_to=...&timezone=...`
- `/analytics/time/activity-heatmap?date_from=...&date_to=...`

**Формат ответа (peak-hours):**
```json
{
  "hourly_stats": [{"hour": 0, "battles": 234, "avg_players": 48}],
  "peak_hour": {"hour": 20, "battles": 842},
  "min_hour": {"hour": 4, "battles": 45},
  "total_battles": 12345,
  "avg_battles_per_hour": 514,
  "day_of_week_stats": [{"day": "Пн", "hourly": [100, 120, ...]}]
}
```

**Формат ответа (activity-heatmap):**
```json
{
  "activity": [
    {
      "date": "2025-10-01",
      "hourly": [50, 60, 45, ..., 200]
    }
  ]
}
```

---

## 8. ⚔️ PvP ELO & Professions (PvP рейтинг)

**URL:** http://localhost:14488/analytics-pvp-elo.html

### Две вкладки

#### Вкладка 1: ELO Рейтинг
- Таблица лидеров
- Ранги: 🥇🥈🥉
- Статистика: топ ELO, средний ELO
- Фильтры: дата от/до, лимит

#### Вкладка 2: По профессиям
- Таблица игроков
- Профессии:
  - 🛡️ Танк
  - ⚔️ Дамагер
  - 💚 Хилер
  - 🔧 Поддержка
- График распределения (donut chart)
- Фильтр по профессии

### API Endpoints
- `/analytics/pvp/elo?date_from=...&date_to=...&limit=50`
- `/players/by-profession?date_from=...&date_to=...&profession=...`

**Формат ответа (ELO):**
```json
[
  {
    "rank": 1,
    "account_id": 1000001,
    "nickname": "Player_1",
    "elo": 2850,
    "battles": 456,
    "win_rate": 68.5,
    "kd_ratio": 2.3
  }
]
```

**Формат ответа (Профессии):**
```json
[
  {
    "account_id": 2000001,
    "nickname": "Player_1",
    "profession": "tank",
    "battles": 234,
    "win_rate": 55.2,
    "avg_damage": 1850
  }
]
```

---

## 9. ⚠️ Churn Prediction (Предсказание оттока)

**URL:** http://localhost:14488/analytics-churn.html

### Функции
- Таблица игроков в группе риска
- Статистика: высокий/средний/низкий риск
- Прогресс-бары вероятности оттока
- График распределения (donut)
- Факторы риска (4 категории)
- Экспорт в CSV

### Фильтры
- Дата от/до
- Уровень риска (все/высокий/средний/низкий)
- Лимит игроков

### Сортировка
- По риску (по убыванию)
- По активности (последний бой)

### API Endpoint
- `/analytics/predictions/churn?date_from=...&date_to=...&risk_threshold=70&limit=50`

**Формат ответа:**
```json
{
  "players": [
    {
      "account_id": 1000001,
      "nickname": "Player_1",
      "churn_probability": 85.3,
      "last_battle_days_ago": 15,
      "battles_last_30d": 12,
      "win_rate": 45.2,
      "avg_damage": 1234,
      "factors": {
        "inactivity": 0.85,
        "declining_performance": 0.45,
        "low_engagement": 0.72
      }
    }
  ]
}
```

---

## 📊 Сводка по дашбордам

| Дашборд | Endpoints | Фильтры | Графики | Демо |
|---------|-----------|---------|---------|------|
| Heatmap | 3 | Даты, источник | Canvas | ✅ |
| Players | 4 | Поиск | Chart.js | ✅ |
| Antibot | 4 | Риск | — | ✅ |
| ML Clusters | 3 | Оси | Plotly.js | ✅ |
| Analytics Heatmap | 3 | Даты, источник | Canvas | ✅ |
| Clan Control | 1 | Период, боёв | — | ✅ |
| Peak Hours | 2 | Даты, TZ, день | Chart.js | ✅ |
| PvP ELO | 2 | Даты, профессия | Chart.js | ✅ |
| Churn Prediction | 1 | Даты, риск, лимит | Chart.js | ✅ |

**Всего:** 9 дашбордов + главная = 10 страниц

---

## 🔌 Все API Endpoints (итого 23)

### Battles
1. `GET /battles/heatmap`
2. `GET /battles/{id}`

### Players
3. `GET /player/search`
4. `GET /player/{id}/stats`
5. `GET /player/{id}/battles`
6. `GET /player/{id}/heatmap`
7. `GET /player/{id}/tanks/top`
8. `GET /players/by-profession`

### Antibot
9. `GET /antibot/check`
10. `GET /antibot/recent`
11. `GET /antibot/suspicious`
12. `GET /antibot/stats/24h`
13. `GET /antibot/stream` (SSE)

### ML
14. `GET /ml/cluster`
15. `GET /ml/clusters/stats`
16. `GET /ml/cluster/{id}/players`
17. `GET /ml/clusters/centroids`

### Analytics
18. `GET /analytics/map/heatmap`
19. `GET /analytics/map/clan-control`
20. `GET /analytics/pve/top-locations`
21. `GET /analytics/map/pvp-hotspots`
22. `GET /analytics/pvp/elo`
23. `GET /analytics/time/peak-hours`
24. `GET /analytics/time/activity-heatmap`
25. `GET /analytics/predictions/churn`

### Locations
26. `GET /locations`
27. `POST /locations`
28. `POST /locations/{id}`
29. `POST /locations/{id}/delete`

### System
30. `GET /health`
31. `GET /stats`

---

## 🚀 Быстрый доступ

```bash
# Главная
http://localhost:14488

# Тепловые карты
http://localhost:14488/heatmap.html              # Редактор локаций
http://localhost:14488/analytics-heatmap.html    # 3 источника данных

# Игроки
http://localhost:14488/players.html              # Поиск + статистика
http://localhost:14488/analytics-pvp-elo.html    # PvP ELO + профессии

# Безопасность и ML
http://localhost:14488/antibot.html              # Real-time мониторинг
http://localhost:14488/ml-clusters.html          # K-Means кластеры

# Аналитика
http://localhost:14488/analytics-clan-control.html  # Контроль кланов
http://localhost:14488/analytics-peak-hours.html    # Пиковые часы + activity
http://localhost:14488/analytics-churn.html         # Предсказание оттока
```

---

## 🎯 Рекомендации по использованию

### Для мониторинга в реальном времени
1. **Antibot** — запустить SSE поток
2. **Peak Hours** — отслеживать текущую нагрузку

### Для аналитики данных
1. **Analytics Heatmap** — выбрать источник (PvE/PvP/All)
2. **Clan Control** — топ кланов за период
3. **Churn Prediction** — игроки в группе риска

### Для поиска и статистики
1. **Players** — поиск конкретного игрока
2. **PvP ELO** — рейтинг лучших игроков
3. **ML Clusters** — анализ стилей игры

---

## 🔧 Настройка API

### Вариант 1: Прямое подключение (localhost)

Если API запущен на `localhost:8005`, всё работает автоматически.

```bash
# Проверка
curl http://localhost:8005/health
```

### Вариант 2: Через Nginx прокси

Если нужен CORS прокси, раскомментируйте в `nginx.conf`:

```nginx
location /api/ {
    proxy_pass http://api_5:8005/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

И пересоберите:

```bash
docker-compose -f docker-compose.viz.yml up -d --build
```

---

## 📥 Экспорт данных

**Поддерживают экспорт в CSV:**
- Clan Control
- Churn Prediction

**Формат:** UTF-8, разделитель — запятая

---

## 🎨 Дизайн-система

### Цветовая палитра

| Компонент | Цвет | Hex |
|-----------|------|-----|
| Background | Тёмно-серый | #0b0f14 |
| Cards | Серый | #111827 |
| Accent Blue | Голубой | #60a5fa |
| Accent Purple | Фиолетовый | #a78bfa |
| Success | Зелёный | #10b981 |
| Warning | Жёлтый | #fbbf24 |
| Danger | Красный | #ef4444 |

### Шрифты

- **Основной:** System UI, -apple-system, Segoe UI, Roboto
- **Моноширинный:** SF Mono, Monaco, Consolas
- **Размер:** 14px (base)

---

## 🐛 Решение проблем

### "Failed to fetch"

**Решение:**
1. Проверьте что API запущен: `curl http://localhost:8005/health`
2. Проверьте `baseURL` в `api-client.js`
3. Используйте демо-данные для тестирования UI

### Демо-данные загружаются всегда

**Это нормально!** Демо-данные загружаются автоматически при ошибке API.

### Страница не открывается

**Решение:**
```bash
# Проверка контейнера
docker ps | grep wg_visualization

# Логи
docker logs wg_visualization --tail 50

# Перезапуск
docker restart wg_visualization
```

---

## 📦 Структура проекта

```
visualization/
├── Dockerfile
├── docker-compose.viz.yml
├── nginx.conf
├── README.md
├── QUICKSTART.md
├── ANALYTICS_DASHBOARDS.md
├── LOCATIONS_GUIDE.md
├── UPDATE_SUMMARY.md
├── ALL_DASHBOARDS.md          ← ВЫ ЗДЕСЬ
└── public/
    ├── index.html              (главная)
    ├── heatmap.html            (редактор локаций)
    ├── players.html            (поиск игроков)
    ├── antibot.html            (антибот)
    ├── ml-clusters.html        (ML кластеры)
    ├── analytics-heatmap.html  (3 источника тепловых карт)
    ├── analytics-clan-control.html
    ├── analytics-peak-hours.html
    ├── analytics-pvp-elo.html  (ELO + профессии)
    ├── analytics-churn.html    (предсказание оттока)
    ├── data/
    │   └── locations.json      (3 купола)
    └── assets/
        ├── js/
        │   └── api-client.js   (31 endpoint)
        └── css/
            └── common.css
```

---

## 🎉 Итого

**Создано:**
- ✅ 10 HTML страниц (9 дашбордов + главная)
- ✅ 31 API endpoint
- ✅ Полная интеграция с API5
- ✅ Демо-данные для всех дашбордов
- ✅ Фильтры по датам/времени/параметрам
- ✅ Экспорт в CSV (2 дашборда)
- ✅ Real-time SSE (Antibot)
- ✅ 3D визуализация (ML Clusters)
- ✅ Интерактивные карты (Canvas)
- ✅ Графики (Chart.js, Plotly.js)
- ✅ Редактор локаций

**Технологии:**
- Frontend: Vanilla JS (0 зависимостей кроме библиотек графиков)
- Графики: Chart.js 4.4.0, Plotly.js 2.27.0
- HTTP: Fetch API с retry/timeout
- Real-time: Server-Sent Events (SSE)
- Сервер: Nginx 1.25 Alpine

---

## 🌐 Все ссылки (для быстрого доступа)

Откройте в браузере:

```
http://localhost:14488                              # Главная
http://localhost:14488/heatmap.html                 # Редактор локаций
http://localhost:14488/players.html                 # Поиск игроков
http://localhost:14488/antibot.html                 # Антибот
http://localhost:14488/ml-clusters.html             # ML кластеры
http://localhost:14488/analytics-heatmap.html       # Аналитические карты (3 источника)
http://localhost:14488/analytics-clan-control.html  # Контроль кланов
http://localhost:14488/analytics-peak-hours.html    # Пиковые часы + activity
http://localhost:14488/analytics-pvp-elo.html       # PvP ELO + профессии
http://localhost:14488/analytics-churn.html         # Предсказание оттока
```

---

**Всё готово к использованию!** 🚀









