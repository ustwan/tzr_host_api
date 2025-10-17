#!/usr/bin/env python3
"""
Демонстрация извлечения токенов из карты
Упрощенная версия для понимания логики
"""

# Пример карты
example_map = """
#######################
#.....................#
#.....T...............#
#....TTT..............#
#.....T......W........#
#...........WWW.......#
#............W........#
#.....................#
#######################
"""

def extract_tokens_simple(map_data: str):
    """Простой способ извлечения токенов"""
    
    print("🔍 ШАГ 1: Исходная карта")
    print(map_data)
    print()
    
    # Шаг 1: Разбиваем на строки
    map_rows = [line for line in map_data.split('\n') if line.strip()]
    
    print(f"🔍 ШАГ 2: Разбили на {len(map_rows)} строк")
    for i, row in enumerate(map_rows, 1):
        print(f"  {i:2} | {row}")
    print()
    
    # Шаг 2: Извлекаем уникальные токены
    tokens = set()
    for row in map_rows:
        tokens.update(row)  # Добавляем все символы из строки
    
    print(f"🔍 ШАГ 3: Нашли {len(tokens)} уникальных токенов")
    print(f"  Токены: {sorted(list(tokens))}")
    print()
    
    # Шаг 3: Подсчитываем частоту
    token_counts = {}
    for row in map_rows:
        for char in row:
            token_counts[char] = token_counts.get(char, 0) + 1
    
    print("🔍 ШАГ 4: Подсчитали частоту каждого токена")
    
    # Вычисляем общее количество клеток
    total_cells = sum(token_counts.values())
    
    # Сортируем по частоте (от большего к меньшему)
    sorted_tokens = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)
    
    for token, count in sorted_tokens:
        percent = (count / total_cells * 100)
        
        # Красивое отображение
        if token == ' ':
            token_display = "' ' (пробел)"
        elif token == '\t':
            token_display = "'\\t' (таб)"
        else:
            token_display = f"'{token}'"
        
        # Визуальная полоса
        bar_length = int(percent / 2)  # Масштаб 1% = 0.5 символа
        bar = '█' * bar_length
        
        print(f"  {token_display:15} {count:4} клеток ({percent:5.2f}%) {bar}")
    
    print()
    print(f"📊 Всего клеток: {total_cells}")
    print()
    
    return {
        "tokens": sorted(list(tokens)),
        "token_counts": token_counts,
        "total_cells": total_cells
    }


def extract_tokens_verbose(map_data: str):
    """Подробная версия с пояснениями"""
    
    print("="*60)
    print("ПОДРОБНОЕ ОБЪЯСНЕНИЕ: Как извлекаются токены")
    print("="*60)
    print()
    
    # Берём только первую строку для примера
    map_rows = [line for line in map_data.split('\n') if line.strip()]
    first_row = map_rows[0]
    
    print(f"Возьмём первую строку: \"{first_row}\"")
    print()
    
    # Показываем что делает tokens.update()
    tokens = set()
    
    print("Итерируем по каждому символу:")
    print()
    
    for i, char in enumerate(first_row, 1):
        tokens.add(char)
        print(f"  Символ {i:2}: '{char}' → tokens = {sorted(list(tokens))}")
        
        if i == 10:
            print("  ... (остальные символы аналогично)")
            break
    
    # Добавляем остальные
    tokens.update(first_row[10:])
    print()
    print(f"После обработки всей строки: {sorted(list(tokens))}")
    print()
    
    # Теперь подсчёт
    print("-"*60)
    print("Подсчёт частоты символа '#':")
    print("-"*60)
    print()
    
    count = 0
    for row_num, row in enumerate(map_rows, 1):
        row_count = row.count('#')
        count += row_count
        print(f"  Строка {row_num:2}: {row_count:2} символов '#' → всего: {count}")
        
        if row_num == 5:
            print("  ... (остальные строки аналогично)")
            break
    
    # Финальный подсчёт
    total_hash = sum(row.count('#') for row in map_rows)
    print()
    print(f"ИТОГО символов '#': {total_hash}")
    print()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--verbose':
        extract_tokens_verbose(example_map)
    else:
        result = extract_tokens_simple(example_map)
        
        print("="*60)
        print("РЕЗУЛЬТАТ (JSON):")
        print("="*60)
        print()
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))





