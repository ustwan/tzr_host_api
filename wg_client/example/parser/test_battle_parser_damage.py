#!/usr/bin/env python3
"""
Тест обновленного battle_parser.py для анализа урона по ходам
"""

import sys
import json
from battle_parser import BattleParser

def analyze_damage_with_parser(filename):
    """Анализирует урон с помощью обновленного BattleParser"""
    
    parser = BattleParser()
    
    # Читаем файл
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Анализ урона для файла: {filename}")
    print("=" * 80)
    
    # Получаем детальный анализ урона по ходам
    attacks = parser.analyze_damage_by_turns(content)
    
    if not attacks:
        print("Атак с уроном не найдено")
        return
    
    # Группируем по ходам
    turns = {}
    for attack in attacks:
        turn = attack['turn']
        if turn not in turns:
            turns[turn] = []
        turns[turn].append(attack)
    
    # Выводим результаты
    for turn_num in sorted(turns.keys()):
        print(f"\nХОД {turn_num}")
        print("-" * 40)
        
        for attack in sorted(turns[turn_num], key=lambda x: x['frame']):
            victim_info = f" → {attack['victim']}" if attack['victim'] != 'координаты' else " → координаты"
            print(f"Кадр {attack['frame']}: {attack['attacker']}{victim_info}")
            print(f"Тип атаки: {attack['attack_type_name']} (type=\"{attack['attack_type']}\")")
            print(f"Бронебой: {attack['armor_piercing']}")
            print(f"Урон: {attack['normal_damage']}")
            
            if attack['status_code'] and attack['status_damage'] > 0:
                print(f"Спец.Урон: {attack['status_damage']} {attack['status_name']}")
            else:
                print("Спец.Урон: 0")
            
            print(f"Формат HP: {attack['format_type']} (HP=\"{attack['hp_string']}\")")
            print()
    
    # Статистика
    print("=" * 80)
    print("СТАТИСТИКА:")
    print("-" * 40)
    
    total_attacks = len(attacks)
    total_damage = sum(a['total_damage'] for a in attacks)
    
    # Группировка по атакующим
    attackers = {}
    for attack in attacks:
        attacker = attack['attacker']
        if attacker not in attackers:
            attackers[attacker] = {'attacks': 0, 'damage': 0}
        attackers[attacker]['attacks'] += 1
        attackers[attacker]['damage'] += attack['total_damage']
    
    # Группировка по типам урона
    damage_types = {}
    for attack in attacks:
        if attack['status_code']:
            status = attack['status_name']
            if status not in damage_types:
                damage_types[status] = {'count': 0, 'damage': 0}
            damage_types[status]['count'] += 1
            damage_types[status]['damage'] += attack['status_damage']
    
    # Группировка по типам атак
    attack_types = {}
    for attack in attacks:
        attack_type = attack['attack_type_name']
        if attack_type not in attack_types:
            attack_types[attack_type] = {'count': 0, 'damage': 0}
        attack_types[attack_type]['count'] += 1
        attack_types[attack_type]['damage'] += attack['total_damage']
    
    print(f"Всего атак: {total_attacks}")
    print(f"Общий урон: {total_damage}")
    print(f"Ходов с боем: {len(turns)}")
    
    print("\nУрон по игрокам:")
    for attacker, stats in sorted(attackers.items()):
        print(f"  {attacker}: {stats['damage']} урона ({stats['attacks']} атак)")
    
    if damage_types:
        print("\nСпец урон по типам:")
        for damage_type, stats in sorted(damage_types.items()):
            print(f"  {damage_type}: {stats['damage']} урона ({stats['count']} атак)")
    
    if attack_types:
        print("\nУрон по типам атак:")
        for attack_type, stats in sorted(attack_types.items(), key=lambda x: x[1]['damage'], reverse=True):
            print(f"  {attack_type}: {stats['damage']} урона ({stats['count']} атак)")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python3 test_battle_parser_damage.py <файл.tzb>")
        sys.exit(1)
    
    filename = sys.argv[1]
    analyze_damage_with_parser(filename)
