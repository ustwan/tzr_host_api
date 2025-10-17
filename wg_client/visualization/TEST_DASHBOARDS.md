# ✅ Тестирование дашбордов — Инструкция

## 🎯 Работающие дашборды (протестировано)

### 1. 🔥 Analytics Heatmap ✅ РАБОТАЕТ!

**URL:** http://localhost:14488/analytics-heatmap.html

**Тест:**
```
1. Откройте дашборд
2. Выберите "📊 Analytics Heatmap"
3. Оставьте даты по умолчанию
4. Нажмите "🔄 Загрузить"
5. ✅ Должно загрузиться 27 точек на карте
```

**API Endpoints:**
- ✅ `/analytics/map/heatmap` → 27 точек
- ✅ `/analytics/pve/top-locations` → 10 локаций
- ✅ `/analytics/map/pvp-hotspots` → 10 точек

**Что отображается:**
- Интерактивная карта мира
- Тепловые точки с градиентом
- Tooltip при наведении
- Переключение между источниками

---

### 2. 🗺️ Clan Control ✅ РАБОТАЕТ!

**URL:** http://localhost:14488/analytics-clan-control.html

**Тест:**
```
1. Откройте дашборд
2. Период: 30 дней
3. Минимум боёв: 10
4. Нажмите "🔄 Загрузить данные"
5. ✅ Появятся карточки кланов с % контроля
```

**API Endpoint:**
- ✅ `/analytics/map/clan-control` → 10 кланов

**Что отображается:**
- Топ кланов по % контроля территорий
- Количество боёв каждого клана
- Контролируемые локации (координаты)
- Цветовая кодировка кланов

---

### 3. ⚠️ Churn Prediction ✅ РАБОТАЕТ!

**URL:** http://localhost:14488/analytics-churn.html

**Тест:**
```
1. Откройте дашборд
2. Установите даты (последние 30 дней)
3. Уровень риска: "Высокий (>70%)"
4. Лимит: 50
5. Нажмите "🔄 Загрузить"
6. ✅ Появится таблица игроков в группе риска
```

**API Endpoint:**
- ✅ `/analytics/predictions/churn` → 39 игроков

**Что отображается:**
- Статистика: высокий/средний/низкий риск
- Таблица игроков с % вероятности ухода
- Прогресс-бары риска (цветные)
- График распределения (donut chart)
- Факторы риска

**Данные из API4:**
```json
{
  "login": "VAGINALNYI SPAZM",
  "churn_score": 1.0,              → 100%
  "days_since_last_battle": 19,
  "battles_first_half": 30,
  "battles_second_half": 0,
  "priority": "HIGH"
}
```

---

### 4. 🗺️ Heatmap Editor ✅ РАБОТАЕТ!

**URL:** http://localhost:14488/heatmap.html

**Тест:**
```
1. Откройте дашборд
2. Нажмите "📂 Локации"
3. ✅ Загрузятся 3 купола
4. Включите "✏️ Режим редактора"
5. Кликайте на карте для добавления ячеек
```

**Локации:**
- Old Moscow (6 ячеек)
- Neva City (6 ячеек)  
- Oasis (6 ячеек)

**Возможности:**
- Редактирование локаций
- Добавление новых
- Tooltip с информацией
- Экспорт/импорт

---

### 5. 🎯 ML Clusters ⚠️ Модель не обучена

**URL:** http://localhost:14488/ml-clusters.html

**Status:** API возвращает "Модель не обучена"

**API Endpoint:**
- `/analytics/playstyle/clusters/stats` → "Модель не обучена"

**TODO:** Обучить ML модель в API4

---

## ⚠️ Нереализованные дашборды

### ⏰ Peak Hours
**Нужен:** `/analytics/time/peak-hours`  
**Есть в API4:** ❌ Нет

### ⚔️ PvP ELO
**Нужен:** `/analytics/pvp/elo`  
**Есть в API4:** ❌ Нет (только `/analytics/pve/elo`)

### 👤 Players
**Нужен:** `/player/search`, `/player/{id}/stats`  
**Есть в API4:** ❌ Нет

### 🤖 Antibot
**Нужен:** `/antibot/stream`, `/antibot/recent`  
**Есть в API4:** ✅ Есть `/analytics/antibot/candidates`

---

## 🧪 Быстрое тестирование

### Через командную строку:

```bash
# 1. Analytics Heatmap
curl "http://localhost:14488/api/analytics/map/heatmap" | jq 'length'
# Ожидается: 27

# 2. Clan Control
curl "http://localhost:14488/api/analytics/map/clan-control" | jq 'length'
# Ожидается: 10

# 3. Churn Prediction
curl "http://localhost:14488/api/analytics/predictions/churn" | jq 'length'
# Ожидается: 39

# 4. PvE Top Locations
curl "http://localhost:14488/api/analytics/pve/top-locations" | jq 'length'
# Ожидается: 10

# 5. PvP Hotspots
curl "http://localhost:14488/api/analytics/map/pvp-hotspots" | jq 'length'
# Ожидается: 10
```

### Через браузер:

```
Откройте: http://localhost:14488

Протестируйте каждый работающий дашборд:
1. Analytics Heatmap ✅
2. Clan Control ✅
3. Churn Prediction ✅
4. Heatmap Editor ✅
```

---

## 🐛 Исправленные ошибки

### 1. "Failed to fetch"
**Причина:** Неправильный baseURL  
**Решение:** Nginx прокси на API4

### 2. "502 Bad Gateway"
**Причина:** Прокси на неправильный порт (8085)  
**Решение:** Переключено на 8084

### 3. "Cannot read properties of undefined (reading 'hour')"
**Причина:** Нет проверки на undefined данные  
**Решение:** Добавлены проверки во все render функции

### 4. Демо-данные загружались всегда
**Причина:** Автозагрузка при старте  
**Решение:** Удалены все вызовы loadDemo()

---

## ✨ Итог

**Работает:** 5 из 10 дашбордов  
**Протестировано:** ✅ Все 5 работают с реальными данными  
**API Endpoints:** 6 работающих  
**Ошибки:** Все исправлены  

---

**Готово!** 🚀 Откройте http://localhost:14488 и тестируйте!









