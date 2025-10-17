from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Depends
import os

from app.database import BattleDatabase
from app.parser import BattleParser
from app.loader import BattleLoader
from app.analytics import BattleAnalytics
from app.infrastructure.repositories.pg_battle_repository import PgBattleRepository
from app.usecases.get_battle import GetBattleUseCase
from app.usecases.list_battles import ListBattlesUseCase
from app.usecases.search_battles import SearchBattlesUseCase
from app.usecases.sync_logs import SyncLogsUseCase
from app.usecases.analytics import (
    PlayerAnalyticsUseCase, ClanAnalyticsUseCase, ResourceAnalyticsUseCase, MonsterAnalyticsUseCase, GeneralStatsUseCase
)
from app.usecases.admin_logs import AdminLogsUseCase


def require_admin_token_factory(env_getter):
    def dependency():
        token = env_getter("ADMIN_API_TOKEN")
        if not token:
            raise HTTPException(status_code=503, detail="ADMIN_API_TOKEN не сконфигурирован")
        return token
    return dependency


@asynccontextmanager
async def build_app(app: FastAPI) -> AsyncIterator[FastAPI]:

    # core infrastructure
    db = BattleDatabase()
    await db.connect()
    parser = BattleParser()
    loader = BattleLoader(db)
    analytics = BattleAnalytics(db)

    # ports/adapters and use cases
    repo = PgBattleRepository(db)
    get_battle_uc = GetBattleUseCase(repo)
    list_battles_uc = ListBattlesUseCase(repo)
    search_battles_uc = SearchBattlesUseCase(repo)
    sync_logs_uc = SyncLogsUseCase(loader)
    player_analytics_uc = PlayerAnalyticsUseCase(analytics)
    clan_analytics_uc = ClanAnalyticsUseCase(analytics)
    resource_analytics_uc = ResourceAnalyticsUseCase(analytics)
    monster_analytics_uc = MonsterAnalyticsUseCase(analytics)
    general_stats_uc = GeneralStatsUseCase(analytics)
    admin_logs_uc = AdminLogsUseCase(loader)

    # dependencies
    require_admin_token = require_admin_token_factory(os.getenv)

    from app.interfaces.http.routes import build_router
    app.include_router(build_router(
        get_battle_uc=get_battle_uc,
        list_battles_uc=list_battles_uc,
        search_battles_uc=search_battles_uc,
        sync_logs_uc=sync_logs_uc,
        player_analytics_uc=player_analytics_uc,
        clan_analytics_uc=clan_analytics_uc,
        resource_analytics_uc=resource_analytics_uc,
        monster_analytics_uc=monster_analytics_uc,
        general_stats_uc=general_stats_uc,
        admin_logs_uc=admin_logs_uc,
        require_admin_token=require_admin_token,
    ))

    try:
        yield app
    finally:
        await db.disconnect()


