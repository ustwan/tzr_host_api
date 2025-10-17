import asyncio
from typing import Optional, List, Tuple, Dict, Any

from ..infrastructure.repositories.pg_battle_repository import PgBattleRepository


class FakeBattleDatabase:
    def __init__(self):
        self._battles: Dict[int, Dict[str, Any]] = {
            1: {"id": 1, "players": ["alice"], "battle_type": "A", "ts": None},
            2: {"id": 2, "players": ["bob"], "battle_type": "B", "ts": None},
        }

    async def get_battle(self, battle_id: int) -> Optional[Dict[str, Any]]:
        return self._battles.get(battle_id)

    async def list_battles(self, page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
        items = list(self._battles.values())
        total = len(items)
        start = (page - 1) * limit
        return items[start:start + limit], total

    async def search_battles(self, **filters) -> Tuple[List[Dict[str, Any]], int]:
        player = filters.get("player")
        items = [b for b in self._battles.values() if not player or player in " ".join(b.get("players", []))]
        return items, len(items)

    async def save_battle(self, battle_data: Dict[str, Any]) -> int:
        self._battles[battle_data["id"]] = battle_data
        return battle_data["id"]


def test_pg_repository_contract_like_behavior():
    repo = PgBattleRepository(FakeBattleDatabase())
    # get
    item = asyncio.get_event_loop().run_until_complete(repo.get_battle(1))
    assert item and item["id"] == 1
    # list
    items, total = asyncio.get_event_loop().run_until_complete(repo.list_battles(page=1, limit=1))
    assert total == 2 and len(items) == 1
    # search
    items, total = asyncio.get_event_loop().run_until_complete(repo.search_battles(player="ali", page=1, limit=10))
    assert total == 1 and items[0]["id"] == 1


