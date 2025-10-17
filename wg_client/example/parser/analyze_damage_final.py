#!/usr/bin/env python3
"""
ФИНАЛЬНЫЙ анализ урона по ходам в файле .tzb
"""

import re
import sys

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

def analyze_damage_final(filename):
    """Финальный анализ урона по ходам"""
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Дедупликация
    second_battle_pos = content.find('<BATTLE', content.find('<BATTLE') + 1)
    if second_battle_pos != -1:
        content = content[:second_battle_pos]
    
    # Найдем все ходы
    turn_pattern = r'<TURN turn="(\d+)"[^>]*>(.*?)</TURN>'
    turns = re.findall(turn_pattern, content, re.DOTALL)
    
    print(f"Детальный анализ урона для файла: {filename}")
    print("=" * 80)
    
    for turn_num, turn_content in turns:
        turn_attacks = []
        
        # Найдем все USER блоки (только с содержимым, не самозакрывающиеся)
        user_pattern = r'<USER login="([^"]+)"[^>]*>(.*?)</USER>'
        users = re.findall(user_pattern, turn_content, re.DOTALL)
        users = [(login, content) for login, content in users if content.strip()]
        
        # Обработаем атаки в каждом USER блоке
        for attacker_login, user_content in users:
            # Найдем все атаки t="5" с HP
            attack_pattern = r'<a sf="(\d+)" t="5"[^>]*HP="([^"]+)"[^>]*>'
            attacks = re.findall(attack_pattern, user_content)
            
            for sf, hp_str in attacks:
                # Найдем полную строку атаки для извлечения login жертвы
                full_attack_pattern = rf'<a sf="{sf}" t="5"[^>]*HP="{re.escape(hp_str)}"[^>]*>'
                full_match = re.search(full_attack_pattern, user_content)
                if full_match:
                    full_attack = full_match.group(0)
                    login_match = re.search(r'login="([^"]+)"', full_attack)
                    victim_login = login_match.group(1) if login_match else None
                    
                    damage_info = parse_damage_detailed(hp_str)
                    if damage_info and damage_info['total_damage'] > 0:
                        victim = victim_login if victim_login else "координаты"
                        turn_attacks.append({
                            'sf': int(sf),
                            'attacker': attacker_login,
                            'victim': victim,
                            'damage_info': damage_info
                        })
        
        # Выводим атаки в этом ходу
        if turn_attacks:
            print(f"\nХОД {turn_num}")
            for attack in sorted(turn_attacks, key=lambda x: x['sf']):
                info = attack['damage_info']
                
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
        print("Использование: python3 analyze_damage_final.py <файл.tzb>")
        sys.exit(1)
    
    filename = sys.argv[1]
    analyze_damage_final(filename)
