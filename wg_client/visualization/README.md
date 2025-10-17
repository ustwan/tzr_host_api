# WG_HUB Visualization Dashboard

Контейнер визуализации для мониторинга и аналитики игровых данных.

## Архитектура

```
visualization/
├── Dockerfile                 # Nginx Alpine образ
├── docker-compose.viz.yml     # Compose конфигурация
├── nginx.conf                 # Nginx конфигурация
└── public/                    # Статические файлы
    ├── index.html             # Главная страница (навигация)
    ├── heatmap.html           # Тепловая карта боёв
    ├── players.html           # Поиск игроков + статистика
    ├── antibot.html           # Антибот мониторинг
    ├── ml-clusters.html       # ML кластеры стилей игры
    └── assets/
        ├── js/
        │   └── api-client.js  # Общий клиент для API
        └── css/
            └── common.css     # Общие стили
```

## Запуск

### 1. Настройка DNS (добавить в `/etc/hosts`):

```bash
127.0.0.1 viz.wg.local
```

### 2. Запуск контейнера:

```bash
cd wg_client/visualization
docker-compose -f docker-compose.viz.yml up -d --build
```

### 3. Доступ:

- **Главная:** https://viz.wg.local
- **Тепловая карта:** https://viz.wg.local/heatmap.html
- **Игроки:** https://viz.wg.local/players.html
- **Антибот:** https://viz.wg.local/antibot.html
- **ML кластеры:** https://viz.wg.local/ml-clusters.html

## API Endpoints

Визуализация использует API5 (`http://api_5:8005`):

- `GET /api/v5/battles/heatmap` - данные для тепловой карты
- `GET /api/v5/player/stats?nickname={name}` - статистика игрока
- `GET /api/v5/antibot/check?account_id={id}` - проверка на бота
- `GET /api/v5/antibot/recent?limit=100` - последние проверки
- `GET /api/v5/ml/cluster?account_id={id}` - кластер игрока
- `GET /api/v5/ml/clusters/stats` - статистика по кластерам

## Разработка

### Локальная разработка без Docker:

```bash
cd public
python3 -m http.server 8080
# Открыть: http://localhost:8080
```

### Обновление без перезапуска:

```bash
# Копировать изменённые файлы в контейнер
docker cp public/heatmap.html wg_visualization:/usr/share/nginx/html/
```

### Полная пересборка:

```bash
docker-compose -f docker-compose.viz.yml down
docker-compose -f docker-compose.viz.yml up -d --build
```

## Структура дашбордов

### 1. Heatmap (Тепловая карта)
- Интерактивная карта мира (координаты -180..180)
- Загрузка данных из API
- Зум, панорамирование, поиск по координатам
- Слои: купола, шахты, сетка, оси

### 2. Players (Игроки)
- Поиск по нику
- Карточка игрока с базовой статистикой
- Графики: урон, винрейт, активность
- Тепловая карта игрока
- ML кластер и стиль игры

### 3. Antibot (Антибот)
- Real-time мониторинг проверок (SSE)
- Таблица последних проверок
- Статистика за 24ч
- Топ подозрительных игроков
- Фильтрация и сортировка

### 4. ML Clusters (Кластеры)
- Визуализация K-Means кластеров
- 3D scatter plot (Plotly.js)
- Статистика по каждому кластеру
- Поиск игроков в кластере

## Технологии

- **Frontend:** Vanilla JS + HTML5 Canvas/SVG
- **Графики:** Chart.js, Plotly.js
- **HTTP:** Fetch API
- **Real-time:** Server-Sent Events (SSE)
- **UI:** Custom CSS (тёмная тема)
- **Сервер:** Nginx 1.25 Alpine

## CORS

Если API недоступен через CORS, раскомментируйте прокси в `nginx.conf`:

```nginx
location /api/ {
    proxy_pass http://api_5:8005/;
    ...
}
```

И используйте относительные URL в `api-client.js`:

```js
const API_BASE_URL = '/api/v5';  // вместо 'http://api_5:8005'
```

## Мониторинг

```bash
# Логи
docker logs -f wg_visualization

# Статус
docker ps | grep wg_visualization

# Health check
curl http://localhost/health
```

## Безопасность

Для добавления базовой авторизации раскомментируйте middleware в `docker-compose.viz.yml` и сгенерируйте пароль:

```bash
htpasswd -nb admin mypassword
# admin:$apr1$...hash...
```

## Производительность

- Gzip сжатие для всех текстовых ресурсов
- Кэширование статики (7 дней)
- Health check каждые 30с
- Restart policy: unless-stopped

## Roadmap

- [ ] WebSocket для real-time обновлений
- [ ] Экспорт данных (CSV, JSON)
- [ ] Кастомизация дашбордов
- [ ] Сохранение настроек в localStorage
- [ ] Темы оформления (light/dark)
- [ ] Мобильная адаптация









