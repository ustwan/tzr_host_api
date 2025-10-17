#!/bin/bash
# Скрипт для применения миграций БД

set -e

DB_HOST=${DB_API4_TEST_HOST:-api_4_db}
DB_PORT=${DB_API4_TEST_PORT:-5432}
DB_NAME=${DB_API4_TEST_NAME:-api4_battles}
DB_USER=${DB_API4_TEST_USER:-api4_user}
DB_PASSWORD=${DB_API4_TEST_PASSWORD:-api4_pass}

echo "Применение миграций для БД $DB_NAME на $DB_HOST:$DB_PORT"

# Применяем полную миграцию
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f /app/migrations/V1__create_tables_complete.sql

echo "Миграции применены успешно"









