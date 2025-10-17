"""
Утилиты для API_4
Вспомогательные функции для работы с данными
"""

import base64
import zlib
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import re


def compress_map(map_data: str) -> str:
    """
    Сжатие карты боя для экономии места в БД
    
    Args:
        map_data: Строка с данными карты
        
    Returns:
        Сжатая строка в base64
    """
    if not map_data:
        return ""
    
    # Сжимаем данные
    compressed = zlib.compress(map_data.encode('utf-8'))
    
    # Кодируем в base64
    return base64.b64encode(compressed).decode('ascii')


def decompress_map(compressed_data: str, height: int, width: int) -> List[str]:
    """
    Разворачивание сжатой карты
    
    Args:
        compressed_data: Сжатые данные в base64
        height: Высота карты
        width: Ширина карты
        
    Returns:
        Список строк карты
    """
    if not compressed_data:
        return []
    
    try:
        # Декодируем из base64
        compressed = base64.b64decode(compressed_data.encode('ascii'))
        
        # Разжимаем
        map_data = zlib.decompress(compressed).decode('utf-8')
        
        # Разбиваем на строки
        rows = map_data.split('\n')
        
        # Фильтруем пустые строки и обрезаем по ширине
        result = []
        for row in rows:
            if row.strip():
                # Обрезаем строку до нужной ширины
                trimmed_row = row[:width] if len(row) > width else row.ljust(width)
                result.append(trimmed_row)
        
        # Обрезаем до нужной высоты
        return result[:height]
        
    except Exception as e:
        print(f"Ошибка разворачивания карты: {e}")
        return []


def calculate_battle_duration(start_ts: datetime, end_ts: Optional[datetime] = None) -> int:
    """
    Вычисление длительности боя в секундах
    
    Args:
        start_ts: Время начала боя
        end_ts: Время окончания боя (если None, используется текущее время)
        
    Returns:
        Длительность в секундах
    """
    if end_ts is None:
        end_ts = datetime.now()
    
    duration = (end_ts - start_ts).total_seconds()
    return max(0, int(duration))


def calculate_survival_rate(participants: List[Dict]) -> float:
    """
    Вычисление коэффициента выживания
    
    Args:
        participants: Список участников боя
        
    Returns:
        Коэффициент выживания (0.0 - 1.0)
    """
    if not participants:
        return 0.0
    
    survived = sum(1 for p in participants if p.get('survived', False))
    return survived / len(participants)


def calculate_kills_per_turn(participants: List[Dict], turns: int) -> float:
    """
    Вычисление убийств за ход
    
    Args:
        participants: Список участников боя
        turns: Количество ходов
        
    Returns:
        Среднее количество убийств за ход
    """
    if turns <= 0:
        return 0.0
    
    total_kills = sum(
        p.get('kills_monsters', 0) + p.get('kills_players', 0) 
        for p in participants
    )
    
    return total_kills / turns


def generate_battle_summary(battle_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Генерация сводки по бою
    
    Args:
        battle_data: Данные боя
        
    Returns:
        Сводка по бою
    """
    meta = battle_data.get('meta', {})
    participants = meta.get('participants', [])
    monsters = meta.get('monsters', {})
    loot = meta.get('loot', {})
    
    # Основная статистика
    total_participants = len(participants)
    survived_count = sum(1 for p in participants if p.get('survived', False))
    total_kills_monsters = sum(p.get('kills_monsters', 0) for p in participants)
    total_kills_players = sum(p.get('kills_players', 0) for p in participants)
    total_monsters = sum(m.get('count', 0) for m in monsters.values())
    
    # Ресурсы
    total_resources = sum(loot.get('resources_total', {}).values())
    total_monster_parts = sum(loot.get('monster_parts_total', {}).values())
    total_other_items = sum(loot.get('other_items', {}).values())
    
    return {
        'participants': {
            'total': total_participants,
            'survived': survived_count,
            'survival_rate': calculate_survival_rate(participants)
        },
        'kills': {
            'monsters': total_kills_monsters,
            'players': total_kills_players,
            'total': total_kills_monsters + total_kills_players
        },
        'monsters': {
            'total': total_monsters,
            'types': len(monsters)
        },
        'loot': {
            'resources': total_resources,
            'monster_parts': total_monster_parts,
            'other_items': total_other_items,
            'total_items': total_resources + total_monster_parts + total_other_items
        },
        'battle_info': {
            'turns': meta.get('battle_info', {}).get('turns', 0),
            'battle_type': meta.get('battle_info', {}).get('battle_type', 'B'),
            'location': meta.get('battle_info', {}).get('location', [0, 0])
        }
    }


def validate_battle_data(battle_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Валидация данных боя
    
    Args:
        battle_data: Данные боя
        
    Returns:
        Кортеж (валидность, список ошибок)
    """
    errors = []
    
    # Проверяем обязательные поля
    required_fields = ['id', 'ts', 'players', 'meta']
    for field in required_fields:
        if field not in battle_data:
            errors.append(f"Отсутствует обязательное поле: {field}")
    
    # Проверяем метаданные
    meta = battle_data.get('meta', {})
    if not isinstance(meta, dict):
        errors.append("Поле 'meta' должно быть словарем")
    else:
        # Проверяем участников
        participants = meta.get('participants', [])
        if not isinstance(participants, list):
            errors.append("Поле 'participants' должно быть списком")
        else:
            for i, participant in enumerate(participants):
                if not isinstance(participant, dict):
                    errors.append(f"Участник {i} должен быть словарем")
                elif 'login' not in participant:
                    errors.append(f"У участника {i} отсутствует поле 'login'")
        
        # Проверяем монстров
        monsters = meta.get('monsters', {})
        if not isinstance(monsters, dict):
            errors.append("Поле 'monsters' должно быть словарем")
        
        # Проверяем лут
        loot = meta.get('loot', {})
        if not isinstance(loot, dict):
            errors.append("Поле 'loot' должно быть словарем")
    
    # Проверяем игроков
    players = battle_data.get('players', [])
    if not isinstance(players, list):
        errors.append("Поле 'players' должно быть списком")
    
    return len(errors) == 0, errors


def sanitize_filename(filename: str) -> str:
    """
    Очистка имени файла от недопустимых символов
    
    Args:
        filename: Исходное имя файла
        
    Returns:
        Очищенное имя файла
    """
    # Удаляем недопустимые символы
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Удаляем множественные подчеркивания
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Удаляем подчеркивания в начале и конце
    sanitized = sanitized.strip('_')
    
    return sanitized


def calculate_file_hash(file_path: str) -> str:
    """
    Вычисление SHA256 хеша файла
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        SHA256 хеш в шестнадцатеричном формате
    """
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception:
        return ""


def format_duration(seconds: int) -> str:
    """
    Форматирование длительности в читаемый вид
    
    Args:
        seconds: Длительность в секундах
        
    Returns:
        Отформатированная строка
    """
    if seconds < 60:
        return f"{seconds}с"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}м {secs}с"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}ч {minutes}м {secs}с"


