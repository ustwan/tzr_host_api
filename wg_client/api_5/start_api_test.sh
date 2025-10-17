#!/usr/bin/env bash
# Запуск API 5 для локального тестирования

echo "🚀 API 5 - Shop Parser: Локальный запуск"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден"
    exit 1
fi

# Установка зависимостей
echo "📦 Проверка зависимостей..."
pip install -q fastapi uvicorn sqlalchemy psycopg2-binary lxml pydantic 2>/dev/null

# Установка переменных окружения для теста
export DB_MODE=test
export DB_API5_TEST_HOST=localhost
export DB_API5_TEST_PORT=6013
export SOVA_MOSCOW_KEY=test_key
export SOVA_OASIS_KEY=test_key
export SOVA_NEVA_KEY=test_key

echo "✅ Зависимости установлены"
echo ""
echo "🌐 Запуск FastAPI на http://localhost:8085"
echo ""
echo "Endpoints доступны:"
echo "  📊 Health:     http://localhost:8085/healthz"
echo "  📦 Items:      http://localhost:8085/items/list"
echo "  📸 Snapshots:  http://localhost:8085/snapshots/latest"
echo "  📚 Swagger UI: http://localhost:8085/docs"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Запуск API
python3 app/main.py







