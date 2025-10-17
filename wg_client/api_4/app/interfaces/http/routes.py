from typing import Optional, Any, Dict, List
import os
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Path, Query, Depends, UploadFile, File

logger = logging.getLogger(__name__)

from app.usecases.get_battle import GetBattleUseCase
from app.usecases.list_battles import ListBattlesUseCase
from app.usecases.search_battles import SearchBattlesUseCase
from app.usecases.sync_logs import SyncLogsUseCase
from app.usecases.analytics import (
    PlayerAnalyticsUseCase, ClanAnalyticsUseCase, ResourceAnalyticsUseCase, MonsterAnalyticsUseCase, GeneralStatsUseCase
)
from app.usecases.admin_logs import AdminLogsUseCase
from app.domain.mappers import map_domain_battles_to_summary
from fastapi.responses import Response
from app.adapters.http_mother_client import HttpMotherClient
from app.database import BattleDatabase


def build_router(
    *,
    get_battle_uc: GetBattleUseCase,
    list_battles_uc: ListBattlesUseCase,
    search_battles_uc: SearchBattlesUseCase,
    sync_logs_uc: SyncLogsUseCase,
    player_analytics_uc: PlayerAnalyticsUseCase,
    clan_analytics_uc: ClanAnalyticsUseCase,
    resource_analytics_uc: ResourceAnalyticsUseCase,
    monster_analytics_uc: MonsterAnalyticsUseCase,
    general_stats_uc: GeneralStatsUseCase,
    admin_logs_uc: AdminLogsUseCase,
    require_admin_token,
) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @router.get("/battle/healthz")
    async def battle_healthz():
        return {"status": "ok"}

    @router.get(
        "/battles/list",
        summary="Список боёв",
        description="Получить список всех боёв с пагинацией. Возвращает реальные battle_id из игры (source_id).",
        tags=["Battles"]
    )
    async def list_battles(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
        battles, total = await list_battles_uc.execute(page=page, limit=limit)
        items = map_domain_battles_to_summary(battles)
        return {"battles": items, "total": total, "page": page, "limit": limit}

    # Алиас для совместимости с клиентами, ожидающими /battle/list
    @router.get("/battle/list")
    async def list_battles_alias(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
        return await list_battles(page=page, limit=limit)

    @router.get(
        "/battles/search",
        summary="Поиск боёв",
        description="""
Поиск боёв по различным критериям: игрок, клан, тип боя, период времени, монстры.

**Примеры:**
- `player=Термит` - все бои игрока
- `clan=WG` - все бои клана
- `from_date=2025-10-01&to_date=2025-10-08` - бои за период
- `monsters=rat` - бои с крысами
        """,
        tags=["Battles"]
    )
    async def search_battles(
        player: Optional[str] = Query(None, description="Имя игрока (частичное совпадение)"),
        clan: Optional[str] = Query(None, description="Название клана"),
        battle_type: Optional[str] = Query(None, description="Тип боя"),
        from_date: Optional[datetime] = Query(None, description="Начало периода"),
        to_date: Optional[datetime] = Query(None, description="Конец периода"),
        monsters: Optional[str] = Query(None, description="Тип монстра"),
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
    ):
        battles, total = await search_battles_uc.execute(
            player=player, clan=clan, battle_type=battle_type,
            from_date=from_date, to_date=to_date, monsters=monsters,
            page=page, limit=limit,
        )
        items = map_domain_battles_to_summary(battles)
        return {"battles": items, "total": total, "page": page, "limit": limit}

    # Алиас для совместимости: /battle/search
    @router.get(
        "/battle/search",
        summary="Поиск боёв по критериям",
        description="""
        Поиск боёв по различным критериям с пагинацией.
        
        **Фильтры поиска:**
        - `player` - логин игрока-участника
        - `clan` - название клана
        - `battle_type` - тип боя (pve/pvp/boss)
        - `from_date`, `to_date` - диапазон дат (ISO 8601)
        - `monsters` - логин монстра (например: "$Кровопийца")
        
        **Пагинация:**
        - `page` - номер страницы (начиная с 1)
        - `limit` - боёв на странице (1-100)
        
        **Возвращает:**
        - `battles` - массив боёв
        - `total` - всего найдено
        - `page`, `limit` - текущая страница
        - `has_more` - есть ли еще результаты
        
        **Примеры:**
        ```
        /battle/search?player=PlayerName&from_date=2025-10-01&limit=20
        /battle/search?clan=MyC lan&battle_type=pvp&page=2
        /battle/search?monsters=$Босс&days=7
        ```
        """,
        tags=["Battles"]
    )
    async def search_battles_alias(
        player: Optional[str] = Query(None, description="Логин игрока"),
        clan: Optional[str] = Query(None, description="Название клана"),
        battle_type: Optional[str] = Query(None, description="Тип боя: pve/pvp/boss"),
        from_date: Optional[datetime] = Query(None, description="Начальная дата (ISO 8601)"),
        to_date: Optional[datetime] = Query(None, description="Конечная дата (ISO 8601)"),
        monsters: Optional[str] = Query(None, description="Логин монстра (с $)"),
        page: int = Query(1, ge=1, description="Номер страницы"),
        limit: int = Query(10, ge=1, le=100, description="Боёв на странице"),
    ):
        return await search_battles(
            player=player, clan=clan, battle_type=battle_type,
            from_date=from_date, to_date=to_date, monsters=monsters,
            page=page, limit=limit,
        )

    @router.get(
        "/battle/{battle_id:int}",
        summary="Получить бой по ID",
        description="Возвращает полную информацию о бое по его battle_id (ID как на сервере игры).",
        tags=["Battles"]
    )
    async def get_battle(battle_id: int = Path(..., description="battle_id (ID как на сервере игры)")):
        battle = await get_battle_uc.execute(battle_id)
        if not battle:
            raise HTTPException(status_code=404, detail="Бой не найден")
        return battle

    @router.get(
        "/battle/by-source/{source_id:int}",
        summary="Получить бой по service_id",
        description="Возвращает полную информацию о бое по его source_id (ID из БД).",
        tags=["Battles"]
    )
    async def get_battle_by_source(source_id: int = Path(..., description="source_id (ID из БД)")):
        # source_id в URL - это на самом деле service_id (внутренний id из БД)
        # get_battle ищет по source_id, поэтому делаем прямой запрос по id
        db = BattleDatabase()
        row = await db._execute_one("SELECT source_id FROM battles WHERE id = $1", source_id)
        await db.disconnect()
        if not row:
            raise HTTPException(status_code=404, detail="Бой с таким source_id не найден")
        # Теперь ищем по реальному battle_id (source_id из БД)
        battle = await get_battle_uc.execute(int(row["source_id"]))
        if not battle:
            raise HTTPException(status_code=404, detail="Бой не найден")
        return battle

    @router.get(
        "/battle/{battle_id:int}/raw",
        summary="Получить сырой XML лог боя",
        description="Возвращает оригинальный XML файл боя (.tzb) для скачивания или анализа.",
        tags=["Battles"]
    )
    async def get_battle_raw(battle_id: int = Path(..., description="Service ID боя")):
        # 1) Получаем storage_key из БД (ищем по source_id, т.к. battle_id = source_id)
        db = BattleDatabase()
        # Сначала находим service_id по source_id
        row = await db._execute_one("SELECT id, storage_key FROM battles WHERE source_id = $1", battle_id)
        await db.disconnect()
        if not row or not row.get("storage_key"):
            raise HTTPException(status_code=404, detail="Исходный файл не найден")
        storage_key = row["storage_key"]

        # 2) Пытаемся получить файл через api_mother (предпочтительно)
        mother = HttpMotherClient()
        try:
            if await mother.health_check():
                # Передаём battle_id.tzb для правильного определения шарда в api_mother
                import os
                content = await mother.get_gz_file(f"{battle_id}.tzb")
                try:
                    import gzip
                    xml = gzip.decompress(content)
                except Exception:
                    xml = content
                return Response(content=xml, media_type="application/xml")
        except Exception as e:
            # Если api_mother не смог найти файл, переходим к локальному поиску
            import logging
            logging.getLogger(__name__).debug(f"api_mother failed for battle {battle_id}: {e}")
        finally:
            await mother.close()

        # 3) Фолбэк: читаем файл с локального пути
            import gzip, os
        candidates = []
        
        shard = battle_id // 50000
        gz_base = os.getenv('LOGS_STORE', '/srv/btl/gz')
        raw_base = os.getenv('LOGS_RAW', '/srv/btl/raw')
        
        # ПРИОРИТЕТ 1: /srv/btl/gz/{shard}/{battle_id}.tzb.gz (ОСНОВНОЕ ХРАНИЛИЩЕ!)
        candidates.append(os.path.join(gz_base, str(shard), f"{battle_id}.tzb.gz"))
        
        # ПРИОРИТЕТ 2: /srv/btl/raw/{shard}/{battle_id}.tzb (ВРЕМЕННОЕ, если ещё не сжато)
        candidates.append(os.path.join(raw_base, str(shard), f"{battle_id}.tzb"))
        
        # ПРИОРИТЕТ 3: storage_key из БД (если указан другой путь)
        storage_key_str = str(storage_key)
        if storage_key_str not in candidates:
            candidates.append(storage_key_str)
            if storage_key_str.endswith('.tzb'):
                candidates.append(storage_key_str.replace('.tzb', '.tzb.gz'))
        
        # ПРИОРИТЕТ 4: Проверяем gz-версию storage_key
        if storage_key_str.endswith('.tzb'):
            gz_version = storage_key_str.replace('/raw/', '/gz/') + '.gz'
            if gz_version not in candidates:
                candidates.append(gz_version)

        last_err = None

        for cand in candidates:
            try:
                if cand.endswith('.gz'):
                    with gzip.open(cand, 'rb') as f:
                    data = f.read()
            else:
                    with open(cand, 'rb') as f:
                    data = f.read()
            return Response(content=data, media_type="application/xml")
            except Exception as e:  # пробуем следующий кандидат
                last_err = e
                continue
        raise HTTPException(status_code=500, detail=f"Не удалось прочитать файл: {last_err}")

    @router.post(
        "/sync",
        summary="Синхронизация логов",
        description="Сканирует папку с логами и синхронизирует их в БД.",
        tags=["Sync"]
    )
    async def sync():
        result = await sync_logs_uc.sync(os.getenv("LOGS_BASE", "/srv/btl/raw"))
        return {"synced": result.get("successful", 0), "total": result.get("total_files", 0), "errors": result.get("errors", [])}

    @router.post(
        "/sync/reprocess",
        summary="Повторная обработка",
        description="Пересканирует и заново обрабатывает все логи.",
        tags=["Sync"]
    )
    async def reprocess():
        result = await sync_logs_uc.reprocess()
        return {"message": "Повторная обработка завершена", "processed": result.get("processed", 0), "successful": result.get("successful", 0), "failed": result.get("failed", 0)}

    @router.get(
        "/analytics/player/{login}",
        summary="Полная статистика игрока",
        description="""
        Возвращает полную статистику игрока за период.
        
        **Включает:**
        - Базовая статистика (бои, винрейт, K/D)
        - Распределение по профессиям
        - Активность по дням
        - Стиль игры (K-means кластеризация)
        - Достижения и рекорды
        - Эффективность в PvE/PvP
        
        **Возвращает:**
        - `login` - логин игрока
        - `battles_count` - всего боёв
        - `win_rate` - процент побед
        - `avg_kills`, `avg_deaths` - среднее убийств/смертей
        - `playstyle` - стиль игры (новичок/фармер/pvp-агрессор и т.д.)
        - `playstyle_confidence` - уверенность ML модели (0-1)
        - `professions_used` - использованные профессии
        - `activity_trend` - тренд активности (growing/stable/declining)
        
        **Пример:**
        ```
        /analytics/player/PlayerName?days=90
        ```
        """,
        tags=["Analytics - Player"]
    )
    async def get_player(
        login: str = Path(..., description="Логин игрока"),
        days: int = Query(30, ge=1, le=365, description="Период анализа")
    ):
        stats = await player_analytics_uc.get_player(login=login, days=days)
        if not stats:
            raise HTTPException(status_code=404, detail="Игрок не найден")
        
        # УЛУЧШЕНИЕ: Добавляем K-means playstyle
        player_id = await player_analytics_uc._a._get_player_id_by_login(login)
        if player_id:
            playstyle_data = await player_analytics_uc._a._get_playstyle(player_id, days=days)
            if playstyle_data:
                # Преобразуем Pydantic объект в dict если нужно
                if hasattr(stats, 'dict'):
                    stats_dict = stats.dict()
                elif hasattr(stats, '__dict__'):
                    stats_dict = stats.__dict__
                else:
                    stats_dict = dict(stats)
                
                # Добавляем playstyle
                stats_dict['playstyle'] = playstyle_data.get('display_name')
                stats_dict['playstyle_confidence'] = playstyle_data.get('confidence')
                stats_dict['playstyle_cluster_id'] = playstyle_data.get('cluster_id')
                
                # Добавляем bot detection
                bd = playstyle_data.get('bot_detection', {})
                if bd.get('is_likely_bot'):
                    stats_dict['bot_warning'] = {
                        'is_likely_bot': True,
                        'bot_score': bd.get('bot_score'),
                        'reasons': bd.get('reasons', [])
                    }
                
                return stats_dict
        
        return stats

    @router.get(
        "/analytics/players/top",
        summary="Топ игроков по метрике",
        description="""
        Возвращает топ игроков по выбранной метрике.
        
        **Доступные метрики:**
        - `battles_count` - Количество боёв
        - `win_rate` - Процент побед
        - `kills` - Количество убийств
        - `damage_dealt` - Нанесенный урон
        - `experience_gained` - Полученный опыт
        - `resources_mined` - Добыто ресурсов
        - `boss_kills` - Убийств боссов
        - `pvp_kills` - PvP убийств
        - `survival_rate` - Процент выживаемости
        - `efficiency_score` - Общая эффективность
        
        **Пример:**
        ```
        /analytics/players/top?metric=win_rate&limit=20&days=90
        ```
        """,
        tags=["Analytics - Players"]
    )
    async def get_top_players(
        metric: str = Query("battles_count", description="Метрика для сортировки"),
        limit: int = Query(10, ge=1, le=100, description="Количество игроков"),
        days: int = Query(30, ge=1, le=365, description="Период (дней)")
    ):
        return await player_analytics_uc.get_top_players(metric=metric, limit=limit, days=days)

    @router.get(
        "/analytics/clan/{name}",
        summary="Статистика клана",
        description="""
        Полная статистика клана за период.
        
        **Анализирует:**
        - Активность членов клана
        - Общий винрейт
        - Территориальный контроль
        - Межклановые войны
        
        **Возвращает:**
        - `clan_name` - название клана
        - `members_count` - количество активных членов
        - `total_battles` - боёв клана
        - `win_rate` - винрейт
        - `avg_member_activity` - средняя активность члена
        - `top_players` - топ игроков клана
        - `clan_wars` - войны с другими кланами
        
        **Пример:**
        ```
        /analytics/clan/MyClan?days=30
        ```
        """,
        tags=["Analytics - Clans"]
    )
    async def get_clan(
        name: str = Path(..., description="Название клана"),
        days: int = Query(30, ge=1, le=365, description="Период анализа")
    ):
        stats = await clan_analytics_uc.get_clan(name=name, days=days)
        if not stats:
            raise HTTPException(status_code=404, detail="Клан не найден")
        return stats

    @router.get(
        "/analytics/resource/{name}",
        summary="Статистика ресурса",
        description="""
        Статистика добычи и использования ресурса.
        
        **Анализирует:**
        - Объемы добычи
        - Топ добытчиков
        - Цены на рынке (если есть)
        - Популярность ресурса
        
        **Возвращает:**
        - `resource_name` - название ресурса
        - `total_mined` - всего добыто
        - `avg_price` - средняя цена
        - `top_miners` - топ добытчиков
        - `mining_trend` - тренд добычи (increasing/stable/decreasing)
        - `rarity` - редкость (common/uncommon/rare/epic/legendary)
        
        **Пример:**
        ```
        /analytics/resource/золото?days=30
        /analytics/resource/артефакт_феникса?days=90
        ```
        """,
        tags=["Analytics - Resources"]
    )
    async def get_resource(
        name: str = Path(..., description="Название ресурса"),
        days: int = Query(30, ge=1, le=365, description="Период анализа")
    ):
        stats = await resource_analytics_uc.get_resource(name=name, days=days)
        if not stats:
            raise HTTPException(status_code=404, detail="Ресурс не найден")
        return stats

    @router.get(
        "/analytics/monster/{kind}",
        summary="Статистика монстра",
        description="""
        Статистика боёв с конкретным типом монстра.
        
        **Анализирует:**
        - Частота появления
        - Винрейт игроков против монстра
        - Средний урон/HP
        - Дропы и награды
        
        **Возвращает:**
        - `monster_kind` - тип монстра
        - `encounters` - количество встреч
        - `player_win_rate` - винрейт игроков
        - `avg_hp` - среднее HP
        - `avg_damage` - средний урон монстра
        - `top_killers` - топ убийц монстра
        - `common_drops` - частые дропы
        
        **Примеры:**
        ```
        /analytics/monster/Кровопийца?days=30
        /analytics/monster/БоссДракон?days=90
        ```
        
        **Примечание:** используйте логин монстра БЕЗ символа $
        """,
        tags=["Analytics - PvE"]
    )
    async def get_monster(
        kind: str = Path(..., description="Тип/имя монстра (без $)"),
        days: int = Query(30, ge=1, le=365, description="Период анализа")
    ):
        stats = await monster_analytics_uc.get_monster(kind=kind, days=days)
        if not stats:
            raise HTTPException(status_code=404, detail="Монстр не найден")
        return stats

    @router.get(
        "/analytics/anomalies",
        summary="Обнаружение аномалий",
        description="""
        Выявляет аномальные события и паттерны в игровой активности.
        
        **Типы аномалий:**
        - Резкий скачок/падение активности
        - Необычные паттерны боёв
        - Подозрительная эффективность (читы/боты)
        - Экономические аномалии (дюп, взломы)
        
        **Возвращает:**
        - `anomaly_type` - тип аномалии
        - `severity` - серьезность (low/medium/high/critical)
        - `description` - описание
        - `affected_players` - затронутые игроки (если есть)
        - `detected_at` - время обнаружения
        - `recommendation` - рекомендации
        
        **Использование:**
        Для мониторинга игровой безопасности и баланса.
        
        **Пример:**
        ```
        /analytics/anomalies?days=7
        ```
        """,
        tags=["Analytics - Security"]
    )
    async def get_anomalies(
        days: int = Query(7, ge=1, le=30, description="Период анализа (макс 30 дней)")
    ):
        return await resource_analytics_uc.get_anomalies(days=days)

    @router.get(
        "/analytics/stats",
        summary="Общая статистика сервера",
        description="""
        Общая статистика сервера за период.
        
        **Включает:**
        - Общее количество боёв
        - Активные игроки (DAU/MAU)
        - Распределение по профессиям
        - PvE vs PvP активность
        - Экономические показатели
        
        **Возвращает:**
        - `total_battles` - всего боёв
        - `active_players` - активных игроков
        - `new_players` - новых игроков
        - `avg_battles_per_day` - среднее боёв в день
        - `pvp_ratio` - доля PvP (0-1)
        - `top_professions` - популярные профессии
        - `server_health` - здоровье сервера (0-100)
        
        **Использование:**
        Для дашборда администратора.
        
        **Пример:**
        ```
        /analytics/stats?days=30
        ```
        """,
        tags=["Analytics - General"]
    )
    async def general_stats(
        days: int = Query(30, ge=1, le=365, description="Период анализа")
    ):
        return await general_stats_uc.get_stats(days=days)

    @router.get("/analytics/antibot/candidates")
    async def analytics_antibot_candidates(limit: int = Query(50, ge=1, le=200), days: int = Query(7, ge=1, le=365)):
        return await player_analytics_uc._a.get_antibot_candidates(limit=limit, days=days)

    @router.get("/analytics/antiboost/pairs")
    async def analytics_antiboost_pairs(days: int = Query(14, ge=1, le=180), min_pairs: int = Query(3, ge=1, le=20)):
        return await player_analytics_uc._a.get_antiboost_pairs(days=days, min_pairs=min_pairs)

    @router.get("/analytics/economy/resources")
    async def analytics_economy_resources(days: int = Query(30, ge=1, le=365)):
        return await resource_analytics_uc.get_economy(days=days)

    # Новые ручки экономики и PvE
    @router.get("/analytics/economy/resources/series")
    async def analytics_resources_series(
        days: int = Query(30, ge=1, le=365),
        bucket: str = Query("day", pattern="^(day|week)$"),
        loc_x: Optional[int] = Query(None),
        loc_y: Optional[int] = Query(None),
        from_date: Optional[datetime] = Query(None),
        to_date: Optional[datetime] = Query(None),
    ):
        # Передадим только один способ задания периода: приоритет from/to
        kwargs = {"days": days, "bucket": bucket, "loc_x": loc_x, "loc_y": loc_y}
        if from_date and to_date:
            kwargs.update({"from_date": from_date.date(), "to_date": to_date.date()})
        return await player_analytics_uc._a.get_resources_series(**kwargs)

    @router.get("/analytics/economy/resources/top-miners")
    async def analytics_resources_top_miners(
        days: int = Query(30, ge=1, le=365),
        loc_x: Optional[int] = Query(None),
        loc_y: Optional[int] = Query(None),
        limit: int = Query(10, ge=1, le=100),
        by: str = Query("player", pattern="^(player|clan)$"),
        from_date: Optional[datetime] = Query(None),
        to_date: Optional[datetime] = Query(None),
        exclude_bots: bool = Query(False, description="Фильтровать ботов (K-means)")  # НОВЫЙ
    ):
        kwargs = {"days": days, "loc_x": loc_x, "loc_y": loc_y, "limit": limit, "by": by, "exclude_bots": exclude_bots}
        if from_date and to_date:
            kwargs.update({"from_date": from_date.date(), "to_date": to_date.date()})
        return await player_analytics_uc._a.get_resources_top_miners(**kwargs)

    @router.get("/analytics/economy/resources/summary")
    async def analytics_resources_summary(
        loc_x: Optional[int] = Query(None),
        loc_y: Optional[int] = Query(None),
        from_date: Optional[datetime] = Query(None),
        to_date: Optional[datetime] = Query(None),
        days: int = Query(30, ge=1, le=365),
    ):
        kwargs = {"loc_x": loc_x, "loc_y": loc_y, "days": days}
        if from_date and to_date:
            kwargs.update({"from_date": from_date.date(), "to_date": to_date.date()})
        return await player_analytics_uc._a.get_resources_summary(**kwargs)

    @router.get("/analytics/pve/load")
    async def analytics_pve_load(
        days: int = Query(30, ge=1, le=365),
        bucket: str = Query("day", pattern="^(day|week)$"),
        loc_x: Optional[int] = Query(None),
        loc_y: Optional[int] = Query(None),
        from_date: Optional[datetime] = Query(None),
        to_date: Optional[datetime] = Query(None),
    ):
        kwargs = {"days": days, "bucket": bucket, "loc_x": loc_x, "loc_y": loc_y}
        if from_date and to_date:
            kwargs.update({"from_date": from_date, "to_date": to_date})
        return await player_analytics_uc._a.get_pve_load(**kwargs)

    @router.get("/analytics/pve/top-locations")
    async def analytics_pve_top_locations(days: int = Query(30, ge=1, le=365), limit: int = Query(10, ge=1, le=100)):
        return await player_analytics_uc._a.get_pve_top_locations(days=days, limit=limit)

    @router.get("/analytics/pve/monsters/breakdown")
    async def analytics_pve_monster_breakdown(
        loc_x: Optional[int] = Query(None),
        loc_y: Optional[int] = Query(None),
        from_date: Optional[datetime] = Query(None),
        to_date: Optional[datetime] = Query(None),
        days: int = Query(30, ge=1, le=365),
        limit: int = Query(100, ge=1, le=1000),
    ):
        return await player_analytics_uc._a.get_pve_monster_breakdown(loc_x=loc_x, loc_y=loc_y, from_date=from_date, to_date=to_date, days=days, limit=limit)

    # ===== Новые аналитики =====
    @router.get("/analytics/survival/player/{login}")
    async def analytics_survival_player(login: str = Path(...), days: int = Query(30, ge=1, le=365)):
        return await player_analytics_uc.get_survival(login=login, days=days)

    @router.get("/analytics/survival/clan/{name}")
    async def analytics_survival_clan(name: str = Path(...), days: int = Query(30, ge=1, le=365)):
        return await clan_analytics_uc.get_survival(name=name, days=days)

    @router.get("/analytics/efficiency/player/{login}")
    async def analytics_efficiency_player(
        login: str = Path(...),
        days: int = Query(30, ge=1, le=365),
        w_p: float = Query(1.0, ge=0.0, le=10.0),
    ):
        return await player_analytics_uc.get_efficiency(login=login, days=days, w_p=w_p)

    @router.get("/analytics/efficiency/top")
    async def analytics_efficiency_top(limit: int = Query(10, ge=1, le=100), days: int = Query(30, ge=1, le=365), w_p: float = Query(1.0, ge=0.0, le=10.0)):
        return await player_analytics_uc.get_efficiency_top(limit=limit, days=days, w_p=w_p)

    @router.get(
        "/analytics/battles/player/{login}",
        summary="История боёв игрока",
        description="""
        Возвращает список боёв игрока за указанный период.
        
        **Параметры дат:**
        - Формат: ISO 8601 (YYYY-MM-DDTHH:MM:SS или YYYY-MM-DD)
        - Примеры: "2025-10-01", "2025-10-11T15:30:00"
        
        **Пример запроса:**
        ```
        /analytics/battles/player/PlayerName?from_date=2025-10-01&to_date=2025-10-11&limit=100
        ```
        """,
        tags=["Analytics - Player"]
    )
    async def analytics_player_battles(
        login: str = Path(..., description="Логин игрока"),
        from_date: Optional[datetime] = Query(None, description="Начальная дата (YYYY-MM-DD или ISO 8601)"),
        to_date: Optional[datetime] = Query(None, description="Конечная дата (YYYY-MM-DD или ISO 8601)"),
        limit: int = Query(1000, ge=1, le=100000, description="Максимум боёв"),
    ):
        """Вернёт список боёв игрока за период: id и ts."""
        db = BattleDatabase()
        where = ["p.login = $1"]
        params: List[Any] = [login]
        arg_idx = 2
        if from_date is not None:
            where.append(f"b.ts >= ${arg_idx}")
            params.append(from_date)
            arg_idx += 1
        if to_date is not None:
            where.append(f"b.ts <= ${arg_idx}")
            params.append(to_date)
            arg_idx += 1
        where_sql = " AND ".join(where)
        query = f"""
            SELECT b.source_id AS battle_id, b.id AS service_id, b.ts
            FROM battles b
            JOIN battle_participants bp ON bp.battle_id = b.id
            JOIN players p ON p.id = bp.player_id
            WHERE {where_sql}
            ORDER BY b.ts ASC
            LIMIT ${arg_idx}
        """
        params.append(limit)
        rows = await db._execute_query(query, *params)
        await db.disconnect()
        return [{"battle_id": r["battle_id"], "service_id": r.get("service_id"), "ts": r["ts"]} for r in rows]

    @router.get(
        "/analytics/antibot/player/{login}",
        summary="Детекция ботов для игрока",
        description="""
        Анализирует поведение игрока для выявления признаков бота.
        
        **Анализируемые паттерны:**
        - Повторяющиеся действия (repetitive_actions)
        - Аномальное время реакций (abnormal_timing)
        - Подозрительная эффективность (suspicious_efficiency)
        - Консистентность действий
        
        **Возвращает:**
        - `is_bot_suspected`: bool - Подозрение на бота
        - `bot_probability`: float (0.0-1.0) - Вероятность
        - `bot_score`: float (0-100) - Общий скор
        - `reasons`: list[string] - Причины подозрения
        - `recommendation`: string - Рекомендация (monitor/investigate/ban)
        
        **Пример:**
        ```
        /analytics/antibot/player/SuspiciousPlayer?days=90
        ```
        """,
        tags=["Analytics - AntiBot"]
    )
    async def analytics_antibot_player_detail(
        login: str = Path(..., description="Логин игрока"),
        days: int = Query(30, ge=1, le=365, description="Период анализа в днях (1-365)")
    ):
        detail = await player_analytics_uc._a.get_antibot_player_detail(login=login, days=days)
        if not detail:
            raise HTTPException(status_code=404, detail="Игрок не найден или недостаточно данных")
        return detail

    @router.get("/admin/loading-stats")
    async def loading_stats(_: str = Depends(require_admin_token)):
        return await admin_logs_uc.loading_stats()

    @router.post("/admin/cleanup")
    async def cleanup(days_old: int = Query(30, ge=1, le=365), _: str = Depends(require_admin_token)):
        deleted = await admin_logs_uc.cleanup(days_old=days_old)
        return {"message": f"Удалено {deleted} старых записей логов", "deleted_count": deleted}
    
    @router.get(
        "/admin/battles-inventory",
        summary="Инвентаризация боёв (файлы vs БД)",
        description="Показывает сколько файлов/боёв и какие диапазоны есть в файлах и в БД",
        tags=["Admin"]
    )
    async def battles_inventory(_: str = Depends(require_admin_token)):
        """Сравнивает файлы с БД и показывает диапазоны"""
        from pathlib import Path
        
        # Собираем battle_id из файлов
        files_battles = set()
        # DEPRECATED: старое зеркало больше не используется
        mirror_path = None
        if False:  # mirror_path and mirror_path.exists():
            for file in []:  # mirror_path.rglob("*.tzb"):
                try:
                    battle_id = int(file.stem)
                    files_battles.add(battle_id)
                except ValueError:
                    continue
        
        # Собираем battle_id из БД
        db = BattleDatabase()
        db_battles_rows = await db._execute_query("SELECT DISTINCT source_id as battle_id FROM battles ORDER BY source_id")
        await db.disconnect()
        db_battles = set(row["battle_id"] for row in db_battles_rows if row.get("battle_id"))
        
        # Анализируем диапазоны
        def find_ranges(ids):
            if not ids:
                return []
            sorted_ids = sorted(ids)
            ranges = []
            start = sorted_ids[0]
            prev = sorted_ids[0]
            
            for current in sorted_ids[1:]:
                if current != prev + 1:
                    if start == prev:
                        ranges.append({"single": start})
                    else:
                        ranges.append({"range": [start, prev], "count": prev - start + 1})
                    start = current
                prev = current
            
            # Последний диапазон
            if start == prev:
                ranges.append({"single": start})
            else:
                ranges.append({"range": [start, prev], "count": prev - start + 1})
            
            return ranges
        
        # Находим разницу
        only_files = files_battles - db_battles
        only_db = db_battles - files_battles
        both = files_battles & db_battles
        
        return {
            "files": {
                "total": len(files_battles),
                "ranges": find_ranges(files_battles)[:50] if len(files_battles) <= 10000 else None,
                "min": min(files_battles) if files_battles else None,
                "max": max(files_battles) if files_battles else None,
            },
            "database": {
                "total": len(db_battles),
                "ranges": find_ranges(db_battles)[:50] if len(db_battles) <= 10000 else None,
                "min": min(db_battles) if db_battles else None,
                "max": max(db_battles) if db_battles else None,
            },
            "comparison": {
                "in_both": len(both),
                "only_in_files": len(only_files),
                "only_in_db": len(only_db),
            },
            "missing_in_db": find_ranges(only_files)[:30] if len(only_files) <= 1000 else {"count": len(only_files), "note": "Слишком много для отображения"},
            "missing_in_files": find_ranges(only_db)[:30] if len(only_db) <= 1000 else {"count": len(only_db), "note": "Слишком много для отображения"},
        }

    @router.post("/battles/upload")
    async def upload_battle_file(file: UploadFile = File(...)):
        """Загружает и обрабатывает TZB файл или архив .tzb.gz"""
        if not (file.filename.endswith('.tzb') or file.filename.endswith('.tzb.gz')):
            raise HTTPException(status_code=400, detail="Только .tzb и .tzb.gz файлы поддерживаются")
        
        try:
            import gzip
            from pathlib import Path
            
            # Читаем содержимое файла
            content = await file.read()
            
            # Извлекаем battle_id из имени файла
            base_name = file.filename.replace('.tzb.gz', '').replace('.tzb', '')
            try:
                battle_id = int(base_name.split('/')[-1])  # Берём последнюю часть после /
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Невозможно извлечь battle_id из имени файла: {file.filename}")
            
            # Определяем шард и создаём правильную структуру
            shard = battle_id // 50000
            raw_dir = Path(os.getenv('LOGS_RAW', '/srv/btl/raw'))
            shard_dir = raw_dir / str(shard)
            shard_dir.mkdir(parents=True, exist_ok=True)
            
            # Правильный путь сохранения
            final_path = shard_dir / f"{battle_id}.tzb"
            
            # Разархивируем если нужно и сохраняем в правильное место
            if file.filename.endswith('.tzb.gz'):
                print(f"🔄 Разархивирую: {file.filename} → {final_path}")
                decompressed_content = gzip.decompress(content)
                with open(final_path, 'wb') as f:
                    f.write(decompressed_content)
            else:
                print(f"💾 Сохраняю: {file.filename} → {final_path}")
                with open(final_path, 'wb') as f:
                    f.write(content)
            
            # Обрабатываем файл через loader
            from app.loader import BattleLoader
            from app.database import BattleDatabase
            
            db = BattleDatabase()
            loader = BattleLoader(db)
            
            # Передаём ПРАВИЛЬНЫЙ путь парсеру
            result = await loader.process_file(str(final_path))
            
            return {
                "message": f"Файл {file.filename} успешно обработан",
                "battle_id": result.get("battle_id"),
                "storage_key": str(final_path),  # Возвращаем правильный путь
                "status": "success"
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")

    # ===== СОЦИАЛЬНЫЕ АНАЛИТИКИ =====
    @router.get(
        "/analytics/social/allies/{login}",
        summary="Союзники игрока",
        description="""
        Возвращает игроков, которые чаще всего воюют на стороне указанного игрока.
        
        **Критерии союзника:**
        - Участвовали в одних боях
        - Были на одной стороне (одинаковый team_id)
        - Высокая частота совместных боёв
        
        **Возвращает:**
        - `ally_login` - логин союзника
        - `battles_together` - количество совместных боёв
        - `win_rate_together` - винрейт в совместных боях
        - `last_battle` - дата последнего боя вместе
        
        **Пример:**
        ```
        /analytics/social/allies/PlayerName?days=90&limit=10
        ```
        """,
        tags=["Analytics - Social"]
    )
    async def analytics_social_allies(
        login: str = Path(..., description="Логин игрока"),
        days: int = Query(30, ge=1, le=365, description="Период анализа"),
        limit: int = Query(10, ge=1, le=50, description="Количество союзников")
    ):
        return await player_analytics_uc._a.get_player_allies(login=login, days=days, limit=limit)

    @router.get(
        "/analytics/social/rivals/{login}",
        summary="Соперники игрока",
        description="""
        Возвращает игроков, которые чаще всего воюют ПРОТИВ указанного игрока.
        
        **Критерии соперника:**
        - Участвовали в одних боях
        - Были на разных сторонах (разный team_id)
        - Высокая частота противостояний
        
        **Возвращает:**
        - `rival_login` - логин соперника
        - `battles_against` - количество боёв против
        - `player_wins` - сколько раз игрок победил
        - `rival_wins` - сколько раз соперник победил
        - `last_battle` - дата последнего противостояния
        
        **Пример:**
        ```
        /analytics/social/rivals/PlayerName?days=90&limit=10
        ```
        """,
        tags=["Analytics - Social"]
    )
    async def analytics_social_rivals(
        login: str = Path(..., description="Логин игрока"),
        days: int = Query(30, ge=1, le=365, description="Период анализа"),
        limit: int = Query(10, ge=1, le=50, description="Количество соперников")
    ):
        return await player_analytics_uc._a.get_player_rivals(login=login, days=days, limit=limit)

    @router.get("/analytics/clans/wars")
    async def analytics_clans_wars(days: int = Query(30, ge=1, le=365), limit: int = Query(20, ge=1, le=100)):
        return await player_analytics_uc._a.get_clan_wars(days=days, limit=limit)

    # ===== ТЕРРИТОРИАЛЬНЫЕ АНАЛИТИКИ =====
    @router.get(
        "/analytics/map/heatmap",
        summary="Тепловая карта активности",
        description="""
        Возвращает координаты и частоту боёв на карте (heatmap).
        
        **Что анализируется:**
        - Координаты всех боёв (x, y из battle_location)
        - Плотность боёв в каждой зоне
        - Популярные места для PvE и PvP
        
        **Возвращает:**
        - `x`, `y` - координаты зоны
        - `battles_count` - количество боёв
        - `avg_participants` - среднее участников
        - `pvp_ratio` - доля PvP боёв (0-1)
        
        **Использование:**
        Для визуализации популярных зон на карте мира.
        
        **Пример:**
        ```
        /analytics/map/heatmap?days=7&limit=200
        ```
        """,
        tags=["Analytics - Map"]
    )
    async def analytics_map_heatmap(
        days: int = Query(30, ge=1, le=365, description="Период анализа"),
        limit: int = Query(100, ge=1, le=500, description="Количество зон")
    ):
        return await player_analytics_uc._a.get_map_heatmap(days=days, limit=limit)

    @router.get(
        "/analytics/map/pvp-hotspots",
        summary="PvP горячие точки",
        description="""
        Возвращает зоны с наибольшей PvP активностью.
        
        **Критерии горячей точки:**
        - Высокая частота PvP боёв (без монстров)
        - Множество уникальных игроков
        - Регулярная активность
        
        **Возвращает:**
        - `location` - название/координаты зоны
        - `pvp_battles` - количество PvP боёв
        - `unique_players` - уникальных игроков
        - `avg_battle_duration` - средняя длительность
        - `danger_level` - уровень опасности (1-10)
        
        **Использование:**
        Для определения опасных зон для новичков.
        
        **Пример:**
        ```
        /analytics/map/pvp-hotspots?days=7&limit=10
        ```
        """,
        tags=["Analytics - Map"]
    )
    async def analytics_map_pvp_hotspots(
        days: int = Query(30, ge=1, le=365, description="Период анализа"),
        limit: int = Query(10, ge=1, le=50, description="Количество зон")
    ):
        return await player_analytics_uc._a.get_pvp_hotspots(days=days, limit=limit)

    @router.get(
        "/analytics/map/clan-control",
        summary="Контроль территорий кланами",
        description="""
        Показывает какие кланы контролируют какие зоны карты.
        
        **Критерии контроля:**
        - Частота боёв клана в зоне
        - Процент побед в зоне
        - Активность членов клана
        
        **Возвращает:**
        - `clan_name` - название клана
        - `controlled_zones` - количество зон под контролем
        - `total_battles` - боёв в контролируемых зонах
        - `control_strength` - сила контроля (0-100)
        - `zones_list` - список зон с координатами
        
        **Использование:**
        Для карты влияния кланов.
        
        **Пример:**
        ```
        /analytics/map/clan-control?days=30&limit=10
        ```
        """,
        tags=["Analytics - Map"]
    )
    async def analytics_map_clan_control(
        days: int = Query(30, ge=1, le=365, description="Период анализа"),
        limit: int = Query(10, ge=1, le=50, description="Количество кланов")
    ):
        return await player_analytics_uc._a.get_clan_control(days=days, limit=limit)

    # ===== ВРЕМЕННЫЕ АНАЛИТИКИ =====
    @router.get(
        "/analytics/time/activity-heatmap",
        summary="Тепловая карта активности по времени",
        description="""
        Показывает распределение активности игроков по времени суток и дням недели.
        
        **Формат данных:**
        - Матрица [день недели][час] = количество боёв
        - День: 0 (понедельник) - 6 (воскресенье)
        - Час: 0-23 (UTC/серверное время)
        
        **Возвращает:**
        - `heatmap` - матрица 7x24 с количеством боёв
        - `peak_day` - самый активный день
        - `peak_hour` - самый активный час
        - `avg_battles_per_hour` - среднее боёв в час
        
        **Использование:**
        Для определения лучшего времени обновлений сервера.
        
        **Пример:**
        ```
        /analytics/time/activity-heatmap?days=30
        ```
        """,
        tags=["Analytics - Time"]
    )
    async def analytics_time_activity_heatmap(
        days: int = Query(30, ge=1, le=365, description="Период анализа")
    ):
        return await player_analytics_uc._a.get_activity_heatmap(days=days)

    @router.get(
        "/analytics/time/peak-hours",
        summary="Пиковые часы активности",
        description="""
        Определяет часы с наибольшей активностью игроков.
        
        **Анализирует:**
        - Количество боёв по часам
        - Количество уникальных игроков
        - Средняя длительность боёв
        
        **Возвращает:**
        - `hour` - час суток (0-23)
        - `battles_count` - количество боёв
        - `unique_players` - уникальных игроков
        - `avg_duration_minutes` - средняя длительность
        - `is_prime_time` - пиковое время (true/false)
        
        **Использование:**
        Для планирования ивентов и технических работ.
        
        **Пример:**
        ```
        /analytics/time/peak-hours?days=30
        ```
        """,
        tags=["Analytics - Time"]
    )
    async def analytics_time_peak_hours(
        days: int = Query(30, ge=1, le=365, description="Период анализа")
    ):
        return await player_analytics_uc._a.get_peak_hours(days=days)

    # ===== ЭКОНОМИКА РАСШИРЕННАЯ =====
    @router.get(
        "/analytics/economy/farm-efficiency/{login}",
        summary="Эффективность фарма игрока",
        description="""
        Анализирует эффективность добычи ресурсов игроком.
        
        **Метрики эффективности:**
        - Ресурсов за бой (resources per battle)
        - Ресурсов за час (resources per hour)
        - Соотношение PvE/PvP времени
        - Эффективность профессии
        
        **Возвращает:**
        - `avg_resources_per_battle` - среднее ресурсов за бой
        - `total_resources` - всего добыто
        - `farm_time_hours` - часов на фарм
        - `efficiency_score` - скор эффективности (0-100)
        - `best_resource` - самый добываемый ресурс
        - `recommendations` - рекомендации по улучшению
        
        **Использование:**
        Для оптимизации фарм-стратегии.
        
        **Пример:**
        ```
        /analytics/economy/farm-efficiency/PlayerName?days=30
        ```
        """,
        tags=["Analytics - Economy"]
    )
    async def analytics_economy_farm_efficiency(
        login: str = Path(..., description="Логин игрока"),
        days: int = Query(30, ge=1, le=365, description="Период анализа")
    ):
        return await player_analytics_uc._a.get_farm_efficiency(login=login, days=days)

    @router.get("/analytics/economy/rare-items")
    async def analytics_economy_rare_items(days: int = Query(30, ge=1, le=365), limit: int = Query(20, ge=1, le=100)):
        return await player_analytics_uc._a.get_rare_items(days=days, limit=limit)

    # ===== СОРЕВНОВАТЕЛЬНЫЕ МЕТРИКИ =====
    @router.get(
        "/analytics/pvp/elo",
        summary="PvP рейтинг ELO",
        description="""
ELO рейтинг игроков в PvP боях (players_cnt > 1).

**Что такое ELO:**
- ELO - это система рейтингов, разработанная Арпадом Эло для шахмат
- Каждый игрок начинает с базового рейтинга (обычно 1000)
- При победе рейтинг растёт, при поражении - падает
- Изменение зависит от разницы: победа над сильным даёт больше очков
- Чем выше ELO, тем сильнее игрок в PvP
        """,
        tags=["Analytics - PvP"]
    )
    async def analytics_pvp_elo(days: int = Query(30, ge=1, le=365), limit: int = Query(50, ge=1, le=200)):
        return await player_analytics_uc._a.get_player_elo_pvp(days=days, limit=limit)

    @router.get(
        "/analytics/pve/elo",
        summary="PvE рейтинг ELO",
        description="""
ELO рейтинг игроков в PvE боях (monsters_cnt > 0).

**Формула:**
- Базовый рейтинг: 1000
- ELO = 1000 + (побед - поражений) × 10
- Учитываются только бои против монстров
- Минимум 10 боёв для попадания в рейтинг
        """,
        tags=["Analytics - PvE"]
    )
    async def analytics_pve_elo(days: int = Query(30, ge=1, le=365), limit: int = Query(50, ge=1, le=200)):
        return await player_analytics_uc._a.get_player_elo_pve(days=days, limit=limit)

    @router.get("/analytics/streaks/{login}")
    async def analytics_streaks(login: str = Path(...), days: int = Query(30, ge=1, le=365)):
        return await player_analytics_uc._a.get_player_streaks(login=login, days=days)

    # ===== МЕТА-АНАЛИЗ =====
    @router.get(
        "/analytics/meta/professions",
        summary="Мета профессий",
        description="""
        Статистика использования и эффективности профессий.
        
        **battle_type параметр:**
        - `all` - Все бои (PvE + PvP)
        - `pve` - Только PvE бои
        - `pvp` - Только PvP бои
        
        **Зачем разделять:**
        PvE профессии (Старатель, Сталкер) доминируют в общей статистике,
        искажая мету для PvP игроков.
        
        **Возвращает:**
        - Винрейт по профессиям
        - Процент использования (pick rate)
        - Средний урон/убийства
        - Тренды (rising/stable/declining)
        """,
        tags=["Analytics - Meta"]
    )
    async def analytics_meta_professions(
        days: int = Query(30, ge=1, le=365, description="Период анализа"),
        battle_type: str = Query("all", regex="^(all|pve|pvp)$", description="Тип боёв: all/pve/pvp")
    ):
        return await player_analytics_uc._a.get_profession_stats(days=days, battle_type=battle_type)

    @router.get(
        "/players/by-profession",
        summary="Игроки по профессии",
        description="""
Получить список игроков по профессии.

**Полный список профессий:**
- 0: без профессии
- 1: корсар
- 2: сталкер  
- 3: старатель
- 4: инженер
- 5: наемник
- 6: торговец
- 7: патрульный
- 8: штурмовик
- 9: специалист
- 10: журналист
- 11: чиновник
- 12: псионик
- 13: каторжник
- 14: пси-кинетик
- 15: пси-медик
- 16: пси-лидер
- 17: полиморф
        """,
        tags=["Players"]
    )
    async def get_players_by_profession(
        profession: str = Query(..., description="Название профессии (например: 'без профессии', 'сталкер')"),
        limit: int = Query(50, ge=1, le=500, description="Количество игроков"),
        days: int = Query(365, ge=1, le=365, description="За последние N дней"),
        min_battles: int = Query(1, ge=1, le=1000, description="Минимум боёв для фильтрации")
    ):
        """Получить список игроков по профессии с их статистикой"""
        return await player_analytics_uc._a.get_players_by_profession(
            profession=profession, 
            limit=limit, 
            days=days,
            min_battles=min_battles
        )

    @router.get(
        "/analytics/meta/balance",
        summary="Баланс профессий",
        description="""
        Анализ баланса профессий (win rate, pick rate, эффективность).
        
        **battle_type параметр:**
        - `all` - Все бои
        - `pve` - Только PvE (фарм, боссы)
        - `pvp` - Только PvP (игрок vs игрок)
        
        **Используйте:**
        - `pve` для анализа фарм-меты
        - `pvp` для анализа PvP-меты
        - `all` для общей картины
        
        **Возвращает:**
        - Винрейт по профессиям
        - Pick rate (% от всех боёв)
        - Средний урон, убийства
        - Тренды изменения популярности
        """,
        tags=["Analytics - Meta"]
    )
    async def analytics_meta_balance(
        days: int = Query(30, ge=1, le=365, description="Период анализа"),
        battle_type: str = Query("all", regex="^(all|pve|pvp)$", description="Тип боёв: all/pve/pvp")
    ):
        return await player_analytics_uc._a.get_balance_report(days=days, battle_type=battle_type)

    # ===== ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА =====
    @router.get(
        "/analytics/predictions/churn",
        summary="Предсказание оттока игроков",
        description="""
        Предсказывает игроков, которые могут покинуть игру (churn prediction).
        
        **ML алгоритм:**
        - Анализирует паттерны активности
        - Снижение частоты боёв
        - Снижение длительности сессий
        - Отсутствие прогресса
        
        **Возвращает:**
        - `login` - логин игрока
        - `churn_probability` - вероятность оттока (0-1)
        - `churn_score` - скор оттока (0-100)
        - `risk_level` - уровень риска (low/medium/high)
        - `last_active` - последняя активность
        - `activity_trend` - тренд (-50% = резкое снижение)
        - `recommendations` - рекомендации по удержанию
        
        **Использование:**
        Для retention-кампаний и удержания игроков.
        
        **Пример:**
        ```
        /analytics/predictions/churn?days=30&limit=100
        ```
        """,
        tags=["Analytics - ML"]
    )
    async def analytics_predictions_churn(
        days: int = Query(30, ge=1, le=365, description="Период анализа"),
        limit: int = Query(50, ge=1, le=200, description="Количество игроков")
    ):
        return await player_analytics_uc._a.get_churn_prediction(days=days, limit=limit)

    @router.get("/analytics/recommendations/farming/{login}")
    async def analytics_recommendations_farming(login: str = Path(...), days: int = Query(30, ge=1, le=365)):
        return await player_analytics_uc._a.get_farming_recommendations(login=login, days=days)

    # ===== ML / PLAYSTYLE =====
    
    @router.get("/analytics/playstyle/{login}")
    async def analytics_playstyle(login: str = Path(...), days: int = Query(90, ge=7, le=365)):
        """Классификация стиля игры с помощью K-means"""
        try:
            from app.ml.playstyle_classifier import PlaystyleClassifier, SKLEARN_AVAILABLE
        except ImportError:
            raise HTTPException(status_code=501, detail="ML модуль не установлен")
        
        if not SKLEARN_AVAILABLE:
            raise HTTPException(status_code=501, detail="scikit-learn не установлен")
        
        # Получаем player_id
        player_id = await player_analytics_uc._a._get_player_id_by_login(login)
        if not player_id:
            raise HTTPException(status_code=404, detail=f"Игрок {login} не найден")
        
        # Загружаем/создаём классификатор
        classifier = PlaystyleClassifier()
        
        # Пытаемся загрузить обученную модель
        if not classifier.load_model():
            # Модель не обучена - возвращаем ошибку с подсказкой
            raise HTTPException(
                status_code=503, 
                detail="Модель не обучена. Админу: запустите POST /admin/ml/train-playstyle"
            )
        
        # Классифицируем игрока
        db = BattleDatabase()
        result = await classifier.classify_player(player_id, db, days=days)
        await db.disconnect()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Недостаточно данных для классификации (минимум 5 боёв)")
        
        return result
    
    @router.get("/analytics/playstyle/clusters/stats")
    async def analytics_playstyle_clusters():
        """Статистика по всем кластерам стилей игры"""
        try:
            from app.ml.playstyle_classifier import PlaystyleClassifier, SKLEARN_AVAILABLE
        except ImportError:
            raise HTTPException(status_code=501, detail="ML модуль не установлен")
        
        if not SKLEARN_AVAILABLE:
            raise HTTPException(status_code=501, detail="scikit-learn не установлен")
        
        classifier = PlaystyleClassifier()
        
        if not classifier.load_model():
            raise HTTPException(status_code=503, detail="Модель не обучена")
        
        return {
            "clusters": classifier.get_cluster_stats(),
            "total_clusters": classifier.n_clusters,
        }
    
    # ===== XML SYNC ENDPOINTS =====
    
    @router.get("/admin/xml-sync/workers/health")
    async def xml_sync_workers_health(_token = Depends(require_admin_token)):
        """Проверить здоровье всех XML воркеров"""
        from app.xml_sync_worker import XmlSyncWorker
        worker = XmlSyncWorker()
        return await worker.check_workers_health()
    
    @router.post("/admin/xml-sync/battle/{battle_id}")
    async def xml_sync_single_battle(
        battle_id: int = Path(..., ge=1),
        _token = Depends(require_admin_token)
    ):
        """Запросить один лог боя через XML протокол"""
        from app.xml_sync_client import XmlSyncClient
        from app.database import BattleDatabase
        
        client = XmlSyncClient()
        db = BattleDatabase()
        
        # Проверяем не запрашивали ли уже
        existing = await db._execute_one(
            "SELECT battle_id, status FROM xml_sync_log WHERE battle_id = $1",
            battle_id
        )
        
        if existing and existing['status'] == 'success':
            await db.disconnect()
            return {
                "message": f"Бой {battle_id} уже был успешно запрошен ранее",
                "battle_id": battle_id,
                "status": "already_exists"
            }
        
        # Запрашиваем лог
        result = client.request_and_save(battle_id)
        
        # Сохраняем в лог
        if result:
            await db._execute_command(
                """
                INSERT INTO xml_sync_log (battle_id, requested_at, status, error_message, file_path, size_bytes)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (battle_id) DO UPDATE SET
                    requested_at = EXCLUDED.requested_at,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    file_path = EXCLUDED.file_path,
                    size_bytes = EXCLUDED.size_bytes
                """,
                battle_id,
                datetime.now(),
                result['status'],
                result.get('error'),
                result.get('file_path'),
                result.get('size_bytes')
            )
        
        await db.disconnect()
        return result
    
    @router.post("/admin/xml-sync/range")
    async def xml_sync_range(
        start_id: int = Query(..., ge=1, description="Начальный ID боя"),
        end_id: int = Query(..., ge=1, description="Конечный ID боя"),
        skip_existing: bool = Query(True, description="Пропускать уже запрошенные бои"),
        _token = Depends(require_admin_token)
    ):
        """Запросить диапазон логов боев через HTTP воркеры"""
        from app.xml_sync_worker import XmlSyncWorker
        
        if end_id < start_id:
            raise HTTPException(status_code=400, detail="end_id должен быть >= start_id")
        
        if end_id - start_id > 1000:
            raise HTTPException(status_code=400, detail="Максимальный диапазон: 1000 боев за раз")
        
        worker = XmlSyncWorker()
        result = await worker.sync_range(start_id, end_id, skip_existing)
        
        return result
    
    @router.get("/admin/xml-sync/status")
    async def xml_sync_status(_token = Depends(require_admin_token)):
        """Получить статистику XML синхронизации"""
        from app.database import BattleDatabase
        
        db = BattleDatabase()
        
        stats = await db._execute_one("""
            SELECT 
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE status = 'success') as success_count,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                MIN(battle_id) as min_battle_id,
                MAX(battle_id) as max_battle_id,
                MAX(requested_at) as last_request
            FROM xml_sync_log
        """)
        
        await db.disconnect()
        
        return {
            "total_requests": stats['total_requests'] or 0,
            "success_count": stats['success_count'] or 0,
            "failed_count": stats['failed_count'] or 0,
            "min_battle_id": stats['min_battle_id'],
            "max_battle_id": stats['max_battle_id'],
            "last_request": stats['last_request'].isoformat() if stats['last_request'] else None
        }
    
    @router.get("/admin/xml-sync/requested")
    async def xml_sync_requested(
        limit: int = Query(50, ge=1, le=500, description="Количество записей"),
        status: Optional[str] = Query(None, description="Фильтр по статусу: success, failed"),
        _token = Depends(require_admin_token)
    ):
        """Получить список запрошенных боев"""
        from app.database import BattleDatabase
        
        db = BattleDatabase()
        
        if status:
            query = """
                SELECT battle_id, requested_at, status, error_message, file_path, size_bytes
                FROM xml_sync_log
                WHERE status = $1
                ORDER BY requested_at DESC
                LIMIT $2
            """
            rows = await db._execute_query(query, status, limit)
        else:
            query = """
                SELECT battle_id, requested_at, status, error_message, file_path, size_bytes
                FROM xml_sync_log
                ORDER BY requested_at DESC
                LIMIT $1
            """
            rows = await db._execute_query(query, limit)
        
        await db.disconnect()
        
        return {
            "count": len(rows),
            "limit": limit,
            "status_filter": status,
            "battles": [
                {
                    "battle_id": row['battle_id'],
                    "requested_at": row['requested_at'].isoformat() if row['requested_at'] else None,
                    "status": row['status'],
                    "error_message": row['error_message'],
                    "file_path": row['file_path'],
                    "size_bytes": row['size_bytes']
                }
                for row in rows
            ]
        }
    
    @router.delete("/admin/xml-sync/cleanup")
    async def xml_sync_cleanup(_token = Depends(require_admin_token)):
        """Очистить временные файлы .tzb из /tmp/"""
        import glob
        
        files = glob.glob("/tmp/*.tzb")
        deleted_count = 0
        
        for file_path in files:
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Не удалось удалить {file_path}: {e}")
        
        return {
            "message": f"Удалено {deleted_count} временных файлов",
            "deleted_count": deleted_count
        }
    
    @router.get("/admin/xml-sync/errors")
    async def xml_sync_errors(
        limit: int = Query(100, ge=1, le=1000, description="Количество записей"),
        error_type: str = Query("all", description="Тип: all, failed, response_timeout"),
        _token = Depends(require_admin_token)
    ):
        """Получить список боев с ошибками"""
        from app.database import BattleDatabase
        
        db = BattleDatabase()
        
        if error_type == "all":
            query = """
                SELECT battle_id, requested_at, status, error_message
                FROM xml_sync_log
                WHERE status IN ('failed', 'response_timeout')
                ORDER BY battle_id
                LIMIT $1
            """
            rows = await db._execute_query(query, limit)
        else:
            query = """
                SELECT battle_id, requested_at, status, error_message
                FROM xml_sync_log
                WHERE status = $1
                ORDER BY battle_id
                LIMIT $2
            """
            rows = await db._execute_query(query, error_type, limit)
        
        await db.disconnect()
        
        return {
            "count": len(rows),
            "error_type": error_type,
            "battles": [
                {
                    "battle_id": row['battle_id'],
                    "requested_at": row['requested_at'].isoformat() if row['requested_at'] else None,
                    "status": row['status'],
                    "error_message": row['error_message']
                }
                for row in rows
            ]
        }
    
    @router.post("/admin/xml-sync/retry-failed")
    async def xml_sync_retry_failed(
        limit: int = Query(100, ge=1, le=500, description="Сколько боев попробовать докачать"),
        workers: int = Query(1, ge=1, le=5, description="Количество параллельных воркеров"),
        _token = Depends(require_admin_token)
    ):
        """Докачать бои с ошибками (failed, response_timeout)"""
        from app.xml_sync_worker import XmlSyncWorker
        
        worker = XmlSyncWorker()
        result = await worker.sync_missing(limit=limit)
        
        return result
    
    @router.post("/admin/xml-sync/auto-continue")
    async def xml_sync_auto_continue(
        batch_size: int = Query(1000, ge=1, le=1000, description="Размер пачки"),
        workers: int = Query(1, ge=1, le=5, description="Количество параллельных воркеров"),
        _token = Depends(require_admin_token)
    ):
        """Автоматическая синхронизация: продолжить с последнего успешного боя"""
        from app.xml_sync_worker import XmlSyncWorker
        
        worker = XmlSyncWorker()
        result = await worker.sync_auto_continue(batch_size=batch_size)
        
        return result

    @router.post(
        "/admin/xml-sync/fetch-new",
        summary="Умная загрузка новых логов",
        description="""
        Умная загрузка НОВЫХ логов после последнего успешного + автопарсинг.
        
        **Алгоритм:**
        1. Находит MAX(battle_id) из успешных в xml_sync_log
        2. Загружает count новых логов через 6 XML воркеров (или все доступные если count=None)
        3. Автоматический retry для failed/timeout логов
        4. Опциональный автопарсинг через api_mother с контролем параллельности
        
        **Примеры:**
        - `count=300` - загрузить 300 следующих логов
        - `count=None` - загрузить все новые до battle_id=3780000
        - `auto_parse=true` - автоматически распарсить в БД
        - `max_parallel=10` - параллельность парсинга (рекомендуется 1-3)
        
        **Производительность:** ~10 логов/сек, 300 логов за ~20-30 секунд
        """,
        tags=["Admin - XML Sync"],
        responses={
            200: {"description": "Успешная загрузка с детальной статистикой"},
            403: {"description": "Неверный admin token"}
        }
    )
    async def xml_sync_fetch_new(
        count: Optional[int] = Query(None, ge=1, le=1000000, description="Количество логов (None=все до текущего)"),
        from_battle_id: Optional[int] = Query(None, ge=1, description="От какого battle_id считать новые (если не указан - ищет MAX в БД)"),
        auto_parse: bool = Query(True, description="Автоматически распарсить"),
        max_parallel: int = Query(10, ge=1, le=20, description="Параллельность парсинга"),
        _token = Depends(require_admin_token)
    ):
        """
        Умная загрузка НОВЫХ логов после последнего успешного + автопарсинг
        
        Алгоритм:
        1. Находит MAX(battle_id) из успешных (или использует from_battle_id)
        2. Загружает count логов (или все до текущего если count=None)
        3. Retry для failed/timeout
        4. Автоматически парсит через api_mother
        """
        import httpx
        from app.xml_sync_worker import XmlSyncWorker
        
        worker = XmlSyncWorker()
        await worker._init_db()  # Инициализируем БД
        
        # Определяем стартовый ID
        if from_battle_id is not None:
            # Используем указанный battle_id
            start_id = from_battle_id
            print(f"🎯 fetch-new: Используем from_battle_id={from_battle_id}, start_id={start_id}")
            logger.info(f"✅ Используем from_battle_id: {from_battle_id}")
        else:
            # Ищем последний успешный лог в БД
            query = "SELECT MAX(battle_id) as max_id FROM xml_sync_log WHERE status = 'success'"
            result = await worker.db._execute_query(query)
            
            if not result or result[0]['max_id'] is None:
                start_id = 3772607
                print(f"📊 fetch-new: MAX не найден, используем дефолт start_id={start_id}")
                logger.info(f"📊 MAX не найден, используем дефолт: {start_id}")
            else:
                start_id = result[0]['max_id'] + 1
                print(f"📊 fetch-new: Найден MAX={result[0]['max_id']}, start_id={start_id}")
                logger.info(f"📊 Найден MAX: {result[0]['max_id']}, start_id: {start_id}")
        
        # Если count не указан - загружаем до текущего максимального (3772606 + новые)
        if count is None:
            end_id = 3780000  # Загружаем с запасом
        else:
            end_id = start_id + count - 1
        
        # Загружаем через XML sync
        sync_result = await worker.sync_range(start_id, end_id, skip_existing=False)
        
        # Retry для failed/timeout
        retry_count = 0
        if sync_result.get('failed', 0) > 0 or sync_result.get('timeout', 0) > 0:
            retry_result = await worker.sync_missing()
            retry_count = retry_result.get('total_synced', 0)
        
        # Автопарсинг
        parsed_count = 0
        if auto_parse and sync_result.get('success', 0) > 0:
            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(
                        "http://host-api-service-api_mother-1:8083/process-batch",
                        params={"limit": count + 100, "max_parallel": max_parallel}
                    )
                    if response.status_code == 200:
                        parse_result = response.json()
                        parsed_count = parse_result.get('processed', 0)
            except Exception as e:
                logger.error(f"Ошибка автопарсинга: {e}")
        
        return {
            "range": {"start": start_id, "end": end_id},
            "downloaded": sync_result.get('success', 0),
            "failed": sync_result.get('failed', 0),
            "timeout": sync_result.get('timeout', 0),
            "retried": retry_count,
            "parsed": parsed_count,
            "workers_used": sync_result.get('workers_used', 0),
            "worker_stats": sync_result.get('worker_stats', {})
        }

    @router.post(
        "/admin/xml-sync/fetch-old",
        summary="Умная загрузка старых логов",
        description="""
        Умная загрузка СТАРЫХ логов до самого раннего успешного + автопарсинг.
        
        **Алгоритм:**
        1. Находит MIN(battle_id) из успешных в xml_sync_log
        2. Загружает count старых логов через 6 XML воркеров (или все до battle_id=1475356 если count=None)
        3. Автоматический retry для failed/timeout логов
        4. Опциональный автопарсинг через api_mother с контролем параллельности
        
        **Примеры:**
        - `count=300` - загрузить 300 предыдущих логов
        - `count=None` - загрузить все старые до battle_id=1475356
        - `auto_parse=true` - автоматически распарсить в БД
        - `max_parallel=10` - параллельность парсинга (рекомендуется 1-3)
        
        **Производительность:** ~10 логов/сек, 300 логов за ~20-30 секунд
        """,
        tags=["Admin - XML Sync"],
        responses={
            200: {"description": "Успешная загрузка с детальной статистикой"},
            400: {"description": "Нет успешных логов для определения начальной точки"},
            403: {"description": "Неверный admin token"}
        }
    )
    async def xml_sync_fetch_old(
        count: Optional[int] = Query(None, ge=1, le=1000000, description="Количество логов (None=все до первого)"),
        from_battle_id: Optional[int] = Query(None, ge=1, description="От какого battle_id считать старые (если не указан - ищет MIN в БД)"),
        auto_parse: bool = Query(True, description="Автоматически распарсить"),
        max_parallel: int = Query(10, ge=1, le=20, description="Параллельность парсинга"),
        _token = Depends(require_admin_token)
    ):
        """
        Умная загрузка СТАРЫХ логов до самого раннего успешного + автопарсинг
        
        Алгоритм:
        1. Находит MIN(battle_id) из успешных (или использует from_battle_id)
        2. Загружает count логов (или все до battle_id=1 если count=None)
        3. Retry для failed/timeout
        4. Автоматически парсит через api_mother
        """
        import httpx
        from app.xml_sync_worker import XmlSyncWorker
        from app.xml_sync_state import get_sync_state
        
        state = get_sync_state()
        
        # Проверка: нет ли уже запущенной операции
        status = await state.get_status()
        if status["is_running"]:
            raise HTTPException(
                status_code=409,
                detail=f"Операция уже выполняется: {status['current_operation']}. Используйте /admin/xml-sync/abort для прерывания."
            )
        
        worker = XmlSyncWorker()
        await worker._init_db()  # Инициализируем БД
        
        # Определяем конечный ID
        if from_battle_id is not None:
            # Используем указанный battle_id - 1 (загружаем старые ДО этого ID)
            end_id = from_battle_id - 1
            print(f"🎯 fetch-old: Используем from_battle_id={from_battle_id}, end_id={end_id}")
        else:
            # Ищем самый ранний успешный лог в БД
            query = "SELECT MIN(battle_id) as min_id FROM xml_sync_log WHERE status = 'success'"
            result = await worker.db._execute_query(query)
            
            if not result or result[0]['min_id'] is None:
                raise HTTPException(
                    status_code=400,
                    detail="Нет успешных логов. Используйте /fetch-new"
                )
            
            min_id = result[0]['min_id']
            end_id = min_id - 1
            print(f"📊 fetch-old: Найден MIN={min_id}, end_id={end_id}")
        
        # Если count не указан - загружаем все от 1 до min_id
        if count is None:
            start_id = max(1, 1475356)  # Самый ранний известный бой
        else:
            start_id = max(1, end_id - count + 1)
        
        if start_id > end_id:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно загрузить: минимальный ID уже {min_id}"
            )
        
        # Начинаем операцию
        operation_name = f"fetch-old: {start_id}-{end_id}"
        await state.start_operation(operation_name, end_id - start_id + 1)
        
        try:
            # Загружаем через XML sync
            sync_result = await worker.sync_range(start_id, end_id, skip_existing=False)
            
            # Проверяем прерывание
            if sync_result.get('aborted', False):
                return {
                    "status": "aborted",
                    "range": {"start": start_id, "end": end_id},
                    "downloaded": sync_result.get('success', 0),
                    "failed": sync_result.get('failed', 0),
                    "timeout": sync_result.get('timeout', 0),
                    "message": "Операция прервана по запросу"
                }
            
            # Retry для failed/timeout (только если не было прерывания)
            retry_count = 0
            if not state.check_abort() and (sync_result.get('failed', 0) > 0 or sync_result.get('timeout', 0) > 0):
                retry_result = await worker.sync_missing()
                retry_count = retry_result.get('total_synced', 0)
            
            # Автопарсинг
            parsed_count = 0
            if not state.check_abort() and auto_parse and sync_result.get('success', 0) > 0:
                try:
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        response = await client.post(
                            "http://host-api-service-api_mother-1:8083/process-batch",
                            params={"limit": (count or 10000) + 100, "max_parallel": max_parallel}
                        )
                        if response.status_code == 200:
                            parse_result = response.json()
                            parsed_count = parse_result.get('processed', 0)
                except Exception as e:
                    logger.error(f"Ошибка автопарсинга: {e}")
            
            return {
                "range": {"start": start_id, "end": end_id},
                "downloaded": sync_result.get('success', 0),
                "failed": sync_result.get('failed', 0),
                "timeout": sync_result.get('timeout', 0),
                "retried": retry_count,
                "parsed": parsed_count,
                "aborted": state.check_abort()
            }
        finally:
            # Завершаем операцию
            await state.finish_operation()

    @router.post(
        "/admin/xml-sync/abort",
        summary="Прервать текущую XML Sync операцию",
        description="""
        Отправляет сигнал прерывания для текущей длительной операции.
        
        Операция будет остановлена **безопасно** после завершения текущего батча.
        """,
        tags=["Admin - XML Sync"]
    )
    async def xml_sync_abort(_token = Depends(require_admin_token)):
        """Прервать текущую XML Sync операцию"""
        from app.xml_sync_state import get_sync_state
        
        state = get_sync_state()
        status = await state.get_status()
        
        if not status["is_running"]:
            raise HTTPException(
                status_code=400,
                detail="Нет активных операций для прерывания"
            )
        
        await state.request_abort()
        
        return {
            "status": "abort_requested",
            "operation": status["current_operation"],
            "progress": status["progress"],
            "message": "Прерывание запрошено, операция остановится после текущего батча"
        }

    @router.get(
        "/admin/xml-sync/progress",
        summary="Прогресс текущей операции",
        description="Показывает прогресс выполнения текущей XML Sync операции",
        tags=["Admin - XML Sync"]
    )
    async def xml_sync_progress(_token = Depends(require_admin_token)):
        """Получить прогресс текущей операции"""
        from app.xml_sync_state import get_sync_state
        
        state = get_sync_state()
        status = await state.get_status()
        
        return status

    @router.post("/admin/ml/train-playstyle")
    async def admin_train_playstyle(
        days: int = Query(90, ge=30, le=365),
        _token = Depends(require_admin_token)
    ):
        """Обучение K-means модели классификации стилей (требует admin token)"""
        try:
            from app.ml.playstyle_classifier import train_playstyle_model, SKLEARN_AVAILABLE
        except ImportError:
            raise HTTPException(status_code=501, detail="ML модуль не установлен")
        
        if not SKLEARN_AVAILABLE:
            raise HTTPException(status_code=501, detail="scikit-learn не установлен")
        
        db = BattleDatabase()
        result = await train_playstyle_model(db, days=days)
        await db.disconnect()
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        return result
    
    @router.post("/admin/ml/train-botdetector")
    async def admin_train_botdetector(
        days: int = Query(90, ge=30, le=365),
        _token = Depends(require_admin_token)
    ):
        """Обучение Voting Ensemble (K-means + Isolation Forest) для детекции ботов"""
        try:
            from app.ml.bot_detector import train_bot_detector, SKLEARN_AVAILABLE
        except ImportError:
            raise HTTPException(status_code=501, detail="BotDetector не установлен")
        
        if not SKLEARN_AVAILABLE:
            raise HTTPException(status_code=501, detail="scikit-learn не установлен")
        
        db = BattleDatabase()
        result = await train_bot_detector(db, days=days)
        await db.disconnect()
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        return result

    return router


