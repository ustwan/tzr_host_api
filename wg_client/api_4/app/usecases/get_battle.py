from typing import Optional, Dict, Any

from ports.battle_repository import BattleRepository


class GetBattleUseCase:
    """Use case: получить бой по идентификатору."""

    def __init__(self, repository: BattleRepository):
        self._repository = repository

    async def execute(self, battle_id: int) -> Optional[Dict[str, Any]]:
        return await self._repository.get_battle(battle_id)


