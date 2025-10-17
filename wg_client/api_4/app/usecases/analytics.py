from typing import Optional, List, Dict, Any

from app.analytics import BattleAnalytics
from app.models import (
    PlayerStats, ClanStats, ResourceStats, MonsterStats,
    ResourceAnomaly
)


class PlayerAnalyticsUseCase:
    def __init__(self, analytics: BattleAnalytics):
        self._a = analytics

    async def get_player(self, *, login: Optional[str], days: int) -> Optional[PlayerStats]:
        return await self._a.get_player_stats(login=login, days=days)

    async def get_top_players(self, *, metric: str, limit: int, days: int) -> List[PlayerStats]:
        return await self._a.get_top_players(metric=metric, limit=limit, days=days)

    async def get_survival(self, *, login: str, days: int) -> Dict[str, Any]:
        return await self._a.get_player_survival(login=login, days=days)

    async def get_efficiency(self, *, login: str, days: int, w_p: float) -> Dict[str, Any]:
        return await self._a.get_player_efficiency(login=login, days=days, w_p=w_p)

    async def get_efficiency_top(self, *, limit: int, days: int, w_p: float) -> List[Dict[str, Any]]:
        return await self._a.get_efficiency_top(limit=limit, days=days, w_p=w_p)


class ClanAnalyticsUseCase:
    def __init__(self, analytics: BattleAnalytics):
        self._a = analytics

    async def get_clan(self, *, name: Optional[str], days: int) -> Optional[ClanStats]:
        return await self._a.get_clan_stats(name=name, days=days)

    async def get_survival(self, *, name: str, days: int) -> Dict[str, Any]:
        return await self._a.get_clan_survival(name=name, days=days)


class ResourceAnalyticsUseCase:
    def __init__(self, analytics: BattleAnalytics):
        self._a = analytics

    async def get_resource(self, *, name: Optional[str], days: int) -> Optional[ResourceStats]:
        return await self._a.get_resource_stats(name=name, days=days)

    async def get_anomalies(self, *, days: int) -> List[ResourceAnomaly]:
        return await self._a.get_resource_anomalies(days=days)

    async def get_economy(self, *, days: int) -> Dict[str, Any]:
        return await self._a.get_resources_economy(days=days)


class MonsterAnalyticsUseCase:
    def __init__(self, analytics: BattleAnalytics):
        self._a = analytics

    async def get_monster(self, *, kind: Optional[str], days: int) -> Optional[MonsterStats]:
        return await self._a.get_monster_stats(kind=kind, days=days)


class GeneralStatsUseCase:
    def __init__(self, analytics: BattleAnalytics):
        self._a = analytics

    async def get_stats(self, *, days: int) -> Dict[str, Any]:
        return await self._a.get_general_stats(days=days)


