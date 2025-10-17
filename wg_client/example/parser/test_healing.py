#!/usr/bin/env python3
"""
Тест обработки лечения в HP атрибутах
"""
from battle_parser import BattleParser

def test_healing_parsing():
    parser = BattleParser()
    
    test_cases = [
        ("0:60", 60, "обычный урон"),
        ("0:-52", -52, "общее лечение"),
        ("0:A-15", -15, "DoT урон от отравления (ход 1)"),
        ("0:A-14", -14, "DoT урон от отравления (ход 2)"),
        ("0:B-30", -30, "DoT урон от ожога"),
        ("0:S100", 100, "ударный урон"),
        ("0:O25", 25, "входящее отравление"),
        ("", 0, "пустая строка"),
        ("invalid", 0, "невалидный формат"),
    ]
    
    print("=== ТЕСТ ОБРАБОТКИ УРОНА И ЛЕЧЕНИЯ ===")
    print()
    
    for hp_str, expected, description in test_cases:
        result = parser.parse_damage(hp_str)
        status = "✓" if result == expected else "✗"
        print(f"{status} HP=\"{hp_str}\" → {result} ({description})")
        if result != expected:
            print(f"   Ожидалось: {expected}, получено: {result}")
    
    print()
    print("=== ИНТЕРПРЕТАЦИЯ ===")
    print("Положительные значения: прямой урон")
    print("Отрицательные значения с кодом: DoT урон (A, B и др.) или лечение (без кода)")
    print("Отрицательные значения без кода: лечение")
    print()
    print("=== МЕХАНИКА DoT ===")
    print("A-15 (ход 1) → A-14 (ход 2) → A-13 (ход 3) → ... → исчезает")
    print("Урон от статусных эффектов уменьшается каждый ход")

if __name__ == "__main__":
    test_healing_parsing()
