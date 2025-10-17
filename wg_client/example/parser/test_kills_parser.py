#!/usr/bin/env python3
"""
Тестовый скрипт для проверки нового алгоритма подсчета убийств
"""
import sys
from battle_parser import BattleParser

def test_kills_parser(file_path: str):
    parser = BattleParser()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Дедуплицируем файл перед парсингом
    from dedupe_tzb import dedupe_tzb_content
    content = dedupe_tzb_content(content)
    
    # Получаем battle_id из существующего парсера
    battle_info = parser._parse_battle_info(content)
    battle_id = battle_info.get("battle_id", 0)
    
    print(f"=== Анализ убийств для {file_path} ===")
    print(f"Battle ID: {battle_id}")
    print()
    
    # Тестируем оба режима
    for mode in ["frame_only", "accumulate_to_death"]:
        print(f"--- Режим: {mode} ---")
        kills = parser.parse_kills_from_xml(content, battle_id, mode)
        
        print(f"Всего убийств: {len(kills)}")
        
        # Группируем по ходам
        by_turn = {}
        total_damage = 0
        for kill in kills:
            turn = kill.turn
            if turn not in by_turn:
                by_turn[turn] = []
            by_turn[turn].append(kill)
            total_damage += kill.damage
        
        print(f"Суммарный урон: {total_damage}")
        print()
        
        # Выводим по ходам
        for turn in sorted(by_turn.keys()):
            turn_kills = by_turn[turn]
            turn_damage = sum(k.damage for k in turn_kills)
            print(f"Ход {turn}: {len(turn_kills)} убийств, урон {turn_damage}")
            
            for kill in turn_kills:
                print(f"  sf={kill.sf}: {kill.killer} → {kill.victim} — {kill.damage} ({kill.shots} выстрелов)")
        
        print()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python3 test_kills_parser.py <путь_к_tzb_файлу>")
        sys.exit(1)
    
    test_kills_parser(sys.argv[1])
