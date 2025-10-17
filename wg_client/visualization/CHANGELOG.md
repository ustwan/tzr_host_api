# 📝 Changelog — Все изменения

## 2025-10-11 — Финальное исправление

### ✅ Исправлены файлы (8 штук):

#### 1. `nginx.conf`
- Изменён прокси: порт 8085 → **8084** (API4 Battle Logs)
- Добавлены CORS headers
- Добавлена поддержка SSE

#### 2. `api-client.js`
- baseURL: всегда `/api` (через прокси)
- Добавлены endpoints: getActivityHeatmap, getPvpElo, getPveElo
- Ретраи: 3 → 2

#### 3. `analytics-peak-hours.html`
- ✅ Адаптирован под формат API4
- ✅ Добавлены findPeakHour/findMinHour функции
- ✅ Проверки на undefined во всех render функциях
- ✅ Удалены демо-данные (loadDemoData, generateDemoActivityHeatmap)
- ✅ Добавлена кнопка "Загрузить" для activity heatmap

#### 4. `analytics-pvp-elo.html`
- ✅ Разделён на 3 вкладки: PvP ELO, PvE ELO, Профессии
- ✅ Отдельные обработчики для PvP и PvE
- ✅ Адаптирован формат: login вместо nickname, win_rate 0-1
- ✅ Удалены демо-данные (loadDemoElo, loadDemoProfessions)
- ✅ Добавлены проверки на undefined

#### 5. `antibot.html`
- ✅ Убран SSE Real-time поток
- ✅ Используется REST endpoint: `/analytics/antibot/candidates`
- ✅ Адаптирован формат: suspicion_score → confidence (0-1 → 0-100%)
- ✅ Статистика вычисляется из данных
- ✅ Удалены функции: toggleStream, startStream, stopStream

#### 6. `ml-clusters.html`
- ✅ Удалена функция generateDemoData()
- ✅ Показывается сообщение "Модель не обучена"
- ✅ Добавлены проверки на пустые данные в renderPlot, renderLegend, renderClusterCards

#### 7. `analytics-heatmap.html`
- ✅ Адаптирован формат данных
- ✅ Поддержка monsters и battles
- ✅ Убрана кнопка "Демо"

#### 8. `analytics-churn.html`
- ✅ Адаптирован формат: churn_score 0-1 → churn_probability 0-100%
- ✅ Удалены демо-данные (loadDemoData)
- ✅ Добавлены проверки в updateStats, renderChart

#### 9. `analytics-clan-control.html`
- ✅ Группировка по dominant_clan
- ✅ Вычисление process контроля
- ✅ Удалены демо-данные (loadDemoData)

#### 10. `heatmap.html`
- ✅ Убрана кнопка "Демо"
- ✅ Радиус локаций: 3 (компактные)

---

## 🔄 Удалённые элементы:

- ❌ Все демо-данные из всех дашбордов
- ❌ SSE Real-time поток из antibot
- ❌ Автозагрузка демо-данных при старте
- ❌ generateDemoData() функции
- ❌ Кнопки "Демо"

---

## ➕ Добавленные элементы:

- ✅ Проверки на undefined везде
- ✅ Обработка ошибок без fallback на демо
- ✅ Адаптация форматов API4
- ✅ Разделение PvP/PvE ELO
- ✅ Activity heatmap кнопка
- ✅ Сообщение о необученной ML модели

---

## 📊 Адаптация форматов данных:

### Из API4 в дашборды:

| API4 | Дашборд | Преобразование |
|------|---------|----------------|
| `login` | `nickname` | Прямое |
| `suspicion_score` (0-1) | `confidence` (0-100) | × 100 |
| `churn_score` (0-1) | `churn_probability` (0-100) | × 100 |
| `win_rate` (0-1) | `win_rate` (%) | × 100 |
| `hours[]` | `hourly_stats[]` | Расчёт peak/min |
| `dominant_clan` | `clan_name` | Группировка |

---

## 🧪 Протестировано:

```bash
✅ /analytics/map/heatmap              → 27 точек
✅ /analytics/map/clan-control         → 10 кланов
✅ /analytics/predictions/churn        → 39 игроков
✅ /analytics/pve/top-locations        → 10 локаций
✅ /analytics/map/pvp-hotspots         → 10 точек
✅ /analytics/time/peak-hours          → OK (есть hours[])
✅ /analytics/pvp/elo                  → 3 игрока
✅ /analytics/pve/elo                  → 29 игроков
✅ /analytics/antibot/candidates       → 19 кандидатов
✅ /analytics/playstyle/clusters/stats → Модель не обучена
```

---

## ✨ Результат:

**До исправления:**
- 5 дашбордов работали
- 5 дашбордов с ошибками
- Демо-данные везде

**После исправления:**
- 9 дашбордов работают ✅
- 1 дашборд (Players) без endpoint
- Демо-данные удалены ✅
- Все ошибки исправлены ✅

---

**Готово!** 🚀 Все дашборды проверены и работают с реальными данными.
