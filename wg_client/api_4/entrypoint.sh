#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║        🚀 API 4 ENTRYPOINT                                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Функция для проверки доступности БД
wait_for_db() {
    echo "⏳ Ждём подключения к БД..."
    
    # Определяем параметры подключения на основе DB_MODE
    if [ "${DB_MODE}" = "prod" ]; then
        DB_HOST="${DB_API4_PROD_HOST}"
        DB_PORT="${DB_API4_PROD_PORT}"
        DB_NAME="${DB_API4_PROD_NAME}"
        DB_USER="${DB_API4_PROD_USER}"
    else
        DB_HOST="${DB_API4_TEST_HOST}"
        DB_PORT="${DB_API4_TEST_PORT}"
        DB_NAME="${DB_API4_TEST_NAME}"
        DB_USER="${DB_API4_TEST_USER}"
    fi
    
    echo "   БД: ${DB_HOST}:${DB_PORT}/${DB_NAME} (режим: ${DB_MODE:-test})"
    
    # Ждём макс 60 секунд
    for i in {1..60}; do
        if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" > /dev/null 2>&1; then
            echo "✅ БД доступна!"
            return 0
        fi
        [ $((i % 10)) -eq 0 ] && echo "   ... ${i} сек прошло"
        sleep 1
    done
    
    echo "❌ БД недоступна после 60 секунд"
    return 1
}

# Функция для применения миграций
apply_migrations() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "🔄 Применение миграций БД..."
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    
    if [ -f "/app/apply_migrations.sh" ]; then
        bash /app/apply_migrations.sh
        if [ $? -eq 0 ]; then
            echo "✅ Миграции применены успешно"
        else
            echo "⚠️  Миграции завершились с ошибками (возможно уже применены)"
        fi
    else
        echo "⚠️  Скрипт миграций не найден, пропускаем..."
    fi
    
    echo ""
}

# Проверка XML Workers (если включён XML mode)
check_xml_workers() {
    if [ "${ENABLE_XML_SYNC_ON_START}" = "true" ]; then
        echo "═══════════════════════════════════════════════════════════════════"
        echo "🌐 Проверка XML Workers..."
        echo "═══════════════════════════════════════════════════════════════════"
        echo ""
        echo "   XML Sync включён: будет использоваться для загрузки логов"
        echo ""
    fi
}

# Основная логика
main() {
    # Ждём БД
    if ! wait_for_db; then
        echo "❌ Не удалось подключиться к БД, запуск прерван"
        exit 1
    fi
    
    # Применяем миграции
    apply_migrations
    
    # Проверяем XML Workers
    check_xml_workers
    
    echo "═══════════════════════════════════════════════════════════════════"
    echo "🚀 Запуск API 4..."
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    
    # Запускаем приложение
    exec "$@"
}

# Запуск
main "$@"




