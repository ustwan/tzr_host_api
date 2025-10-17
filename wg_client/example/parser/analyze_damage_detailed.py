#!/usr/bin/env python3
"""
Детальный анализ урона по ходам в файле .tzb
Показывает урон в формате: Кадр X: Атакующий → Жертва, Бронебой, Урон, Спец.Урон
"""

import re
import sys
from collections import defaultdict

def parse_damage_detailed(hp_str):
    """Парсит HP строку и возвращает детальную информацию об уроне"""
    if not hp_str:
        return None
    
    # Простой формат HP="60"
    simple_match = re.match(r'^(\d+)$', hp_str)
    if simple_match:
        return {
            'armor_piercing': 0,
            'normal_damage': int(simple_match.group(1)),
            'status_code': None,
            'status_damage': 0,
            'total_damage': int(simple_match.group(1))
        }
    
    # Формат HP="0:60" 
    colon_match = re.match(r'^0:(\d+)$', hp_str)
    if colon_match:
        return {
            'armor_piercing': 0,
            'normal_damage': int(colon_match.group(1)),
            'status_code': None,
            'status_damage': 0,
            'total_damage': int(colon_match.group(1))
        }
    
    # Расширенный формат HP="0:18:N4" - HP="бронебойный:обычный:код_урон"
    extended_match = re.match(r'^(\d+):(\d+):([A-Z])(-?\d+)$', hp_str)
    if extended_match:
        try:
            armor_piercing = int(extended_match.group(1))
            normal_damage = int(extended_match.group(2))
            status_code = extended_match.group(3)
            status_damage = int(extended_match.group(4))
            
            return {
                'armor_piercing': armor_piercing,
                'normal_damage': normal_damage,
                'status_code': status_code,
                'status_damage': abs(status_damage),
                'total_damage': normal_damage + abs(status_damage)
            }
        except ValueError:
            return None
    
    # DoT формат HP="0:A-15" (урон от отравления)
    dot_match = re.match(r'^0:([A-Z])(-?\d+)$', hp_str)
    if dot_match:
        status_code = dot_match.group(1)
        status_damage = int(dot_match.group(2))
        
        return {
            'armor_piercing': 0,
            'normal_damage': 0,
            'status_code': status_code,
            'status_damage': abs(status_damage),
            'total_damage': abs(status_damage)
        }
    
    return None

def get_status_name(code):
    """Возвращает название статуса по коду"""
    status_names = {
        'A': 'отравление',
        'O': 'отравление входящее',
        'B': 'ожог',
        'D': 'ослепление',
        'P': 'паралич',
        'N': 'паника',
        'H': 'галлюцинации',
        'C': 'контузия',
        'Z': 'зомбирование',
        'V': 'биологическое заражение',
        'S': 'ударное',
        'E': 'энергетическое'
    }
    return status_names.get(code, f'неизвестный({code})')

def analyze_damage_detailed(filename):
    """Анализирует урон по ходам в детальном формате"""
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Дедупликация: обрезаем содержимое от второго <BATTLE> тега
    second_battle_pos = content.find('<BATTLE', content.find('<BATTLE') + 1)
    if second_battle_pos != -1:
        print(f"Обнаружен дублированный BATTLE блок, обрезаем")
        content = content[:second_battle_pos]
    
    # Найдем все ходы
    turn_pattern = r'<TURN turn="(\d+)"[^>]*>(.*?)</TURN>'
    turns = re.findall(turn_pattern, content, re.DOTALL)
    
    print(f"Детальный анализ урона для файла: {filename}")
    print("=" * 80)
    
    for turn_num, turn_content in turns:
        # Найдем всех пользователей в этом ходу (только с содержимым)
        user_pattern = r'<USER login="([^"]+)"[^>]*>(.*?)</USER>'
        users = re.findall(user_pattern, turn_content, re.DOTALL)
        # Фильтруем только пользователей с непустым содержимым
        users = [(login, content) for login, content in users if content.strip()]
        
        turn_attacks = []
        
        for attacker_login, user_content in users:
            # Найдем все атаки этого пользователя
            attack_pattern = r'<a sf="(\d+)" t="5"[^>]*HP="([^"]+)"[^>]*/?>'
            attacks = re.findall(attack_pattern, user_content)
            
            # Для каждой атаки отдельно ищем login
            detailed_attacks = []
            for sf, hp_str in attacks:
                # Найдем полную строку атаки для извлечения login
                full_attack_pattern = rf'<a sf="{sf}" t="5"[^>]*>'
                full_match = re.search(full_attack_pattern, user_content)
                if full_match:
                    full_attack = full_match.group(0)
                    login_match = re.search(r'login="([^"]+)"', full_attack)
                    victim_login = login_match.group(1) if login_match else None
                    detailed_attacks.append((sf, victim_login, hp_str))
            
            attacks = detailed_attacks
            
            for sf, victim_login, hp_str in attacks:
                damage_info = parse_damage_detailed(hp_str)
                if damage_info and damage_info['total_damage'] > 0:
                    victim = victim_login if victim_login else "координаты"
                    turn_attacks.append({
                        'sf': int(sf),
                        'attacker': attacker_login,
                        'victim': victim,
                        'damage_info': damage_info,
                        'hp_str': hp_str
                    })
        
        # Выводим атаки в этом ходу, если они есть
        if turn_attacks:
            print(f"\nХОД {turn_num}")
            for attack in sorted(turn_attacks, key=lambda x: x['sf']):
                info = attack['damage_info']
                
                # Формируем строку с уроном
                if attack['victim'] == 'координаты':
                    target_str = f"{attack['attacker']} → координаты"
                else:
                    target_str = f"{attack['attacker']} → {attack['victim']}"
                
                print(f"Кадр {attack['sf']}: {target_str}")
                print(f"Бронебой: {info['armor_piercing']}")
                print(f"Урон: {info['normal_damage']}")
                
                if info['status_code'] and info['status_damage'] > 0:
                    status_name = get_status_name(info['status_code'])
                    print(f"Спец.Урон: {info['status_damage']} {status_name}")
                else:
                    print("Спец.Урон: 0")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python3 analyze_damage_detailed.py <файл.tzb>")
        sys.exit(1)
    
    filename = sys.argv[1]
    analyze_damage_detailed(filename)
