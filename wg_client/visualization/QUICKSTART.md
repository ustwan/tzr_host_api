# 🚀 WG_HUB Visualization — Быстрый старт

## Что создано?

Полноценный контейнер визуализации с 4 интерактивными дашбордами:

1. **🗺️ Heatmap** — интерактивная карта мира с тепловой картой боёв
2. **👤 Players** — поиск игроков, детальная статистика, графики
3. **🤖 Antibot** — real-time мониторинг проверок на ботов (SSE)
4. **🎯 ML Clusters** — 3D визуализация K-Means кластеров стилей игры

---

## Структура проекта

```
wg_client/visualization/
├── Dockerfile                 # Nginx Alpine
├── docker-compose.viz.yml     # Docker Compose конфигурация
├── nginx.conf                 # Nginx конфигурация
├── README.md                  # Полная документация
├── QUICKSTART.md             # Этот файл
└── public/                    # Статические файлы
    ├── index.html             # Главная страница (навигация)
    ├── heatmap.html           # Тепловая карта
    ├── players.html           # Поиск игроков
    ├── antibot.html           # Антибот мониторинг
    ├── ml-clusters.html       # ML кластеры
    └── assets/
        ├── js/
        │   └── api-client.js  # Общий API клиент
        └── css/
            └── common.css     # Общие стили
```

---

## Запуск за 3 шага

### Шаг 1: Настройка DNS

Добавьте в `/etc/hosts`:

```bash
sudo nano /etc/hosts
```

Добавить строку:

```
127.0.0.1 viz.wg.local
```

Сохранить: `Ctrl+O`, `Enter`, выйти: `Ctrl+X`

---

### Шаг 2: Запуск контейнера

```bash
cd /Users/ii/Documents/code/WG_HUB/wg_client/visualization
docker-compose -f docker-compose.viz.yml up -d --build
```

**Ожидаемый вывод:**

```
[+] Building 12.3s (8/8) FINISHED
[+] Running 1/1
 ✔ Container wg_visualization  Started
```

---

### Шаг 3: Проверка

```bash
# Проверка статуса контейнера
docker ps | grep wg_visualization

# Проверка логов
docker logs wg_visualization

# Health check
curl http://localhost/health
# Ответ: OK
```

---

## Доступ к дашбордам

После запуска открыть в браузере:

- **Главная:** https://viz.wg.local
- **Heatmap:** https://viz.wg.local/heatmap.html
- **Players:** https://viz.wg.local/players.html
- **Antibot:** https://viz.wg.local/antibot.html
- **ML Clusters:** https://viz.wg.local/ml-clusters.html

> ⚠️ **Важно:** Убедитесь, что Traefik запущен и настроен для `wg_internal` сети.

---

## API Endpoints (используемые дашбордами)

Визуализация интегрируется с API5:

| Endpoint | Дашборд | Описание |
|----------|---------|----------|
| `GET /battles/heatmap` | Heatmap | Данные для тепловой карты |
| `GET /player/search?nickname={name}` | Players | Поиск игрока |
| `GET /player/{id}/stats` | Players | Статистика игрока |
| `GET /antibot/check?account_id={id}` | Players, Antibot | Проверка на бота |
| `GET /antibot/recent?limit=100` | Antibot | Последние проверки |
| `GET /antibot/stream` (SSE) | Antibot | Real-time поток |
| `GET /ml/clusters/stats` | ML Clusters | Статистика кластеров |
| `GET /ml/cluster/{id}/players` | ML Clusters | Игроки кластера |

---

## Быстрые команды

```bash
# Пересборка и перезапуск
docker-compose -f docker-compose.viz.yml up -d --build --force-recreate

# Остановка
docker-compose -f docker-compose.viz.yml down

# Логи в реальном времени
docker logs -f wg_visualization

# Перезапуск без пересборки
docker restart wg_visualization

# Обновить только HTML/CSS/JS (без пересборки)
docker cp public/heatmap.html wg_visualization:/usr/share/nginx/html/
docker exec wg_visualization nginx -s reload
```

