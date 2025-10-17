#!/usr/bin/env python3
"""
Тест анализа смены стоек в battle_parser.py
"""

import sys
from battle_parser import BattleParser

def analyze_stances_with_parser(filename):
    """Анализирует смены стоек с помощью BattleParser"""
    
    parser = BattleParser()
    
    # Читаем файл
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Анализ смены стоек для файла: {filename}")
    print("=" * 80)
    
    # Получаем анализ смены стоек
    stance_changes = parser.analyze_stance_changes(content)
    
    if not stance_changes:
        print("Смен стоек не найдено")
        return
    
    # Группируем по ходам
    turns = {}
    for change in stance_changes:
        turn = change['turn']
        if turn not in turns:
            turns[turn] = []
        turns[turn].append(change)
    
    # Выводим результаты
    for turn_num in sorted(turns.keys()):
        print(f"\nХОД {turn_num}")
        print("-" * 40)
        
        for change in sorted(turns[turn_num], key=lambda x: x['frame']):
            run_info = f" (run=\"{change['run_value']}\")" if change['run_value'] and change['run_value'] != 'escape' else ""
            print(f"Кадр {change['frame']:2d}: {change['player']} → {change['stance_name']}{run_info}")
    
    # Статистика
    print("\n" + "=" * 80)
    print("СТАТИСТИКА СМЕН СТОЕК:")
    print("-" * 40)
    
    total_changes = len(stance_changes)
    
    # Группировка по игрокам
    players = {}
    for change in stance_changes:
        player = change['player']
        if player not in players:
            players[player] = {'changes': 0, 'stances': []}
        players[player]['changes'] += 1
        players[player]['stances'].append(change['stance_name'])
    
    # Группировка по типам стоек
    stance_types = {}
    for change in stance_changes:
        stance = change['stance_name']
        if stance not in stance_types:
            stance_types[stance] = 0
        stance_types[stance] += 1
    
    print(f"Всего смен стоек: {total_changes}")
    print(f"Ходов со сменами стоек: {len(turns)}")
    
    print("\nСмены по игрокам:")
    for player, stats in sorted(players.items()):
        unique_stances = len(set(stats['stances']))
        print(f"  {player}: {stats['changes']} смен ({unique_stances} разных стоек)")
    
    print("\nЧастота использования стоек:")
    for stance, count in sorted(stance_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {stance}: {count} раз")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python3 test_stance_analysis.py <файл.tzb>")
        sys.exit(1)
    
    filename = sys.argv[1]
    analyze_stances_with_parser(filename)
