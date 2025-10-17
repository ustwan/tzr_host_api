#!/usr/bin/env bash
# Исправление конфликтов портов
set -euo pipefail

echo "═══════════════════════════════════════════════════"
echo "  Поиск и освобождение занятых портов"
echo "═══════════════════════════════════════════════════"
echo

# Список портов которые нужны
PORTS=(1010 8081 8082 8083 8084 8085 9000 9100 9101 9102 9107 2019 51820)

echo "🔍 Проверка занятых портов..."
echo

for port in "${PORTS[@]}"; do
    # Проверяем кто занимает порт
    pid=$(sudo lsof -ti :$port 2>/dev/null || true)
    
    if [[ -n "$pid" ]]; then
        # Получаем информацию о процессе
        info=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
        
        # Проверяем это Docker контейнер
        container=$(docker ps --format '{{.Names}}' --filter "publish=$port" 2>/dev/null || true)
        
        if [[ -n "$container" ]]; then
            echo "⚠️  Порт $port занят контейнером: $container"
            echo "   Остановка контейнера..."
            docker stop "$container" 2>/dev/null || true
        else
            echo "⚠️  Порт $port занят процессом: $info (PID: $pid)"
            echo "   Команда для остановки: sudo kill $pid"
        fi
    else
        echo "✅ Порт $port свободен"
    fi
done

echo
echo "═══════════════════════════════════════════════════"
echo "  Готово! Теперь можно запускать сервисы"
echo "═══════════════════════════════════════════════════"
echo
echo "Запустите:"
echo "  sudo bash tools/ctl.sh start-all"
echo

