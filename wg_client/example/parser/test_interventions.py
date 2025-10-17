#!/usr/bin/env python3
"""
Тест анализа вмешательств в бой в battle_parser.py
"""

import sys
import json
from battle_parser import BattleParser

def analyze_interventions_with_parser(filename):
    """Анализирует вмешательства в бой с помощью BattleParser"""
    
    parser = BattleParser()
    
    # Читаем файл
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Анализ вмешательств в бой для файла: {filename}")
    print("=" * 80)
    
    # Получаем анализ вмешательств
    result = parser.analyze_battle_interventions(content)
    
    if 'error' in result:
        print(f"Ошибка: {result['error']}")
        return
    
    # Выводим изначальных участников
    initial = result['initial_participants']
    print("ИЗНАЧАЛЬНЫЕ УЧАСТНИКИ БОЛЯ:")
    print("-" * 40)
    print(f"Игроки ({len(initial['players'])}):")
    for player in initial['players']:
        print(f"  - {player}")
    
    print(f"\nМонстры ({len(initial['monsters'])}):")
    for monster in initial['monsters']:
        print(f"  - {monster}")
    
    print(f"\nВсего участников: {initial['total']}")
    
    # Выводим вмешательства
    interventions = result['interventions']
    if interventions:
        print(f"\n" + "=" * 80)
        print("ВМЕШАТЕЛЬСТВА В БОЙ:")
        print("-" * 40)
        
        for intervention in interventions:
            participant_type = "Игрок" if intervention['type'] == 'player' else "Монстр"
            frame_info = f" (кадр {intervention['appearance_frame']})" if intervention['appearance_frame'] else ""
            actions_info = " с действиями" if intervention['has_actions'] else " без действий"
            
            print(f"Ход {intervention['turn']:2d}: {participant_type} '{intervention['login']}'{frame_info}{actions_info}")
    
    # Статистика
    summary = result['intervention_summary']
    print(f"\n" + "=" * 80)
    print("СТАТИСТИКА ВМЕШАТЕЛЬСТВ:")
    print("-" * 40)
    print(f"Всего вмешательств: {summary['total_interventions']}")
    print(f"Вмешательства игроков: {summary['player_interventions']}")
    print(f"Вмешательства монстров: {summary['monster_interventions']}")
    print(f"Ходов с вмешательствами: {summary['turns_with_interventions']}")
    
    if interventions:
        print(f"\nДетали по ходам:")
        turns_with_interventions = {}
        for intervention in interventions:
            turn = intervention['turn']
            if turn not in turns_with_interventions:
                turns_with_interventions[turn] = []
            turns_with_interventions[turn].append(intervention)
        
        for turn in sorted(turns_with_interventions.keys()):
            participants = turns_with_interventions[turn]
            players = [p for p in participants if p['type'] == 'player']
            monsters = [p for p in participants if p['type'] == 'monster']
            
            print(f"  Ход {turn}: ", end="")
            if players:
                print(f"{len(players)} игрок(ов)", end="")
            if monsters:
                if players:
                    print(f", {len(monsters)} монстр(ов)", end="")
                else:
                    print(f"{len(monsters)} монстр(ов)", end="")
            print()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python3 test_interventions.py <файл.tzb>")
        sys.exit(1)
    
    filename = sys.argv[1]
    analyze_interventions_with_parser(filename)
