#!/usr/bin/env python3
"""
Генератор тестовых .tzb (XML) файлов для тестирования файлового контура
"""
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# Базовая директория для логов
BASE_DIR = Path(__file__).parent / "export" / "btl"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# Шаблон XML лога боя
BATTLE_XML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<battle>
  <index>{index}</index>
  <arenaUniqueID>{arena_id}</arenaUniqueID>
  <arenaCreateTime>{timestamp}</arenaCreateTime>
  <duration>{duration}</duration>
  <gameplayID>{gameplay_id}</gameplayID>
  <mapName>{map_name}</mapName>
  <playerVehicles>
    {players}
  </playerVehicles>
  <common>
    <arenaTypeName>{map_name}</arenaTypeName>
    <bonusType>{bonus_type}</bonusType>
    <finishReason>{finish_reason}</finishReason>
    <winnerTeam>{winner_team}</winnerTeam>
    <duration>{duration}</duration>
  </common>
  <personal>
    <accountDBID>{player_id}</accountDBID>
    <team>{team}</team>
    <damageDealt>{damage}</damageDealt>
    <kills>{kills}</kills>
    <xp>{xp}</xp>
    <credits>{credits}</credits>
  </personal>
</battle>
"""

PLAYER_TEMPLATE = """    <vehicle>
      <accountDBID>{player_id}</accountDBID>
      <name>{player_name}</name>
      <team>{team}</team>
      <vehicleType>{vehicle}</vehicleType>
      <damageDealt>{damage}</damageDealt>
      <kills>{kills}</kills>
    </vehicle>
"""

# Список танков
VEHICLES = [
    "T-34", "IS-7", "Leopard 1", "M1 Abrams", "Panther", 
    "Tiger II", "T-54", "Centurion", "M48 Patton", "AMX 50B"
]

# Список карт
MAPS = [
    "Himmelsdorf", "Prokhorovka", "Steppes", "Malinovka", "Redshire",
    "El Halluf", "Mines", "Cliff", "Lakeville", "Live Oaks"
]

def generate_player(player_id, team):
    """Генерирует данные одного игрока"""
    return {
        'player_id': player_id,
        'player_name': f"Player_{player_id}",
        'team': team,
        'vehicle': random.choice(VEHICLES),
        'damage': random.randint(0, 5000),
        'kills': random.randint(0, 7)
    }

def generate_battle_log(index):
    """Генерирует один лог боя"""
    # Параметры боя
    timestamp = datetime.now() - timedelta(hours=random.randint(0, 720))
    duration = random.randint(300, 900)
    map_name = random.choice(MAPS)
    
    # Генерация игроков (14 игроков, 7 на команду)
    players_data = []
    for i in range(14):
        team = 1 if i < 7 else 2
        player = generate_player(random.randint(100000, 999999), team)
        players_data.append(PLAYER_TEMPLATE.format(**player))
    
    # Данные личного игрока (первый в списке)
    main_player = generate_player(random.randint(100000, 999999), 1)
    
    # Заполнение шаблона
    battle_data = {
        'index': index,
        'arena_id': random.randint(10000000, 99999999),
        'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'duration': duration,
        'gameplay_id': random.randint(1, 100),
        'map_name': map_name,
        'players': "\n".join(players_data),
        'bonus_type': random.randint(1, 5),
        'finish_reason': random.randint(0, 3),
        'winner_team': random.randint(1, 2),
        'player_id': main_player['player_id'],
        'team': main_player['team'],
        'damage': main_player['damage'],
        'kills': main_player['kills'],
        'xp': random.randint(200, 2000),
        'credits': random.randint(10000, 100000)
    }
    
    return BATTLE_XML_TEMPLATE.format(**battle_data)

def main():
    """Генерирует тестовые логи"""
    # Количество логов для генерации
    num_logs = 100
    
    print(f"Генерация {num_logs} тестовых .tzb файлов...")
    
    for i in range(num_logs):
        index = random.randint(1000000, 9999999)
        log_content = generate_battle_log(index)
        
        # Имя файла
        filename = f"{index}.tzb"
        filepath = BASE_DIR / filename
        
        # Запись файла
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        if (i + 1) % 10 == 0:
            print(f"  Создано {i + 1}/{num_logs} файлов...")
    
    print(f"\n✅ Готово! Создано {num_logs} файлов в {BASE_DIR}")
    print(f"\nПримеры файлов:")
    for file in sorted(BASE_DIR.glob("*.tzb"))[:5]:
        size = file.stat().st_size
        print(f"  {file.name} ({size} bytes)")

if __name__ == "__main__":
    main()










