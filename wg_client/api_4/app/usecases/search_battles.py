from typing import Optional, List, Tuple, Dict, Any

from ports.battle_repository import BattleRepository


class SearchBattlesUseCase:
    """Use case: поиск по боям по набору фильтров."""

    def __init__(self, repository: BattleRepository):
        self._repository = repository

    async def execute(
        self,
        *,
        player: Optional[str] = None,
        clan: Optional[str] = None,
        battle_type: Optional[str] = None,
        from_date: Optional[Any] = None,
        to_date: Optional[Any] = None,
        monsters: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[Dict[str, Any]], int]:
        return await self._repository.search_battles(
            player=player,
            clan=clan,
            battle_type=battle_type,
            from_date=from_date,
            to_date=to_date,
            monsters=monsters,
            page=page,
            limit=limit,
        )


