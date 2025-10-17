#!/bin/bash

echo "🗜️ СЖАТИЕ RAW → GZ (только новые файлы)"
echo "========================================"
echo ""

RAW_DIR="./data/btl/raw"
GZ_DIR="./data/btl/gz"

# Подсчитываем общее количество файлов для сжатия
echo "📊 Подсчитываю файлы для сжатия..."
total=0
to_compress=0

for raw_file in $(find "$RAW_DIR" -type f -name "*.tzb"); do
    total=$((total + 1))
    
    # Получаем shard и battle_id
    shard=$(basename $(dirname "$raw_file"))
    battle_id=$(basename "$raw_file" .tzb)
    
    # Проверяем, есть ли уже .gz файл
    gz_file="$GZ_DIR/$shard/$battle_id.tzb.gz"
    
    if [ ! -f "$gz_file" ]; then
        to_compress=$((to_compress + 1))
    fi
done

echo "📂 Всего RAW файлов: $total"
echo "🆕 Нужно сжать: $to_compress"
echo "✅ Уже есть в GZ: $((total - to_compress))"
echo ""

if [ $to_compress -eq 0 ]; then
    echo "✅ Все файлы уже сжаты!"
    exit 0
fi

echo "🚀 Начинаю сжатие (8 параллельных потоков)..."
echo ""

# Создаём временный файл со списком файлов для сжатия
temp_list=$(mktemp)

for raw_file in $(find "$RAW_DIR" -type f -name "*.tzb"); do
    shard=$(basename $(dirname "$raw_file"))
    battle_id=$(basename "$raw_file" .tzb)
    gz_file="$GZ_DIR/$shard/$battle_id.tzb.gz"
    
    if [ ! -f "$gz_file" ]; then
        echo "$raw_file" >> "$temp_list"
    fi
done

# Функция для сжатия одного файла
compress_file() {
    raw_file=$1
    shard=$(basename $(dirname "$raw_file"))
    battle_id=$(basename "$raw_file" .tzb)
    gz_dir="$GZ_DIR/$shard"
    gz_file="$gz_dir/$battle_id.tzb.gz"
    
    # Создаём директорию если нужно
    mkdir -p "$gz_dir"
    
    # Сжимаем
    if gzip -c "$raw_file" > "$gz_file" 2>/dev/null; then
        # Проверяем что gz-файл создан
        if [ -f "$gz_file" ]; then
            # Удаляем raw
            rm "$raw_file" 2>/dev/null
            echo "✅ $battle_id"
        else
            echo "❌ $battle_id (gz не создан)"
        fi
    else
        echo "❌ $battle_id (ошибка сжатия)"
    fi
}

export -f compress_file
export GZ_DIR

# Запускаем параллельное сжатие
cat "$temp_list" | xargs -P 8 -I {} bash -c 'compress_file "{}"'

# Удаляем временный файл
rm "$temp_list"

echo ""
echo "========================================"
echo "✅ СЖАТИЕ ЗАВЕРШЕНО!"
echo ""
echo "📊 Финальная статистика:"
echo "RAW: $(find "$RAW_DIR" -type f -name "*.tzb" 2>/dev/null | wc -l | xargs) файлов"
echo "GZ:  $(find "$GZ_DIR" -type f -name "*.gz" 2>/dev/null | wc -l | xargs) файлов"
echo ""
du -sh "$RAW_DIR" "$GZ_DIR" 2>/dev/null




