#!/usr/bin/env python3
"""
Скрипт для получения карты боя из API

Использование:
    python3 get_battle_map.py 3697692
    python3 get_battle_map.py 3697692 --json
    python3 get_battle_map.py 3697692 --tokens
"""

import sys
import requests
import xml.etree.ElementTree as ET
import json
from typing import Dict, List, Optional, Tuple

API_BASE = "http://localhost:8084"


def get_battle_map(battle_id: int) -> Optional[Dict]:
    """Получить карту боя через API"""
    
    # 1. Получаем XML
    url = f"{API_BASE}/battle/{battle_id}/raw"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 404:
            print(f"❌ Бой {battle_id} не найден в системе", file=sys.stderr)
            return None
        
        if response.status_code != 200:
            print(f"❌ Ошибка API: {response.status_code}", file=sys.stderr)
            try:
                error = response.json()
                print(f"   Детали: {error.get('detail', 'Unknown error')}", file=sys.stderr)
            except:
                print(f"   {response.text[:200]}", file=sys.stderr)
            return None
        
        # 2. Парсим XML
        xml_content = response.content
        
        try:
            tree = ET.fromstring(xml_content)
        except ET.ParseError as e:
            print(f"❌ Ошибка парсинга XML: {e}", file=sys.stderr)
            return None
        
        # 3. Ищем тег <map>
        map_elem = tree.find('.//map')
        
        if map_elem is None:
            print(f"⚠️  Тег <map> не найден в XML боя {battle_id}", file=sys.stderr)
            return None
        
        # 4. Извлекаем данные карты
        width = int(map_elem.get('width', 0))
        height = int(map_elem.get('height', 0))
        
        # Ищем данные карты (могут быть в <data> или непосредственно в <map>)
        data_elem = map_elem.find('data')
        if data_elem is not None and data_elem.text:
            map_data = data_elem.text.strip()
        elif map_elem.text:
            map_data = map_elem.text.strip()
        else:
            print(f"⚠️  Данные карты не найдены в теге <map>", file=sys.stderr)
            return None
        
        # 5. Разбиваем карту на строки
        map_rows = [line for line in map_data.split('\n') if line.strip()]
        
        # 6. Извлекаем уникальные токены (символы)
        tokens = set()
        for row in map_rows:
            tokens.update(row)
        
        # 7. Подсчитываем частоту токенов
        token_counts = {}
        for row in map_rows:
            for char in row:
                token_counts[char] = token_counts.get(char, 0) + 1
        
        return {
            "battle_id": battle_id,
            "width": width,
            "height": height,
            "actual_height": len(map_rows),
            "actual_width": max(len(row) for row in map_rows) if map_rows else 0,
            "map_data": map_rows,
            "tokens": sorted(list(tokens)),
            "token_counts": token_counts,
            "total_cells": width * height
        }
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Невозможно подключиться к API ({API_BASE})", file=sys.stderr)
        print(f"   Убедитесь что API_4 запущен", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def print_map_visual(map_data: Dict):
    """Красивый вывод карты"""
    print(f"\n{'='*60}")
    print(f"🗺️  КАРТА БОЯ #{map_data['battle_id']}")
    print(f"{'='*60}\n")
    
    print(f"📐 Размер: {map_data['width']}x{map_data['height']} (заявленный)")
    print(f"📐 Фактический: {map_data['actual_width']}x{map_data['actual_height']}")
    print(f"📊 Всего клеток: {map_data['total_cells']}\n")
    
    print(f"🔤 ТОКЕНЫ КАРТЫ ({len(map_data['tokens'])} уникальных):")
    for token in map_data['tokens']:
        count = map_data['token_counts'].get(token, 0)
        percent = (count / map_data['total_cells'] * 100) if map_data['total_cells'] > 0 else 0
        
        # Визуальное представление токена
        if token == ' ':
            token_display = "' ' (пробел)"
        elif token == '\t':
            token_display = "'\\t' (таб)"
        else:
            token_display = f"'{token}'"
        
        print(f"  {token_display:15} → {count:5} клеток ({percent:5.2f}%)")
    
    print(f"\n{'─'*60}")
    print(f"📍 КАРТА:")
    print(f"{'─'*60}\n")
    
    for i, row in enumerate(map_data['map_data'], 1):
        print(f"{i:3} | {row}")
    
    print(f"\n{'='*60}\n")


def print_map_tokens(map_data: Dict):
    """Вывод только токенов"""
    print(json.dumps(map_data['tokens'], indent=2))


def print_map_json(map_data: Dict):
    """Вывод в JSON формате"""
    # Убираем map_data для компактности (можно оставить если нужно)
    output = {
        "battle_id": map_data['battle_id'],
        "width": map_data['width'],
        "height": map_data['height'],
        "tokens": map_data['tokens'],
        "token_counts": map_data['token_counts']
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def main():
    if len(sys.argv) < 2:
        print("Использование: python3 get_battle_map.py <battle_id> [--json|--tokens]")
        print("\nПримеры:")
        print("  python3 get_battle_map.py 3697692          # Визуальный вывод")
        print("  python3 get_battle_map.py 3697692 --json   # JSON формат")
        print("  python3 get_battle_map.py 3697692 --tokens # Только токены")
        sys.exit(1)
    
    try:
        battle_id = int(sys.argv[1])
    except ValueError:
        print(f"❌ Неверный battle_id: {sys.argv[1]}", file=sys.stderr)
        sys.exit(1)
    
    output_mode = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Получаем данные карты
    map_data = get_battle_map(battle_id)
    
    if map_data is None:
        sys.exit(1)
    
    # Выводим в зависимости от режима
    if output_mode == '--json':
        print_map_json(map_data)
    elif output_mode == '--tokens':
        print_map_tokens(map_data)
    else:
        print_map_visual(map_data)


if __name__ == '__main__':
    main()