---

## Разработка без Docker

Для локальной разработки:

```bash
cd public
python3 -m http.server 8080
```

Открыть: http://localhost:8080

> **Примечание:** API запросы будут недоступны без прокси или настройки CORS.

---

## Настройка API URL

По умолчанию дашборды подключаются к API через внутреннюю Docker сеть:

```javascript
// В файле: public/assets/js/api-client.js
const API_CONFIG = {
  baseURL: 'http://api_5:8005',  // ← По умолчанию
};
```

**Если нужен прокси через Nginx** (для CORS):

1. Раскомментировать прокси в `nginx.conf`:

```nginx
location /api/ {
    proxy_pass http://api_5:8005/;
    proxy_set_header Host $host;
}
```

2. Изменить URL в `api-client.js`:

```javascript
baseURL: '/api/v5',  // ← Относительный путь
```

3. Пересобрать:

```bash
docker-compose -f docker-compose.viz.yml up -d --build
```

---

## Troubleshooting

### Проблема: "viz.wg.local не открывается"

**Решение:**

1. Проверьте DNS:
   ```bash
   ping viz.wg.local
   ```

2. Проверьте Traefik:
   ```bash
   docker logs traefik | grep viz
   ```

3. Проверьте сеть:
   ```bash
   docker network inspect wg_internal
   ```

---

### Проблема: "API недоступен"

**Решение:**

1. Проверьте API5:
   ```bash
   docker ps | grep api_5
   curl http://api_5:8005/health
   ```

2. Проверьте сеть:
   ```bash
   docker network connect wg_internal wg_visualization
   ```

---

### Проблема: "Real-time поток не работает"

**Решение:**

SSE требует правильной настройки Nginx для длинных соединений:

```nginx
location /api/antibot/stream {
    proxy_pass http://api_5:8005/antibot/stream;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
}
```

---

## Следующие шаги

1. ✅ Запустите контейнер
2. ✅ Откройте https://viz.wg.local
3. ✅ Протестируйте все 4 дашборда
4. ⚙️ Настройте интеграцию с реальным API5
5. 🎨 Кастомизируйте дизайн под свои нужды
6. 📊 Добавьте дополнительные дашборды

---

## Архитектура

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Browser   │─────▶│   Traefik   │─────▶│ Nginx (viz) │
│ viz.wg.local│      │   (443)     │      │   (port 80) │
└─────────────┘      └─────────────┘      └─────────────┘
                            │                     │
                            │                     │
                            ▼                     ▼
                     ┌─────────────┐      ┌─────────────┐
                     │   API 5     │◀─────│ api-client.js│
                     │  (port 8005)│      │  (fetch)    │
                     └─────────────┘      └─────────────┘
```

---

## Технологии

- **Frontend:** Vanilla JS + HTML5 Canvas
- **Графики:** Chart.js 4.4.0 (2D), Plotly.js 2.27.0 (3D)
- **Real-time:** Server-Sent Events (SSE)
- **HTTP Client:** Fetch API с retry
- **Сервер:** Nginx 1.25 Alpine
- **UI:** Custom CSS (тёмная тема)

---

## Производительность

- Gzip сжатие для всех текстовых ресурсов
- Кэширование статики (7 дней)
- Lazy loading для графиков
- Debounce для поиска
- Responsive design

---

## Безопасность

Для добавления базовой авторизации:

```bash
# Генерация пароля
htpasswd -nb admin mypassword
# Результат: admin:$apr1$...

# Добавить в docker-compose.viz.yml (раскомментировать middleware)
```

---

## Поддержка

- **Документация:** `README.md`
- **Логи:** `docker logs wg_visualization`
- **Health:** `curl http://localhost/health`

---

**Готово! 🎉 Контейнер визуализации полностью настроен и готов к работе.**









