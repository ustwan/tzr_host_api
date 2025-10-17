import json
import sys
import importlib.util
from pathlib import Path
from typing import Any, Dict
from datetime import datetime, timezone


# Кэш импортов (загружаем один раз при старте модуля)
_CACHED_PARSERS = None

def _import_from_example() -> tuple:
    """Динамически импортирует battle_parser.py и dedupe_tzb.py из example/parser."""
    global _CACHED_PARSERS
    
    # Возвращаем из кэша если уже загружено
    if _CACHED_PARSERS is not None:
        return _CACHED_PARSERS
    
    # В контейнере example/parser находится в /app/example/parser
    base = Path("/app/example/parser")
    battle_parser_path = base / "battle_parser.py"
    dedupe_tzb_path = base / "dedupe_tzb.py"
    if not battle_parser_path.exists() or not dedupe_tzb_path.exists():
        raise FileNotFoundError(f"Не найдены файлы парсера в {base}")

    spec_bp = importlib.util.spec_from_file_location("example_parser_battle", str(battle_parser_path))
    example_parser_battle = importlib.util.module_from_spec(spec_bp)  # type: ignore
    assert spec_bp and spec_bp.loader
    spec_bp.loader.exec_module(example_parser_battle)  # type: ignore

    spec_dd = importlib.util.spec_from_file_location("example_parser_dedupe", str(dedupe_tzb_path))
    example_parser_dedupe = importlib.util.module_from_spec(spec_dd)  # type: ignore
    assert spec_dd and spec_dd.loader
    spec_dd.loader.exec_module(example_parser_dedupe)  # type: ignore

    # Сохраняем в кэш
    _CACHED_PARSERS = (example_parser_battle, example_parser_dedupe)
    return _CACHED_PARSERS


