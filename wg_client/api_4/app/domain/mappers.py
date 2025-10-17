from typing import Dict, Any, List
from domain.entities import Battle


def map_db_battle_to_domain(row: Dict[str, Any]) -> Battle:
    return Battle(
        id=row.get("id"),
        players=list(row.get("players") or []),
        battle_type=row.get("battle_type"),
    )


def map_domain_battles_to_summary(battles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for battle in battles:
        # Используем source_id если он есть, иначе service_id
        source_id = battle.get("source_id")
        battle_id = source_id if source_id is not None else battle.get("id")
        
        items.append({
            "battle_id": battle_id,  # Реальный battle_id из игрового лога (или service_id для старых)
            "service_id": battle.get("id"),  # Внутренний ID БД
            "ts": battle.get("ts"),
            "players": battle.get("players"),
            "battle_type": battle.get("battle_type"),
            "duration": battle.get("duration"),
            "monsters_count": battle.get("monsters_count"),
            "location": battle.get("location"),
        })
    return items


