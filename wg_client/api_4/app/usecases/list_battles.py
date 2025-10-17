from typing import List, Tuple, Dict, Any

from ports.battle_repository import BattleRepository


class ListBattlesUseCase:
    """Use case: получить страницу боёв с пагинацией."""

    def __init__(self, repository: BattleRepository):
        self._repository = repository

    async def execute(self, page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
        return await self._repository.list_battles(page=page, limit=limit)


