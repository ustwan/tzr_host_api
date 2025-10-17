# WG_HUB - Финальная версия с исправлениями

## 🎯 Что исправлено

### ✅ Критические исправления
1. **Относительные импорты** — все исправлены на абсолютные (`app.*`)
2. **Dockerfile API 4** — добавлено копирование `example/parser` и скриптов
3. **База данных** — создана полная миграция `V1__create_tables_complete.sql`
4. **Сети Docker** — исправлены имена сетей в compose файлах
5. **SQL запросы** — исправлены все ошибки (`p.player_id` → `p.id`)
6. **Путь парсера** — исправлен на `/app/example/parser`

### 🚀 Новые возможности
1. **Режимы работы** — тестовый и продакшн через `ctl.sh`
2. **Автоматический запуск** — скрипт `start_project.sh`
3. **Переменные окружения** — `env.test` и `env.prod`
4. **Автоматические миграции** — БД настраивается автоматически

## 🚀 Быстрый запуск

### 1. Автоматический запуск (рекомендуется)
```bash
cd wg_client
./start_project.sh
```

### 2. Ручной запуск через ctl.sh
```bash
# Тестовый режим (ограниченные ресурсы)
./tools/ctl.sh start-test

# Продакшн режим (полные ресурсы)
./tools/ctl.sh start-prod

# Все сервисы (по умолчанию)
./tools/ctl.sh start-all
```

### 3. Применение миграций
```bash
./tools/ctl.sh migrate
```

## 📊 Режимы работы

### Тестовый режим
- **Команда**: `./tools/ctl.sh start-test`
- **БД**: тестовая (`api4_battles`)
- **Ресурсы**: BATCH_SIZE=10, MAX_WORKERS=2
- **Файл конфигурации**: `env.test`

### Продакшн режим
- **Команда**: `./tools/ctl.sh start-prod`
- **БД**: продакшн (`api4_battles_prod`)
- **Ресурсы**: BATCH_SIZE=100, MAX_WORKERS=8
- **Файл конфигурации**: `env.prod`

## 🔧 Управление

### Основные команды
```bash
# Запуск
./tools/ctl.sh start-test    # тестовый режим
./tools/ctl.sh start-prod    # продакшн режим
./tools/ctl.sh start-all     # все сервисы

# Остановка
./tools/ctl.sh stop-all      # остановить все
./tools/ctl.sh down-all      # остановить и удалить volumes

# Управление
./tools/ctl.sh status        # статус контейнеров
./tools/ctl.sh logs [svc]    # логи сервиса
./tools/ctl.sh restart [svc] # перезапуск сервиса
./tools/ctl.sh migrate       # применить миграции

# Диагностика
./tools/ctl.sh doctor        # диагностика окружения
./tools/ctl.sh networks      # управление сетями
./tools/ctl.sh prune         # очистка Docker
```

## 📊 Доступные сервисы

После запуска доступны:
- **API 4**: http://127.0.0.1:1010/api/battles/list
- **API Mother**: http://127.0.0.1:1010/api/mother/list
- **Portainer**: http://127.0.0.1:9100
- **Netdata**: http://127.0.0.1:19999
- **PgAdmin**: http://127.0.0.1:5050
- **Swagger UI**: http://127.0.0.1:8080

## 🧪 Тестирование

### Тест API 4
```bash
curl http://127.0.0.1:1010/api/battles/list
```

### Тест обработки файлов
```bash
# Обработка 3 файлов
curl -X POST "http://127.0.0.1:1010/api/mother/process-batch?limit=3"

# Обработка конкретного файла
curl -X POST "http://127.0.0.1:1010/api/mother/process/53/2655800.tzb"
```

## 🗄️ База данных

### Автоматические миграции
При первом запуске автоматически применяется миграция `V1__create_tables_complete.sql` со всеми таблицами:
- `battles` — основная информация о боях
- `battle_participants` — участники боёв
- `battle_monsters` — монстры в боях
- `battle_loot` — лут из боёв
- `players` — справочник игроков
- `monster_catalog` — справочник монстров

### Ручное применение миграций
```bash
./tools/ctl.sh migrate
```

## 🔄 Новый парсер v2.0

### Интеграция
- **Статус**: ✅ Полностью интегрирован и работает
- **Путь**: `/app/example/parser` в контейнере
- **Дедупликация**: автоматическое удаление дублированных `<BATTLE>` блоков
- **Новые поля**: `map_patch`, `intervened`, `kills`, `damage_total`, `personal_loot`

### Использование
```python
from app.external_parser import run_new_parser

# Парсинг TZB файла
result = run_new_parser('/path/to/battle.tzb')
# Возвращает: battle, participants, monsters, loot_total
```

## 🐛 Устранение проблем

### Если API 4 не запускается
1. Проверьте логи: `docker logs wg-client-api_4-1`
2. Убедитесь, что БД запущена: `docker ps | grep postgres`
3. Примените миграции: `./tools/ctl.sh migrate`

### Если файлы не обрабатываются
1. Проверьте, что `example/parser` скопирован в контейнер
2. Проверьте логи API 4 на ошибки парсера

### Если данные не сохраняются
1. Проверьте подключение к БД
2. Убедитесь, что миграции применены
3. Проверьте логи на ошибки SQL

## 📝 Логи

```bash
# Логи API 4
docker logs wg-client-api_4-1 -f

# Логи API Mother
docker logs wg-client-api_mother-1 -f

# Логи БД
docker logs host-api-service-api_4_db-1 -f

# Все логи через ctl.sh
./tools/ctl.sh logs api_4
./tools/ctl.sh logs api_mother
```

## 🔄 Перезапуск

```bash
# Полный перезапуск
./start_project.sh

# Перезапуск только API 4
./tools/ctl.sh restart api_4

# Перезапуск только API Mother
./tools/ctl.sh restart api_mother
```

## 📚 Документация

- **[MAIN.md](../MAIN.md)** — главный файл знаний
- **[BATTLE_COMPLETE_GUIDE.md](../BATTLE_COMPLETE_GUIDE.md)** — полное руководство по API 4
- **[PARSER_TEST_RESULTS.md](../PARSER_TEST_RESULTS.md)** — результаты тестирования парсера

---

**Версия:** 2.1 (с исправлениями и режимами работы)  
**Статус:** ✅ Полностью работает, исправлен и готов к продакшн  
**Последнее обновление:** 2025-10-04









