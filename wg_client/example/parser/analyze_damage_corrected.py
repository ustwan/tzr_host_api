#!/usr/bin/env python3
"""
ИСПРАВЛЕННЫЙ анализ урона по ходам в файле .tzb
Показывает кто кому нанес какой урон в каждом ходу
"""

import re
import sys
from collections import defaultdict

def parse_damage(hp_str):
    """Парсит HP строку и возвращает урон"""
    if not hp_str:
        return 0
    
    # Простой формат HP="60"
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
    print("=" * 80)
    
    total_damage_by_player = defaultdict(int)
    
    for turn_num, turn_content in turns:
        print(f"\nХОД {turn_num}:")
        print("-" * 40)
        
        # Найдем всех пользователей в этом ходу (только с содержимым, не самозакрывающиеся)
        user_pattern = r'<USER login="([^"]+)"[^>]*>(.*?)</USER>'
        users = re.findall(user_pattern, turn_content, re.DOTALL)
        # Фильтруем только пользователей с непустым содержимым
        users = [(login, content) for login, content in users if content.strip()]
        
        turn_attacks = []
        
        for attacker_login, user_content in users:
            # Найдем все атаки этого пользователя
            attack_pattern = r'<a sf="(\d+)" t="5"[^>]*(?:login="([^"]+)"[^>]*)?HP="([^"]+)"[^>]*/?>'
            attacks = re.findall(attack_pattern, user_content)
            
            for sf, victim_login, hp_str in attacks:
                damage = parse_damage(hp_str)
                if damage > 0:
                    # attacker_login - это владелец USER блока (атакующий)
                    # victim_login - это login в атрибуте атаки (жертва)
                    victim = victim_login if victim_login else "координаты/область"
                    turn_attacks.append({
                        'sf': int(sf),
                        'attacker': attacker_login,
                        'victim': victim,
                        'damage': damage,
                        'hp_str': hp_str
                    })
                    total_damage_by_player[attacker_login] += damage
        
        # Выводим атаки в этом ходу, отсортированные по кадрам
        if turn_attacks:
            for attack in sorted(turn_attacks, key=lambda x: x['sf']):
                victim_info = f" -> {attack['victim']}" if attack['victim'] != 'координаты/область' else " (по координатам/области)"
                print(f"  Кадр {attack['sf']:2d}: {attack['attacker']}{victim_info} урон {attack['damage']} (HP=\"{attack['hp_str']}\")")
        else:
            print("  Урона не было")
    
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ СТАТИСТИКА УРОНА:")
    print("-" * 40)
    for player, total_damage in sorted(total_damage_by_player.items()):
        print(f"{player}: {total_damage} урона")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python3 analyze_damage_corrected.py <файл.tzb>")
        sys.exit(1)
    
    filename = sys.argv[1]
    analyze_damage_by_turns(filename)
