from typing import Optional, List, Tuple, Dict, Any


class BattleRepository:
    """Абстракция доступа к боям.

    Реализации должны предоставлять доступ к данным боёв (чтение/запись)
    независимо от конкретной технологии хранилища.
    """

    async def get_battle(self, battle_id: int) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def list_battles(self, page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
        raise NotImplementedError

    async def search_battles(self, **filters) -> Tuple[List[Dict[str, Any]], int]:
        raise NotImplementedError

    async def save_battle(self, battle_data: Dict[str, Any]) -> int:
        raise NotImplementedError