def calculate_z_score(value: float, mean: float, std_dev: float) -> float:
    """
    Вычисление Z-score для обнаружения аномалий
    
    Args:
        value: Значение
        mean: Среднее значение
        std_dev: Стандартное отклонение
        
    Returns:
        Z-score
    """
    if std_dev == 0:
        return 0.0
    return (value - mean) / std_dev


def is_anomaly(z_score: float, threshold: float = 2.0) -> bool:
    """
    Проверка, является ли значение аномалией
    
    Args:
        z_score: Z-score
        threshold: Пороговое значение (по умолчанию 2.0)
        
    Returns:
        True, если значение является аномалией
    """
    return abs(z_score) > threshold


def generate_activity_score(participants: List[Dict], turns: int) -> float:
    """
    Генерация оценки активности боя
    
    Args:
        participants: Список участников
        turns: Количество ходов
        
    Returns:
        Оценка активности (0.0 - 1.0)
    """
    if not participants or turns <= 0:
        return 0.0
    
    # Базовые метрики
    total_kills = sum(
        p.get('kills_monsters', 0) + p.get('kills_players', 0) 
        for p in participants
    )
    
    survival_rate = calculate_survival_rate(participants)
    kills_per_turn = calculate_kills_per_turn(participants, turns)
    
    # Нормализуем метрики
    normalized_kills = min(total_kills / (len(participants) * turns), 1.0)
    normalized_survival = survival_rate
    normalized_kpt = min(kills_per_turn / 2.0, 1.0)  # Предполагаем максимум 2 убийства за ход
    
    # Взвешенная сумма
    activity_score = (
        normalized_kills * 0.4 +
        normalized_survival * 0.3 +
        normalized_kpt * 0.3
    )
    
    return min(1.0, max(0.0, activity_score))


def extract_battle_keywords(battle_data: Dict[str, Any]) -> List[str]:
    """
    Извлечение ключевых слов из данных боя для поиска
    
    Args:
        battle_data: Данные боя
        
    Returns:
        Список ключевых слов
    """
    keywords = set()
    
    # Игроки
    players = battle_data.get('players', [])
    for player in players:
        if isinstance(player, str):
            keywords.add(player.lower())
    
    # Кланы
    meta = battle_data.get('meta', {})
    participants = meta.get('participants', [])
    for participant in participants:
        if isinstance(participant, dict):
            clan = participant.get('clan')
            if clan:
                keywords.add(clan.lower())
    
    # Монстры
    monsters = meta.get('monsters', {})
    for monster_name in monsters.keys():
        keywords.add(monster_name.lower())
    
    # Ресурсы
    loot = meta.get('loot', {})
    resources = loot.get('resources_total', {})
    for resource_name in resources.keys():
        keywords.add(resource_name.lower())
    
    return list(keywords)


def create_battle_thumbnail(map_data: List[str], max_width: int = 50, max_height: int = 20) -> str:
    """
    Создание миниатюры карты боя
    
    Args:
        map_data: Данные карты
        max_width: Максимальная ширина миниатюры
        max_height: Максимальная высота миниатюры
        
    Returns:
        Миниатюра карты
    """
    if not map_data:
        return ""
    
    # Обрезаем до максимальных размеров
    thumbnail_rows = map_data[:max_height]
    thumbnail = []
    
    for row in thumbnail_rows:
        if len(row) > max_width:
            thumbnail.append(row[:max_width])
        else:
            thumbnail.append(row)
    
    return '\n'.join(thumbnail)