def run_new_parser(file_path: str) -> Dict[str, Any]:
    """Выполняет новый парсер из example/parser в том же процессе и возвращает JSON."""
    example_parser_battle, example_parser_dedupe = _import_from_example()

    p = Path(file_path)
    
    # Определяем compressed по сигнатуре файла
    with p.open('rb') as f:
        magic = f.read(2)
        is_gzipped = (magic == b'\x1f\x8b')
    
    # Безопасное чтение файла
    try:
        with p.open('r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Fallback на cp1251
        with p.open('r', encoding='cp1251', errors='replace') as f:
            content = f.read()
    
    # Дедупликация в памяти (не перезаписываем файл)
    deduped = example_parser_dedupe.dedupe_tzb_content(content)  # type: ignore[attr-defined]

    parser = example_parser_battle.BattleParser()  # type: ignore[attr-defined]
    result = parser.parse_file(str(p))  # type: ignore[call-arg]
    if not isinstance(result, dict):
        raise ValueError("Ожидался dict от нового парсера")
    
    # Добавляем метаданные о compressed из реального определения
    if 'battle' in result and isinstance(result['battle'], dict):
        result['battle']['compressed'] = is_gzipped
    
    return result


def normalize_for_db(parser_json: Dict[str, Any]) -> Dict[str, Any]:
    """Преобразует JSON нового парсера к схеме, ожидаемой слоем БД API4."""
    battle = parser_json.get("battle", {})
    participants = parser_json.get("participants", [])
    monsters = parser_json.get("monsters", [])
    loot_total = parser_json.get("loot_total", {})

    # Основные поля боя
    # Конвертируем start_ts_unix -> datetime (TIMESTAMPTZ ожидание)
    start_ts_unix = battle.get("start_ts_unix")
    start_ts_dt = None
    if isinstance(start_ts_unix, (int, float)):
        try:
            start_ts_dt = datetime.fromtimestamp(int(start_ts_unix), tz=timezone.utc)
        except Exception:
            start_ts_dt = None

    # Сформируем список игроков (логины) из participants
    player_logins = [p.get("login") for p in (participants or []) if isinstance(p, dict) and p.get("login")]

    # Преобразуем battle.ts (ISO8601) в datetime (UTC) если это строка
    ts_value = battle.get("ts")
    if isinstance(ts_value, str):
        try:
            ts_value = datetime.fromisoformat(ts_value.replace('Z', '+00:00'))
        except Exception:
            ts_value = None

    out: Dict[str, Any] = {
        "id": int(battle.get("id")) if battle.get("id") is not None else None,
        "source_id": int(battle.get("id")) if battle.get("id") is not None else None,
        "ts": ts_value,
        "size_bytes": int(battle.get("size_bytes")) if battle.get("size_bytes") is not None else None,
        "sha256": str(battle.get("sha256")) if battle.get("sha256") else None,
        "storage_key": str(battle.get("storage_key")) if battle.get("storage_key") else None,
        "compressed": bool(battle.get("compressed")) if battle.get("compressed") is not None else False,
        "turns": int(battle.get("turns")) if battle.get("turns") is not None else None,
        "battle_type": str(battle.get("battle_type")) if battle.get("battle_type") else None,
        "loc_x": int((battle.get("loc") or {}).get("x")) if (battle.get("loc") or {}).get("x") is not None else None,
        "loc_y": int((battle.get("loc") or {}).get("y")) if (battle.get("loc") or {}).get("y") is not None else None,
        "start_ts": start_ts_dt,
        "players_cnt": int(battle.get("players_cnt")) if battle.get("players_cnt") is not None else None,
        "monsters_cnt": int(battle.get("monsters_cnt")) if battle.get("monsters_cnt") is not None else None,
        "entities_cnt": int(battle.get("entities_cnt")) if battle.get("entities_cnt") is not None else None,
        # Полные данные для хранения (map_patch в т.ч.)
        "data": {
            "battle": battle,
            "participants": participants,
            "monsters": monsters,
            "loot_total": loot_total,
        },
        # Обработанные participants и monsters (для loader.py)
        "participants": _meta_participants(participants),
        "monsters": _meta_monsters(monsters),
        # meta для существующих методов сохранения
        "meta": {
            "participants": _meta_participants(participants),
            "monsters": _meta_monsters(monsters),
            "loot": _meta_loot(loot_total),
        },
        # Для валидации и поиска
        "players": player_logins,
    }
    return out


def _meta_participants(participants: Any) -> Any:
    # Преобразуем типы данных для совместимости с БД
    result = []
    for p in participants or []:
        participant = dict(p)  # Копируем участника
        # Приводим login/clan к строке
        if 'login' in participant and participant['login'] is not None:
            participant['login'] = str(participant['login'])
        if 'clan' in participant and participant['clan'] is not None:
            participant['clan'] = str(participant['clan'])
        # Преобразуем profession: сохраняем И id И name
        profession_map = {
            0: 'без профессии',
            1: 'корсар',
            2: 'сталкер',
            3: 'старатель',
            4: 'инженер',
            5: 'наемник',
            6: 'торговец',
            7: 'патрульный',
            8: 'штурмовик',
            9: 'специалист',
            10: 'журналист',
            11: 'чиновник',
            12: 'псионик',
            13: 'каторжник',
            14: 'пси-кинетик',
            15: 'пси-медик',
            16: 'пси-лидер',
            17: 'полиморф',
        }
        
        if 'profession' in participant:
            prof_val = participant['profession']
            # ВСЕГДА преобразуем для БД: int → str
            if prof_val is None:
                participant['profession'] = None
            elif isinstance(prof_val, int):
                # Преобразуем int → string ДЛЯ БД
                participant['profession'] = profession_map.get(prof_val, 'unknown')
            # Если уже строка - оставляем как есть
        # Преобразуем side из числа в строку
        if 'side' in participant and isinstance(participant['side'], int):
            side_map = {0: 'neutral', 1: 'good', 2: 'evil'}
            participant['side'] = side_map.get(participant['side'], 'neutral')
        # Преобразуем gender из числа в строку
        if 'gender' in participant and isinstance(participant['gender'], int):
            gender_map = {0: 'unknown', 1: 'male', 2: 'female'}
            participant['gender'] = gender_map.get(participant['gender'], 'unknown')
        # Преобразуем survived из числа в boolean
        if 'survived' in participant and isinstance(participant['survived'], int):
            participant['survived'] = bool(participant['survived'])
        result.append(participant)
    return result


def _meta_monsters(monsters: Any) -> Any:
    # Слой БД ожидает dict с ключами kind|spec —
    # преобразуем список в dict
    result: Dict[str, Dict[str, Any]] = {}
    for m in monsters or []:
        key = m.get("kind") if m.get("spec") in (None, "") else f"{m.get('kind')}|{m.get('spec')}"
        result[key] = {
            "kind": m.get("kind"),
            "spec": m.get("spec"),
            "side": m.get("side", 0),
            "count": m.get("count", 0),
            "min_level": m.get("min_level", 0),
            "max_level": m.get("max_level", 0),
        }
    return result


def _meta_loot(loot_total: Any) -> Any:
    # Переводим агрегаты в формат, который понимает слой БД (_save_battle_loot)
    return {
        "resources_total": {i.get("name"): i.get("qty", 0) for i in loot_total.get("resources", [])},
        "monster_parts_total": {i.get("name"): i.get("qty", 0) for i in loot_total.get("monster_parts", [])},
        "other_items": {i.get("item_name"): i.get("qty", 0) for i in loot_total.get("other", [])},
    }


