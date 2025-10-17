import asyncio
from typing import Optional, List, Tuple, Dict, Any

from ..usecases.get_battle import GetBattleUseCase
from ..usecases.list_battles import ListBattlesUseCase
from ..usecases.search_battles import SearchBattlesUseCase
from ..ports.battle_repository import BattleRepository


class InMemoryBattleRepository(BattleRepository):
    def __init__(self, battles: Dict[int, Dict[str, Any]]):
        self._battles = battles

    async def get_battle(self, battle_id: int) -> Optional[Dict[str, Any]]:
        return self._battles.get(battle_id)

    async def list_battles(self, page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
        items = list(self._battles.values())
        total = len(items)
        start = (page - 1) * limit
        return items[start:start + limit], total

    async def search_battles(self, **filters) -> Tuple[List[Dict[str, Any]], int]:
        # very naive filter by player substring
        player = filters.get("player")
        data = [b for b in self._battles.values() if not player or player in (" ".join(b.get("players", [])))]
        return data, len(data)

    async def save_battle(self, battle_data: Dict[str, Any]) -> int:
        self._battles[battle_data["id"]] = battle_data
        return battle_data["id"]


def test_get_battle_returns_item():
    repo = InMemoryBattleRepository({1: {"id": 1, "players": ["alice"]}})
    uc = GetBattleUseCase(repo)
    result = asyncio.get_event_loop().run_until_complete(uc.execute(1))
    assert result is not None and result["id"] == 1


def test_list_battles_pagination():
    repo = InMemoryBattleRepository({i: {"id": i} for i in range(1, 21)})
    uc = ListBattlesUseCase(repo)
    page1, total = asyncio.get_event_loop().run_until_complete(uc.execute(page=1, limit=5))
    assert total == 20 and len(page1) == 5 and page1[0]["id"] == 1


def test_search_battles_by_player():
    repo = InMemoryBattleRepository({
        1: {"id": 1, "players": ["alice"]},
        2: {"id": 2, "players": ["bob"]},
    })
    uc = SearchBattlesUseCase(repo)
    result, total = asyncio.get_event_loop().run_until_complete(uc.execute(player="ali", page=1, limit=10))
    assert total == 1 and result[0]["id"] == 1

