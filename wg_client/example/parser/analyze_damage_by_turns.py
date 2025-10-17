#!/usr/bin/env python3
"""
Анализ урона по ходам в файле .tzb
Показывает кто кому нанес какой урон в каждом ходу
"""

import re
import sys
from collections import defaultdict

def parse_damage(hp_str):
    """Парсит HP строку и возвращает урон"""
    if not hp_str:
        return 0
    
    # Простой формат HP="0:60" или HP="60"
    simple_match = re.match(r'^(\d+)$', hp_str)
    if simple_match:
        return int(simple_match.group(1))
    
    # Формат HP="0:60" 
    colon_match = re.match(r'^0:(\d+)$', hp_str)
    if colon_match:
        return int(colon_match.group(1))
    
    # Расширенный формат HP="0:18:N4" - HP="бронебойный:обычный:код_урон"
    extended_match = re.match(r'^(\d+):(\d+):([A-Z])(-?\d+)$', hp_str)
    if extended_match:
        try:
            armor_piercing = int(extended_match.group(1))
            normal_damage = int(extended_match.group(2))
            status_code = extended_match.group(3)
            status_damage = int(extended_match.group(4))
            
            # Суммируем обычный урон и абсолютное значение урона от статуса
            total_damage = normal_damage + abs(status_damage)
            return total_damage
        except ValueError:
            return 0
    
    # DoT формат HP="0:A-15" (урон от отравления)
    dot_match = re.match(r'^0:([A-Z])(-?\d+)$', hp_str)
    if dot_match:
        status_code = dot_match.group(1)
        status_damage = int(dot_match.group(2))
        # Отрицательные значения с кодом - это DoT урон
        if status_damage < 0:
            return abs(status_damage)
        else:
            return status_damage
    
    return 0

def analyze_damage_by_turns(filename):
    """Анализирует урон по ходам"""
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Дедупликация: обрезаем содержимое от второго <BATTLE> тега
    second_battle_pos = content.find('<BATTLE', content.find('<BATTLE') + 1)
    if second_battle_pos != -1:
        print(f"Обнаружен дублированный BATTLE блок на позиции {second_battle_pos}, обрезаем")
        content = content[:second_battle_pos]
    
    # Найдем все ходы
    turn_pattern = r'<TURN turn="(\d+)"[^>]*>(.*?)</TURN>'
    turns = re.findall(turn_pattern, content, re.DOTALL)
    
    print(f"Анализ урона по ходам для файла: {filename}")
    print("=" * 60)
    
    total_damage_by_player = defaultdict(int)
    
    for turn_num, turn_content in turns:
        print(f"\nХОД {turn_num}:")
        print("-" * 30)
        
        # Найдем все атаки в этом ходу (как внутри USER блоков, так и вне их)
        attack_pattern = r'<a sf="(\d+)" t="5"[^>]*(?:login="([^"]+)"[^>]*)?HP="([^"]+)"[^>]*/?>'
        attacks = re.findall(attack_pattern, turn_content)
        
        turn_damage = defaultdict(list)
        
        # Также найдем всех пользователей в этом ходу для определения атакующего
        user_pattern = r'<USER login="([^"]+)"[^>]*>(.*?)</USER>'
        users = re.findall(user_pattern, turn_content, re.DOTALL)
        
        # Создадим словарь атак по пользователям
        user_attacks = {}
        for login, user_content in users:
            user_attack_pattern = r'<a sf="(\d+)" t="5"[^>]*(?:login="([^"]+)"[^>]*)?HP="([^"]+)"[^>]*/?>'
            user_attacks[login] = re.findall(user_attack_pattern, user_content)
        
        # Обработаем атаки внутри USER блоков
        for attacker, attacks_list in user_attacks.items():
            for sf, target, hp_str in attacks_list:
                damage = parse_damage(hp_str)
                if damage > 0:
                    # В атаках login указывает на жертву, а атакующий - владелец USER блока
                    actual_target = target if target else 'координаты/область'
                    turn_damage[attacker].append({
                        'sf': int(sf),
                        'target': actual_target,
                        'damage': damage,
                        'hp_str': hp_str
                    })
                    total_damage_by_player[attacker] += damage
        
        # Обработаем атаки вне USER блоков
        for sf, target, hp_str in attacks:
            # Проверим, не обработали ли мы уже эту атаку
            already_processed = False
            for user_attacks_list in user_attacks.values():
                if (sf, target, hp_str) in user_attacks_list:
                    already_processed = True
                    break
            
            if not already_processed:
                damage = parse_damage(hp_str)
                if damage > 0:
                    turn_damage['неизвестный'].append({
                        'sf': int(sf),
                        'target': target if target else 'неизвестно',
                        'damage': damage,
                        'hp_str': hp_str
                    })
                    total_damage_by_player['неизвестный'] += damage
        
        # Выводим урон в этом ходу
        if turn_damage:
            for attacker, attacks in turn_damage.items():
                for attack in sorted(attacks, key=lambda x: x['sf']):
                    target_info = f" -> {attack['target']}" if attack['target'] != 'координаты/область' else " (по координатам/области)"
                    print(f"  Кадр {attack['sf']:2d}: {attacker}{target_info} урон {attack['damage']} (HP=\"{attack['hp_str']}\")")
        else:
            print("  Урона не было")
    
    print("\n" + "=" * 60)
    print("ИТОГОВАЯ СТАТИСТИКА УРОНА:")
    print("-" * 30)
    for player, total_damage in sorted(total_damage_by_player.items()):
        print(f"{player}: {total_damage} урона")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python3 analyze_damage_by_turns.py <файл.tzb>")
        sys.exit(1)
    
    filename = sys.argv[1]
    analyze_damage_by_turns(filename)
