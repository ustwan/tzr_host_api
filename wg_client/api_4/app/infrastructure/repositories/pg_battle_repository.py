from typing import Optional, List, Tuple, Dict, Any

from ports.battle_repository import BattleRepository
from database import BattleDatabase


class PgBattleRepository(BattleRepository):
    """Репозиторий боёв на PostgreSQL поверх текущего BattleDatabase."""

    def __init__(self, db: BattleDatabase):
        self._db = db

    async def get_battle(self, battle_id: int) -> Optional[Dict[str, Any]]:
        return await self._db.get_battle(battle_id)

    async def list_battles(self, page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
        return await self._db.list_battles(page, limit)

    async def search_battles(self, **filters) -> Tuple[List[Dict[str, Any]], int]:
        return await self._db.search_battles(
            player=filters.get("player"),
            clan=filters.get("clan"),
            battle_type=filters.get("battle_type"),
            from_date=filters.get("from_date"),
            to_date=filters.get("to_date"),
            monsters=filters.get("monsters"),
            page=filters.get("page", 1),
            limit=filters.get("limit", 10),
        )

    async def save_battle(self, battle_data: Dict[str, Any]) -> int:
        return await self._db.save_battle(battle_data)


