#!/usr/bin/env bash
# Тестовый запуск API 5 локально

echo "🚀 API 5 - Shop Parser: Тестовый запуск"
echo "=========================================="

# Проверка виртуального окружения
if [[ ! -d "venv" ]]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

source venv/bin/activate

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip install -q -r requirements.txt

# Запуск тестов
echo ""
echo "🧪 Запуск тестов..."
pytest tests/ -v

# Проверка результата
if [[ $? -eq 0 ]]; then
    echo ""
    echo "✅ Все тесты прошли успешно!"
    echo ""
    echo "Для запуска API выполните:"
    echo "  python app/main.py"
    echo ""
    echo "Для запуска воркеров:"
    echo "  python shop_workers/run_workers.py"
else
    echo ""
    echo "❌ Тесты провалились"
    exit 1
fi


