"""
Аналитические запросы для API_4
Антибот, экономика, командная динамика и другие аналитики
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from dataclasses import dataclass

from app.database import BattleDatabase
from app.models import (
    PlayerStats, ClanStats, ResourceStats, MonsterStats,
    DailyPlayerFeatures, DailyClanFeatures, ResourceAnomaly, BotSuspicion
)


@dataclass
class AnalyticsConfig:
    """Конфигурация для аналитики"""
    z_score_threshold: float = 2.0
    bot_suspicion_threshold: float = 0.6
    min_battles_for_analysis: int = 10
    lookback_days: int = 30
    # Пороговые значения и веса для гибкого скоринга антибота
    activity_high: int = 100                 # линейная шкала активности: от min_battles_for_analysis до activity_high
    sr_mid: float = 0.7                      # SR, с которого начинается рост подозрительности
    sr_high: float = 0.95                    # SR, при котором достигается максимум по SR
    kpm_mid: float = 1.0                     # PvP KPM, с которого начинается рост подозрительности
    kpm_high: float = 5.0                    # PvP KPM, при котором достигается максимум по KPM
    pve_kpm_mid: float = 10.0                # PvE KPM, с которого начинаем считать PvE-фокус заметным
    pve_kpm_high: float = 25.0               # PvE KPM, при котором PvE-фокус максимален
    pvp_kpm_low: float = 0.3                 # Низкий PvP KPM, усиливающий PvE штраф
    intervals_std_ratio_thresh: float = 0.1  # std/mean ниже этого — максимально регулярные интервалы
    max_gap_hours_low: float = 8.0           # если max_gap ниже — сильный вклад в подозрительность
    hour_spread_narrow: float = 4.0          # узкое окно часов активности
    active_hours_ratio_high: float = 20.0/24.0  # квази-круглосуточность
    # Короткие интервалы между боями
    short_interval_sec: float = 0.5             # порог короткого интервала, сек (боты < 0.5 сек)
    ultra_short_interval_sec: float = 0.5       # ультра-короткие интервалы (только боты)
    short_interval_streak_high: int = 50        # длинная серия коротких интервалов (увеличено)
    short_interval_ratio_high: float = 0.7      # доля коротких интервалов
    ultra_short_ratio_high: float = 0.3         # 30%+ интервалов < 0.5 сек = бот
    
    # Длинные сессии без перерывов (марафоны)
    marathon_session_hours: float = 3.0         # сессия 3+ часа без перерывов = подозрительно
    natural_break_minutes: float = 5.0          # перерыв > 5 минут = естественная пауза

    # Веса метрик
    w_activity: float = 0.20                 # снижен (активность != бот)
    w_sr: float = 0.10                       # снижен (SR != бот)
    w_kpm: float = 0.10                      # снижен (KPM != бот)
    w_intervals_regular: float = 0.15
    w_max_gap: float = 0.10                  # снижен
    w_hour_spread_or_ratio: float = 0.10     # снижен
    w_pve_penalty: float = 0.05              # СИЛЬНО снижен (PvE игроки != боты)
    w_short_intervals: float = 0.20          # средний вес
    w_ultra_short_intervals: float = 0.40    # НОВЫЙ: главный признак бота!
    w_marathon_sessions: float = 0.35        # НОВЫЙ: сессии без перерывов
    w_in_session_gap: float = 0.15           # средний вклад


class BattleAnalytics:
    """Аналитика боёв"""
    
    def __init__(self, db: BattleDatabase, config: Optional[AnalyticsConfig] = None):
        self.db = db
        self.config = config or AnalyticsConfig()
    
    # ===== СТАТИСТИКА ИГРОКОВ =====
    
    async def get_player_stats(
        self, 
        player_id: Optional[int] = None,
        login: Optional[str] = None,
        days: int = 30
    ) -> Optional[PlayerStats]:
        """Получение статистики игрока"""
        if not player_id and not login:
            return None
        
        # Определяем player_id если передан login
        if not player_id and login:
            player_id = await self._get_player_id_by_login(login)
            if not player_id:
                return None
        
        query = """
            SELECT 
                p.id as player_id,
                p.login,
                COUNT(bp.battle_id) as battles_count,
                SUM(CASE WHEN bp.survived = true THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN bp.survived = false THEN 1 ELSE 0 END) as losses,
                SUM(bp.kills_monsters) as kills_monsters,
                SUM(bp.kills_players) as kills_players,
                AVG(bp.rank_points) as rank_points_avg,
                AVG(bp.pve_points) as pve_points_avg
            FROM players p
            JOIN battle_participants bp ON p.id = bp.player_id
            JOIN battles b ON bp.battle_id = b.id
            WHERE p.id = $1
            AND b.ts >= $2
            GROUP BY p.id, p.login
        """
        
        cutoff_date = datetime.now() - timedelta(days=days)
        result = await self.db._execute_one(query, player_id, cutoff_date)
        
        if not result:
            return None
        
        return PlayerStats(
            player_id=result["player_id"],
            login=result["login"],
            battles_count=result["battles_count"],
            wins=result["wins"],
            losses=result["losses"],
            kills_monsters=result["kills_monsters"],
            kills_players=result["kills_players"],
            rank_points_avg=float(result["rank_points_avg"] or 0),
            pve_points_avg=float(result["pve_points_avg"] or 0)
        )
    
    async def get_top_players(
        self, 
        metric: str = "battles_count",
        limit: int = 10,
        days: int = 30
    ) -> List[PlayerStats]:
        """Топ игроков по метрике"""
        valid_metrics = [
            "battles_count", "wins", "kills_monsters", "kills_players",
            "rank_points_avg", "pve_points_avg"
        ]
        
        if metric not in valid_metrics:
            metric = "battles_count"
        
        query = f"""
            SELECT 
                p.id as player_id,
                p.login,
                COUNT(bp.battle_id) as battles_count,
                SUM(CASE WHEN bp.survived = true THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN bp.survived = false THEN 1 ELSE 0 END) as losses,
                SUM(bp.kills_monsters) as kills_monsters,
                SUM(bp.kills_players) as kills_players,
                AVG(bp.rank_points) as rank_points_avg,
                AVG(bp.pve_points) as pve_points_avg
            FROM players p
            JOIN battle_participants bp ON p.id = bp.player_id
            JOIN battles b ON bp.battle_id = b.id
            WHERE b.ts >= $1
            GROUP BY p.id, p.login
            HAVING COUNT(bp.battle_id) >= $2
            ORDER BY {metric} DESC
            LIMIT $3
        """
        
        cutoff_date = datetime.now() - timedelta(days=days)
        results = await self.db._execute_query(
            query, cutoff_date, self.config.min_battles_for_analysis, limit
        )
        
        return [
            PlayerStats(
                player_id=row["player_id"],
                login=row["login"],
                battles_count=row["battles_count"],
                wins=row["wins"],
                losses=row["losses"],
                kills_monsters=row["kills_monsters"],
                kills_players=row["kills_players"],
                rank_points_avg=float(row["rank_points_avg"] or 0),
                pve_points_avg=float(row["pve_points_avg"] or 0)
            )
            for row in results
        ]
    
    # ===== СТАТИСТИКА КЛАНОВ =====
    
    async def get_clan_stats(
        self, 
        clan_id: Optional[int] = None,
        name: Optional[str] = None,
        days: int = 30
    ) -> Optional[ClanStats]:
        """Получение статистики клана"""
        if not clan_id and not name:
            return None
        
        # Определяем clan_name если передано clan_id
        clan_name = name
        if not clan_name and clan_id:
            clan_name = await self._get_clan_name_by_id(clan_id)
            if not clan_name:
                return None
        
        query = """
            SELECT 
                c.clan_id as clan_id,
                c.name,
                COUNT(DISTINCT bp.player_id) as members_count,
                COUNT(bp.battle_id) as battles_count,
                SUM(CASE WHEN bp.survived = true THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN bp.survived = false THEN 1 ELSE 0 END) as losses,
                SUM(bp.rank_points) as total_rank_points,
                SUM(bp.pve_points) as total_pve_points
            FROM clans c
            JOIN battle_participants bp ON c.name = bp.clan
            JOIN battles b ON bp.battle_id = b.id
            WHERE c.name = $1
            AND b.ts >= $2
            GROUP BY c.clan_id, c.name
        """
        
        cutoff_date = datetime.now() - timedelta(days=days)
        result = await self.db._execute_one(query, clan_name, cutoff_date)
        
        if not result:
            return None
        
        return ClanStats(
            clan_id=result["clan_id"],
            name=result["name"],
            members_count=result["members_count"],
            battles_count=result["battles_count"],
            wins=result["wins"],
            losses=result["losses"],
            total_rank_points=float(result["total_rank_points"] or 0),
            total_pve_points=result["total_pve_points"]
        )
    
    # ===== СТАТИСТИКА РЕСУРСОВ =====
    
    async def get_resource_stats(
        self, 
        resource_id: Optional[int] = None,
        name: Optional[str] = None,
        days: int = 30
    ) -> Optional[ResourceStats]:
        """Получение статистики ресурса"""
        if not resource_id and not name:
            return None
        
        # Определяем resource_id если передано name
        if not resource_id and name:
            resource_id = await self._get_resource_id_by_name(name)
            if not resource_id:
                return None
        
        query = """
            SELECT 
                r.id as resource_id,
                r.name,
                SUM(bl.qty) as total_quantity,
                COUNT(DISTINCT bl.battle_id) as battles_count,
                AVG(bl.qty) as avg_per_battle
            FROM resource_names r
            JOIN battle_loot bl ON r.id = bl.resource_id
            JOIN battles b ON bl.battle_id = b.id
            WHERE r.id = $1
            AND bl.kind = 'resource'
            AND b.ts >= $2
            GROUP BY r.id, r.name
        """
        
        cutoff_date = datetime.now() - timedelta(days=days)
        result = await self.db._execute_one(query, resource_id, cutoff_date)
        
        if not result:
            return None
        
        return ResourceStats(
            resource_id=result["resource_id"],
            name=result["name"],
            total_quantity=result["total_quantity"],
            battles_count=result["battles_count"],
            avg_per_battle=float(result["avg_per_battle"] or 0)
        )
    
    async def get_resource_anomalies(self, days: int = 7) -> List[ResourceAnomaly]:
        """Поиск аномалий в ресурсах"""
        query = """
            WITH resource_stats AS (
                SELECT 
                    r.id as resource_id,
                    r.name,
                    DATE(b.ts) as battle_date,
                    SUM(bl.qty) as daily_quantity
                FROM resource_names r
                JOIN battle_loot bl ON r.id = bl.resource_id
                JOIN battles b ON b.id = bl.battle_id
                WHERE bl.kind = 'resource'
                AND b.ts >= $1
                GROUP BY r.id, r.name, DATE(b.ts)
            ),
            resource_means AS (
                SELECT 
                    resource_id,
                    AVG(daily_quantity) as mean_quantity,
                    STDDEV(daily_quantity) as std_quantity
                FROM resource_stats
                GROUP BY resource_id
            )
            SELECT 
                rs.resource_id,
                rs.name,
                rs.battle_date as date,
                rs.daily_quantity as quantity,
                CASE 
                    WHEN rm.std_quantity > 0 THEN 
                        (rs.daily_quantity - rm.mean_quantity) / rm.std_quantity
                    ELSE 0
                END as z_score
            FROM resource_stats rs
            JOIN resource_means rm ON rs.resource_id = rm.resource_id
            WHERE rm.std_quantity > 0
            ORDER BY ABS(CASE 
                    WHEN rm.std_quantity > 0 THEN 
                        (rs.daily_quantity - rm.mean_quantity) / rm.std_quantity
                    ELSE 0
                END) DESC
        """
        
        cutoff_date = date.today() - timedelta(days=days)
        results = await self.db._execute_query(query, cutoff_date)
        
        anomalies = []
        for row in results:
            z_score = float(row["z_score"])
            is_anomaly = abs(z_score) > self.config.z_score_threshold
            
            anomalies.append(ResourceAnomaly(
                resource_id=row["resource_id"],
                resource_name=row["name"],
                date=row["date"],
                quantity=row["quantity"],
                z_score=z_score,
                is_anomaly=is_anomaly,
                threshold=self.config.z_score_threshold
            ))
        
        return anomalies
    
    # ===== СТАТИСТИКА МОНСТРОВ =====
    
    async def get_monster_stats(
        self, 
        monster_id: Optional[int] = None,
        kind: Optional[str] = None,
        days: int = 30
    ) -> Optional[MonsterStats]:
        """Получение статистики монстра"""
        if not monster_id and not kind:
            return None
        
        # Определяем monster_id если передан kind
        if not monster_id and kind:
            monster_id = await self._get_monster_id_by_kind(kind)
            if not monster_id:
                return None
        
        query = """
            SELECT 
                mc.id as monster_id,
                mc.kind,
                mc.spec,
                COUNT(bm.battle_id) as battles_count,
                SUM(bm.count) as total_count,
                AVG(bm.count) as avg_per_battle
            FROM monster_catalog mc
            JOIN battle_monsters bm ON mc.id = bm.monster_id
            JOIN battles b ON bm.battle_id = b.id
            WHERE mc.id = $1
            AND b.ts >= $2
            GROUP BY mc.id, mc.kind, mc.spec
        """
        
        cutoff_date = datetime.now() - timedelta(days=days)
        result = await self.db._execute_one(query, monster_id, cutoff_date)
        
        if not result:
            return None
        
        return MonsterStats(
            monster_id=result["monster_id"],
            kind=result["kind"],
            spec=result["spec"],
            battles_count=result["battles_count"],
            total_count=result["total_count"],
            avg_per_battle=float(result["avg_per_battle"] or 0)
        )

    # ===== ДОП. АНАЛИТИКА: SURVIVAL / EFFICIENCY =====

    async def get_player_survival(self, login: str, days: int = 30) -> Dict[str, Any]:
        """Survival Rate и Clutch Rate для игрока."""
        cutoff_date = datetime.now() - timedelta(days=days)
        query = """
            SELECT
                COUNT(*)::int AS battles,
                SUM(CASE WHEN bp.survived = TRUE THEN 1 ELSE 0 END)::int AS survived_battles,
                SUM(CASE WHEN bp.survived = TRUE AND EXISTS (
                    SELECT 1 FROM battle_participants bp2
                    WHERE bp2.battle_id = bp.battle_id AND bp2.player_id <> bp.player_id AND bp2.survived = FALSE
                ) THEN 1 ELSE 0 END)::int AS clutch_battles
            FROM battle_participants bp
            JOIN players p ON p.id = bp.player_id
            JOIN battles b ON b.id = bp.battle_id
            WHERE p.login = $1 AND b.ts >= $2
        """
        row = await self.db._execute_one(query, login, cutoff_date)
        battles = (row or {}).get("battles", 0) or 0
        survived = (row or {}).get("survived_battles", 0) or 0
        clutch = (row or {}).get("clutch_battles", 0) or 0
        return {
            "login": login,
            "period_days": days,
            "battles": battles,
            "survival_rate": (survived / battles) if battles else 0.0,
            "clutch_rate": (clutch / battles) if battles else 0.0,
            "survived": survived,
            "clutch": clutch,
        }

    async def get_clan_survival(self, name: str, days: int = 30) -> Dict[str, Any]:
        """Survival/Clutch агрегировано по клану (участники, заявившие этот клан в бою)."""
        cutoff_date = datetime.now() - timedelta(days=days)
        query = """
            SELECT
                COUNT(*)::int AS battles,
                SUM(CASE WHEN bp.survived = TRUE THEN 1 ELSE 0 END)::int AS survived_battles,
                SUM(CASE WHEN bp.survived = TRUE AND EXISTS (
                    SELECT 1 FROM battle_participants bp2
                    WHERE bp2.battle_id = bp.battle_id AND bp2.player_id <> bp.player_id AND bp2.survived = FALSE
                ) THEN 1 ELSE 0 END)::int AS clutch_battles
            FROM battle_participants bp
            JOIN battles b ON b.id = bp.battle_id
            WHERE bp.clan = $1 AND b.ts >= $2
        """
        row = await self.db._execute_one(query, name, cutoff_date)
        battles = (row or {}).get("battles", 0) or 0
        survived = (row or {}).get("survived_battles", 0) or 0
        clutch = (row or {}).get("clutch_battles", 0) or 0
        return {
            "clan": name,
            "period_days": days,
            "battles": battles,
            "survival_rate": (survived / battles) if battles else 0.0,
            "clutch_rate": (clutch / battles) if battles else 0.0,
            "survived": survived,
            "clutch": clutch,
        }

    async def get_player_efficiency(self, login: str, days: int = 30, w_p: float = 1.0) -> Dict[str, Any]:
        """KPM, KPT, Weighted Kills (упрощённо: вес PvP = w_p)."""
        cutoff_date = datetime.now() - timedelta(days=days)
        # Пер-матч метрики на основе записей участника в каждом бою
        query = """
            SELECT
                COUNT(*)::int AS battles,
                AVG((bp.kills_monsters + $3 * bp.kills_players)::numeric) AS kpm_avg,
                AVG(
                    CASE WHEN NULLIF(b.turns, 0) IS NULL THEN NULL
                         ELSE (bp.kills_monsters + $3 * bp.kills_players)::numeric / NULLIF(b.turns, 0)
                    END
                ) AS kpt_avg,
                SUM((bp.kills_monsters + $3 * bp.kills_players))::numeric AS weighted_kills_sum
            FROM battle_participants bp
            JOIN players p ON p.id = bp.player_id
            JOIN battles b ON b.id = bp.battle_id
            WHERE p.login = $1 AND b.ts >= $2
        """
        row = await self.db._execute_one(query, login, cutoff_date, w_p)
        battles = int((row or {}).get("battles", 0) or 0)
        return {
            "login": login,
            "period_days": days,
            "battles": battles,
            "kpm": float(row["kpm_avg"]) if row and row["kpm_avg"] is not None else 0.0,
            "kpt": float(row["kpt_avg"]) if row and row["kpt_avg"] is not None else 0.0,
            "weighted_kills": float(row["weighted_kills_sum"]) if row and row["weighted_kills_sum"] is not None else 0.0,
            "w_p": w_p,
        }

    async def get_efficiency_top(self, limit: int = 10, days: int = 30, w_p: float = 1.0) -> List[Dict[str, Any]]:
        """Топ игроков по KPM/KPT (с фильтром минимум боёв)."""
        cutoff_date = datetime.now() - timedelta(days=days)
        query = """
            SELECT
                p.login,
                COUNT(*)::int AS battles,
                AVG((bp.kills_monsters + $2 * bp.kills_players)::numeric) AS kpm_avg,
                AVG(
                    CASE WHEN NULLIF(b.turns, 0) IS NULL THEN NULL
                         ELSE (bp.kills_monsters + $2 * bp.kills_players)::numeric / NULLIF(b.turns, 0)
                    END
                ) AS kpt_avg
            FROM battle_participants bp
            JOIN players p ON p.id = bp.player_id
            JOIN battles b ON b.id = bp.battle_id
            WHERE b.ts >= $1
            GROUP BY p.login
            HAVING COUNT(*) >= $3
            ORDER BY kpm_avg DESC NULLS LAST
            LIMIT $4
        """
        rows = await self.db._execute_query(query, cutoff_date, w_p, self.config.min_battles_for_analysis, limit)
        out = []
        for r in rows:
            out.append({
                "login": r["login"],
                "battles": int(r["battles"] or 0),
                "kpm": float(r["kpm_avg"]) if r["kpm_avg"] is not None else 0.0,
                "kpt": float(r["kpt_avg"]) if r["kpt_avg"] is not None else 0.0,
                "w_p": w_p,
            })
        return out
    
    # ===== АНТИБОТ АНАЛИЗ =====
    
    async def detect_bot_suspicion(
        self, 
        player_id: Optional[int] = None,
        login: Optional[str] = None,
        days: int = 7
    ) -> Optional[BotSuspicion]:
        """Обнаружение подозрения на бота"""
        if not player_id and not login:
            return None
        
        # Определяем player_id если передан login
        if not player_id and login:
            player_id = await self._get_player_id_by_login(login)
            if not player_id:
                return None
        
        # Получаем статистику игрока
        player_stats = await self.get_player_stats(player_id=player_id, days=days)
        if not player_stats or player_stats.battles_count < self.config.min_battles_for_analysis:
            return None
        
        # Гибкий скоринг: нормализованные вклады метрик и взвешенная сумма
        reasons: List[str] = []
        cfg = self.config
        battles = max(0, player_stats.battles_count)
        sr = (player_stats.wins / battles) if battles else 0.0
        kpm_pvp = (player_stats.kills_players / battles) if battles else 0.0
        kpm_pve = (player_stats.kills_monsters / battles) if battles else 0.0

        # 1) Активность
        if battles <= cfg.min_battles_for_analysis:
            act_score = 0.0
        elif battles >= cfg.activity_high:
            act_score = 1.0
        else:
            act_score = (battles - cfg.min_battles_for_analysis) / (cfg.activity_high - cfg.min_battles_for_analysis)
        if act_score > 0.7:
            reasons.append(f"Высокая активность ({battles} боёв)")

        # 2) SR
        if sr <= cfg.sr_mid:
            sr_score = 0.0
        elif sr >= cfg.sr_high:
            sr_score = 1.0
        else:
            sr_score = (sr - cfg.sr_mid) / (cfg.sr_high - cfg.sr_mid)
        if sr_score > 0.7:
            reasons.append(f"Высокий SR ({sr:.3f})")

        # 3) PvP KPM
        kpm = kpm_pvp
        if kpm <= cfg.kpm_mid:
            kpm_score = 0.0
        elif kpm >= cfg.kpm_high:
            kpm_score = 1.0
        else:
            kpm_score = (kpm - cfg.kpm_mid) / (cfg.kpm_high - cfg.kpm_mid)
        if kpm_score > 0.7:
            reasons.append(f"Высокий KPM ({kpm:.2f})")

        # 3b) PvE‑фокус (штраф): высокий PvE KPM при низком PvP KPM
        if kpm_pve <= cfg.pve_kpm_mid:
            pve_focus = 0.0
        elif kpm_pve >= cfg.pve_kpm_high:
            pve_focus = 1.0
        else:
            pve_focus = (kpm_pve - cfg.pve_kpm_mid) / (cfg.pve_kpm_high - cfg.pve_kpm_mid)
        # Усиливаем штраф при очень низком PvP
        low_pvp_factor = 1.0 if kpm_pvp <= cfg.pvp_kpm_low else 0.0
        pve_penalty = pve_focus * low_pvp_factor
        if pve_penalty >= 0.7:
            reasons.append("PvE‑фокус (много монстров, мало PvP)")

        # 4) Временные паттерны
        time_patterns = await self._analyze_time_patterns(player_id, days)

        # 4.1) Регулярность интервалов (std/mean)
        intervals = time_patterns.get("intervals", [])
        if len(intervals) > 2:
            mean_interval = sum(intervals) / len(intervals)
            variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
            std_dev = variance ** 0.5
            ratio = (std_dev / mean_interval) if mean_interval > 0 else 0.0
            if ratio <= 0:
                reg_score = 1.0
            else:
                reg_score = max(0.0, min(1.0, (cfg.intervals_std_ratio_thresh / ratio)))
            if reg_score > 0.7:
            reasons.append("Слишком регулярные интервалы между боями")
        else:
            reg_score = 0.0

        # 4.2) Максимальный разрыв (чем меньше, тем подозрительнее)
        max_gap_hours = float(time_patterns.get("max_gap_hours", 0.0) or 0.0)
        if max_gap_hours <= 0:
            gap_score = 0.0
        elif max_gap_hours >= cfg.max_gap_hours_low:
            gap_score = 0.0
        else:
            gap_score = max(0.0, min(1.0, (cfg.max_gap_hours_low - max_gap_hours) / cfg.max_gap_hours_low))
        if gap_score > 0.7 and (time_patterns.get("intervals_count", 0) or 0) >= 5:
            reasons.append(f"Почти нет длинных перерывов (max_gap={max_gap_hours:.1f}h)")

        # 4.3) Регулярность часов
        hour_spread = float(time_patterns.get("active_hour_spread", 24.0) or 24.0)
        active_ratio = float(time_patterns.get("active_hours_ratio", 0.0) or 0.0)
        if hour_spread >= 24.0:
            spread_score = 0.0
        else:
            spread_score = max(0.0, min(1.0, (cfg.hour_spread_narrow - hour_spread) / cfg.hour_spread_narrow))
        if active_ratio <= 0:
            ratio_score = 0.0
        else:
            base = cfg.active_hours_ratio_high
            ratio_score = max(0.0, min(1.0, (active_ratio - base) / (1.0 - base))) if active_ratio > base else 0.0
        hourly_score = max(spread_score, ratio_score)
        if hourly_score > 0.7:
            if spread_score >= ratio_score:
                reasons.append(f"Регулярность времени суток (узкое окно ~{hour_spread:.1f}ч)")
            else:
                reasons.append("Регулярность времени суток (круглосуточно)")

        # 4.4) Сверхкороткие интервалы между боями (≤ threshold)
        short_ratio = float(time_patterns.get("short_ratio", 0.0) or 0.0)
        short_streak_max = int(time_patterns.get("short_streak_max", 0) or 0)
        # Нормализация: чем больше доля/серия — тем выше вклад
        sr_target = cfg.short_interval_ratio_high
        sr_score = max(0.0, min(1.0, short_ratio / sr_target)) if sr_target > 0 else 0.0
        ss_target = cfg.short_interval_streak_high
        ss_score = max(0.0, min(1.0, short_streak_max / ss_target)) if ss_target > 0 else 0.0
        short_score = max(sr_score, ss_score)
        if short_score > 0.7:
            reasons.append(
                f"Сверхкороткие интервалы (доля={short_ratio:.2f}, серия={short_streak_max})"
            )
        
        # 4.5) НОВОЕ: Ультра-короткие интервалы (< 0.5 сек - ГЛАВНЫЙ ПРИЗНАК БОТА!)
        ultra_short_ratio = float(time_patterns.get("ultra_short_ratio", 0.0) or 0.0)
        ultra_short_count = int(time_patterns.get("ultra_short_count", 0) or 0)
        ultra_target = cfg.ultra_short_ratio_high
        ultra_score = max(0.0, min(1.0, ultra_short_ratio / ultra_target)) if ultra_target > 0 else 0.0
        if ultra_score > 0.3:  # уже 30% от порога (10% интервалов < 0.5 сек)
            reasons.append(
                f"🤖 Ботовые интервалы < 0.5 сек ({ultra_short_ratio:.1%}, {ultra_short_count} шт)"
            )
        
        # 4.6) НОВОЕ: Марафон-сессии (3+ часа без перерывов - ПРИЗНАК БОТА!)
        marathon_count = int(time_patterns.get("marathon_count", 0) or 0)
        longest_marathon = float(time_patterns.get("longest_marathon_hours", 0.0) or 0.0)
        total_marathon_battles = int(time_patterns.get("total_marathon_battles", 0) or 0)
        
        # Score зависит от количества и длины марафонов
        if marathon_count > 0:
            marathon_score = min(1.0, marathon_count / 3.0)  # 3+ марафона = max
            if longest_marathon > 5.0:  # 5+ часов подряд
                marathon_score = min(1.0, marathon_score + 0.3)
        else:
            marathon_score = 0.0
        
        if marathon_score > 0.5:
            reasons.append(
                f"🤖 Марафон-сессии без перерывов ({marathon_count} шт, макс {longest_marathon:.1f}ч, {total_marathon_battles} боев)"
            )

        # 4.5) Средняя пауза в сессии: чем меньше, тем подозрительнее
        # Для этого нам нужен avg_gap_in_session_sec — вычислим по тем же данным, что и _analyze_time_patterns
        # Быстрая оценка: посчитаем интервалы подряд и возьмем только те, что <= 30 мин (сессионные)
        in_sess = [x for x in intervals if x <= 30*60]
        avg_gap_in_session = (sum(in_sess)/len(in_sess)) if in_sess else 0.0
        # Нормализация: 0 сек => 1.0; 120 сек => ~0.5; ≥600 сек => 0
        if avg_gap_in_session <= 0:
            in_sess_score = 0.0  # нет данных — не усиливаем
        else:
            # линейная шкала по две точки: 0..600 сек
            in_sess_score = max(0.0, min(1.0, (600.0 - avg_gap_in_session)/600.0))

        # Итог: взвешенная сумма (с новыми весами!)
        suspicion_score = (
            cfg.w_activity * act_score +
            cfg.w_sr * sr_score +
            cfg.w_kpm * kpm_score +
            cfg.w_intervals_regular * reg_score +
            cfg.w_max_gap * gap_score +
            cfg.w_hour_spread_or_ratio * hourly_score +
            cfg.w_short_intervals * short_score +
            cfg.w_ultra_short_intervals * ultra_score +      # НОВОЕ: главный признак!
            cfg.w_marathon_sessions * marathon_score +       # НОВОЕ: марафоны!
            cfg.w_in_session_gap * in_sess_score
        )
        
        # НОВАЯ ЛОГИКА: Различение PvE игроков и ботов
        is_pve_focused = (kpm_pve > 10.0 and kpm_pvp < 0.5)
        has_natural_breaks = (max_gap_hours > 0.5)  # есть перерывы > 30 минут
        has_ultra_short = (ultra_short_ratio > 0.1)  # 10%+ интервалов < 0.5 сек
        has_marathons = (marathon_count > 0)         # есть сессии 3+ часа
        
        if is_pve_focused:
            if has_natural_breaks and not has_ultra_short and not has_marathons:
                # ✅ Обычный PvE игрок - СНИЖАЕМ подозрительность
                suspicion_score -= 0.3
                reasons.append("✅ PvE игрок с естественными перерывами (не бот)")
            elif (has_marathons or has_ultra_short) and ultra_short_ratio > 0.2:
                # 🤖 PvE БОТ - ПОВЫШАЕМ подозрительность
                suspicion_score += 0.4
                reasons.append("🤖 PvE бот: марафоны + микро-интервалы")
        
        # Минимальный штраф за PvE‑фокус (сильно снижен)
        suspicion_score -= cfg.w_pve_penalty * pve_penalty

        suspicion_score = max(0.0, min(1.0, suspicion_score))
        
        is_bot = suspicion_score >= self.config.bot_suspicion_threshold
        confidence = suspicion_score
        
        return BotSuspicion(
            player_id=player_id,
            login=player_stats.login,
            date=date.today(),
            suspicion_score=suspicion_score,
            reasons=reasons,
            is_bot=is_bot,
            confidence=confidence
        )
    
    async def get_antibot_candidates(self, limit: int = 50, days: int = 7) -> List[Dict[str, Any]]:
        """Подозрительные на бота игроки с Voting Ensemble (K-means + Isolation Forest)."""
        # Берём топ по активностям как базу кандидатов (увеличен для покрытия)
        top = await self.get_top_players(metric="battles_count", limit=limit * 4, days=days)
        out: List[Dict[str, Any]] = []
        ml_detected_bots: List[Dict[str, Any]] = []  # НОВОЕ: боты обнаруженные только ML
        
        # Пытаемся загрузить Voting Ensemble детектор
        use_voting = False
        bot_detector = None
        try:
            from app.ml.bot_detector import BotDetector, SKLEARN_AVAILABLE
            if SKLEARN_AVAILABLE:
                bot_detector = BotDetector()
                use_voting = bot_detector.load_model()
        except Exception as e:
            print(f"BotDetector не загружен: {e}")
            use_voting = False
        
        # Если Voting недоступен, используем старую логику с K-means
        use_kmeans_fallback = False
        if not use_voting:
            try:
                from app.ml.playstyle_classifier import PlaystyleClassifier, SKLEARN_AVAILABLE
                if SKLEARN_AVAILABLE:
                    classifier = PlaystyleClassifier()
                    use_kmeans_fallback = classifier.load_model()
            except:
                pass
        
        for s in top:
            # ИЗМЕНЕНО: Сначала ML проверка, потом rule-based
            base_score = 0.0
            final_score = 0.0
            boost = 0.0
            playstyle_name = None
            bot_score = 0.0
            method = "rule_based"
            reasons = []
            
            # VOTING ENSEMBLE (ПРИОРИТЕТ #1)
            voting_detected = False
            if use_voting and bot_detector:
                try:
                    voting_result = await bot_detector.detect(s.player_id, self.db, days=days)
                    
                    if voting_result and 'is_bot' in voting_result:
                        playstyle_name = voting_result.get('playstyle')
                        reasons = voting_result.get('reasons', [])
                        
                        # Если Voting Ensemble уверен - это БОТ независимо от rule-based!
                        if voting_result.get('is_bot'):
                            confidence = voting_result.get('confidence', 0)
                            method = voting_result.get('method', 'voting')
                            bot_score = confidence
                            voting_detected = True
                            
                            # Высокий базовый score для ML-ботов
                            base_score = 0.7  # минимум для ML-ботов
                            
                            if confidence >= 0.95:  # оба метода согласны
                                boost = 0.30  # +30%
                                base_score = 0.7
                            elif confidence >= 0.75:  # K-means уверен
                                boost = 0.25  # +25%
                                base_score = 0.6
                            elif confidence >= 0.70:  # IF уверен
                                boost = 0.20  # +20%
                                base_score = 0.5
                            
                            final_score = min(1.0, base_score + boost)
                except Exception as e:
                    print(f"Voting Ensemble error for {s.player_id}: {e}")
                    pass
            
            # RULE-BASED (если ML не обнаружил или для уточнения)
            if not voting_detected:
                suspicion = await self.detect_bot_suspicion(player_id=s.player_id, days=days)
                if not suspicion:
                    continue  # пропускаем только если и ML и rule-based пропустили
                
                base_score = suspicion.suspicion_score
                final_score = base_score
                reasons = suspicion.reasons
            
            # FALLBACK: K-means если Voting недоступен
            elif use_kmeans_fallback:
                try:
                    playstyle_data = await classifier.classify_player(s.player_id, self.db, days=days)
                    if playstyle_data:
                        playstyle_name = playstyle_data.get('display_name')
                        bd = playstyle_data.get('bot_detection', {})
                        bot_score = bd.get('bot_score', 0)
                        
                        if bot_score > 0.75:
                            boost = 0.15
                        elif bot_score > 0.5:
                            boost = 0.10
                        
                        if playstyle_data.get('playstyle') == 'bot_farmer':
                            boost += 0.20
                        elif playstyle_data.get('playstyle') == 'pve_grinder' and bot_score > 0.5:
                            boost += 0.15
                        
                        final_score = min(1.0, base_score + boost)
                        method = "kmeans_only"
                except:
                    pass
            
            # Если ML обнаружил - не нужен suspicion
            if voting_detected:
                is_bot_final = True
                login = s.login
            else:
                is_bot_final = (suspicion.is_bot if suspicion else False) or final_score >= self.config.bot_suspicion_threshold
                login = suspicion.login if suspicion else s.login
            
            result_item = {
                "login": login,
                "battles": s.battles_count,
                "suspicion_score": round(final_score, 3),
                "base_score": round(base_score, 3),
                "is_bot": is_bot_final,
                "reasons": reasons,
                "confidence": round(final_score, 3),
                "detection_method": method,
            }
            
            # Добавляем ML данные если есть
            if playstyle_name:
                result_item["playstyle"] = playstyle_name
            if boost > 0:
                result_item["ml_boost"] = round(boost, 3)
            if bot_score > 0:
                result_item["bot_score"] = round(bot_score, 3)
            
            out.append(result_item)
        
        # УЛУЧШЕНИЕ: Добавляем ботов которых нашёл только ML (даже с низким base_score)
        # Проверяем всех остальных активных игроков через ML
        if use_voting and bot_detector and len(out) < limit:
            # Берём ещё игроков для ML проверки
            additional_top = await self.get_top_players(metric="battles_count", limit=limit * 6, days=days)
            checked_logins = {x['login'] for x in out}
            
            for s in additional_top:
                if s.login in checked_logins:
                    continue
                
                try:
                    voting_result = await bot_detector.detect(s.player_id, self.db, days=days)
                    
                    if voting_result and voting_result.get('is_bot') and voting_result.get('confidence', 0) >= 0.70:
                        # ML уверен что это бот - добавляем независимо от rule-based score
                        suspicion = await self.detect_bot_suspicion(player_id=s.player_id, days=days)
                        base_score = suspicion.suspicion_score if suspicion else 0.5
                        confidence = voting_result.get('confidence', 0)
                        
                        # Сильный boost для ML-обнаруженных ботов
                        if confidence >= 0.95:
                            boost = 0.40
                        elif confidence >= 0.75:
                            boost = 0.30
                        else:
                            boost = 0.20
                        
                        final_score = min(1.0, base_score + boost)
                        
                        ml_detected_bots.append({
                            "login": s.login,
                            "battles": s.battles_count,
                            "suspicion_score": round(final_score, 3),
                            "base_score": round(base_score, 3),
                            "is_bot": True,
                            "reasons": voting_result.get('reasons', []),
                            "confidence": round(confidence, 3),
                            "detection_method": voting_result.get('method'),
                            "playstyle": voting_result.get('playstyle'),
                            "ml_boost": round(boost, 3),
                            "bot_score": round(confidence, 3),
                            "ml_only": True,  # пометка что найден только ML
                        })
                        
                        if len(ml_detected_bots) >= limit // 2:  # не более половины limit
                            break
                except:
                    pass
        
        # Объединяем списки
        all_candidates = out + ml_detected_bots
        
        # Сортируем по убыванию подозрительности и отдаем top-N
        all_candidates.sort(key=lambda x: x.get("suspicion_score", 0), reverse=True)
        return all_candidates[:limit]

    async def get_antiboost_pairs(self, days: int = 14, min_pairs: int = 3) -> List[Dict[str, Any]]:
        """Поиск пар с взаимными убийствами игроков (килл-трейдинг).
        Использует JSONB поле kills->players как {victim_login: count}.
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        query = """
            WITH edges AS (
                SELECT p.login AS killer,
                       key AS victim,
                       COALESCE((bp.kills -> 'players' ->> key)::int, 0) AS kills
                FROM battle_participants bp
                JOIN players p ON p.id = bp.player_id
                JOIN battles b ON b.id = bp.battle_id
                CROSS JOIN LATERAL jsonb_object_keys(COALESCE(bp.kills -> 'players', '{}'::jsonb)) key
                WHERE b.ts >= $1 
                  AND bp.kills IS NOT NULL 
                  AND jsonb_typeof(bp.kills) = 'object'
                  AND bp.kills ? 'players'
                  AND jsonb_typeof(bp.kills -> 'players') = 'object'
            ),
            pairs AS (
                SELECT e1.killer, e1.victim,
                       SUM(e1.kills) AS k1,
                       COALESCE((SELECT SUM(e2.kills) FROM edges e2 WHERE e2.killer = e1.victim AND e2.victim = e1.killer), 0) AS k2
                FROM edges e1
                GROUP BY e1.killer, e1.victim
            )
            SELECT killer, victim, k1, k2, (k1 + k2) AS total
            FROM pairs
            WHERE k1 > 0 AND k2 > 0
            ORDER BY total DESC
            LIMIT 200
        """
        rows = await self.db._execute_query(query, cutoff_date)
        out = []
        for r in rows:
            if (r["k1"] or 0) >= min_pairs and (r["k2"] or 0) >= min_pairs:
                out.append({
                    "killer": r["killer"],
                    "victim": r["victim"],
                    "kills_ab": int(r["k1"] or 0),
                    "kills_ba": int(r["k2"] or 0),
                    "total": int(r["total"] or 0),
                })
        return out
    
    async def get_antibot_player_detail(self, login: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """Детальный разбор антибот по конкретному игроку: score, причины, компоненты и временные метрики."""
        player_id = await self._get_player_id_by_login(login)
        if not player_id:
            return None

        susp = await self.detect_bot_suspicion(player_id=player_id, days=days)
        if not susp:
            return None

        stats = await self.get_player_stats(player_id=player_id, days=days)
        if not stats:
            return None

        battles = max(0, stats.battles_count)
        sr = (stats.wins / battles) if battles else 0.0
        kpm_pvp = (stats.kills_players / battles) if battles else 0.0
        kpm_pve = (stats.kills_monsters / battles) if battles else 0.0
        tpat = await self._analyze_time_patterns(player_id, days)

        # Сессии и дополнительные метрики: строим по хронологии боёв за период
        cutoff_date = datetime.now() - timedelta(days=days)
        rows = await self.db._execute_query(
            """
            SELECT b.ts, COALESCE(b.turns, 0) AS turns, b.loc_x, b.loc_y
            FROM battles b
            JOIN battle_participants bp ON bp.battle_id = b.id
            WHERE bp.player_id = $1 AND b.ts >= $2
            ORDER BY b.ts ASC
            """,
            player_id, cutoff_date
        )

        timestamps: List[datetime] = [r["ts"] for r in rows]
        turns_list: List[int] = [int(r["turns"] or 0) for r in rows]
        locations: List[Tuple[Optional[int], Optional[int]]] = [(r.get("loc_x"), r.get("loc_y")) for r in rows]

        # Разбиение на сессии по порогу 30 минут
        session_gap_seconds = 30 * 60
        sessions: List[List[int]] = []  # индексы боёв в каждой сессии
        if timestamps:
            current: List[int] = [0]
            for i in range(1, len(timestamps)):
                gap = (timestamps[i] - timestamps[i-1]).total_seconds()
                if gap > session_gap_seconds:
                    sessions.append(current)
                    current = [i]
                else:
                    current.append(i)
            if current:
                sessions.append(current)

        # Средние интервалы внутри сессий
        in_session_gaps: List[float] = []
        for sess in sessions:
            for a, b in zip(sess, sess[1:]):
                in_session_gaps.append((timestamps[b] - timestamps[a]).total_seconds())

        avg_gap_in_session = (sum(in_session_gaps) / len(in_session_gaps)) if in_session_gaps else 0.0
        avg_turns = (sum(turns_list) / len(turns_list)) if turns_list else 0.0
        # Количество боёв по сессиям
        sessions_battles: List[int] = [len(s) for s in sessions]

        # Распределение по часам и дням недели
        hour_hist: Dict[int, int] = {}
        weekday_hist: Dict[int, int] = {}
        for ts in timestamps:
            hour_hist[ts.hour] = hour_hist.get(ts.hour, 0) + 1
            weekday_hist[ts.weekday()] = weekday_hist.get(ts.weekday(), 0) + 1  # 0=Mon..6=Sun

        # Топ локаций (loc_x, loc_y)
        loc_hist: Dict[str, int] = {}
        for lx, ly in locations:
            if lx is None or ly is None:
                continue
            key = f"{lx},{ly}"
            loc_hist[key] = loc_hist.get(key, 0) + 1
        top_locations = sorted(({"loc": k, "count": v} for k, v in loc_hist.items()), key=lambda x: x["count"], reverse=True)[:10]

        # НОВОЕ: Проверим ML детектор (Voting Ensemble)
        ml_result = None
        ml_is_bot = False
        ml_confidence = 0.0
        ml_method = "none"
        
        try:
            from app.ml.bot_detector import BotDetector, SKLEARN_AVAILABLE
            if SKLEARN_AVAILABLE:
                bot_detector = BotDetector()
                if bot_detector.load_model():
                    ml_result = await bot_detector.detect(player_id, self.db, days=days)
                    if ml_result and 'is_bot' in ml_result:
                        ml_is_bot = ml_result.get('is_bot', False)
                        ml_confidence = ml_result.get('confidence', 0.0)
                        ml_method = ml_result.get('method', 'none')
        except:
            pass
        
        # Используем ML результат если доступен (конвертируем numpy типы в Python!)
        final_is_bot = bool(ml_is_bot) if ml_result else susp.is_bot
        final_score = float(ml_confidence) if ml_result else susp.suspicion_score
        final_reasons = ml_result.get('reasons', []) if ml_result else susp.reasons
        
        # Конвертируем ml_result для JSON (numpy → Python types)
        if ml_result:
            ml_result = {
                'is_bot': bool(ml_result.get('is_bot', False)),
                'confidence': float(ml_result.get('confidence', 0.0)),
                'method': str(ml_result.get('method', 'none')),
                'kmeans_bot': bool(ml_result.get('kmeans_bot', False)),
                'if_anomaly': bool(ml_result.get('if_anomaly', False)),
                'if_anomaly_score': float(ml_result.get('if_anomaly_score', 0.0)),
                'playstyle': str(ml_result.get('playstyle', 'Unknown')),
                'reasons': list(ml_result.get('reasons', []))
            }
        
        # Тепловая карта активности (24x7)
        heatmap = []
        for hour in range(24):
            for day in range(7):
                battles_count = 0
                # Подсчитаем бои для этой комбинации hour+day
                for ts in timestamps:
                    if ts.hour == hour and ts.weekday() == day:
                        battles_count += 1
                if battles_count > 0:
                    heatmap.append({
                        "hour": hour,
                        "weekday": day,  # 0=Mon, 6=Sun
                        "battles": battles_count
                    })
        
        # Вернём ключевые компоненты и конфиг (порог/веса)
        return {
            "login": login,
            "period_days": days,
            "battles": battles,
            "score": final_score,
            "is_bot": final_is_bot,
            "confidence": final_score,
            "reasons": final_reasons,
            "detection_method": ml_method if ml_result else "rule_based",
            "metrics": {
                "sr": sr,
                "kpm_pvp": kpm_pvp,
                "kpm_pve": kpm_pve,
                "max_gap_hours": float(tpat.get("max_gap_hours", 0.0) or 0.0),
                "active_hour_spread": float(tpat.get("active_hour_spread", 0.0) or 0.0),
                "active_hours_ratio": float(tpat.get("active_hours_ratio", 0.0) or 0.0),
                "short_ratio": float(tpat.get("short_ratio", 0.0) or 0.0),
                "short_streak_max": int(tpat.get("short_streak_max", 0) or 0),
                # НОВЫЕ МЕТРИКИ:
                "ultra_short_ratio": float(tpat.get("ultra_short_ratio", 0.0) or 0.0),
                "ultra_short_count": int(tpat.get("ultra_short_count", 0) or 0),
                "marathon_count": int(tpat.get("marathon_count", 0) or 0),
                "longest_marathon_hours": float(tpat.get("longest_marathon_hours", 0.0) or 0.0),
                "total_marathon_battles": int(tpat.get("total_marathon_battles", 0) or 0),
                # Сессии:
                "avg_gap_in_session_sec": float(avg_gap_in_session),
                "avg_turns": float(avg_turns),
                "sessions_count": len(sessions),
                "avg_session_length_battles": (sum(len(s) for s in sessions) / len(sessions)) if sessions else 0.0,
                "sessions_battles": sessions_battles,
                # Распределения (для графиков):
                "hour_hist": hour_hist,
                "weekday_hist": weekday_hist,
                "heatmap": heatmap,  # НОВОЕ: Тепловая карта 24x7
                "top_locations": top_locations,
            },
            "ml_detection": ml_result if ml_result else None,  # НОВОЕ: Данные ML детектора
            "config": {
                "bot_threshold": self.config.bot_suspicion_threshold,
                "weights": {
                    "activity": self.config.w_activity,
                    "sr": self.config.w_sr,
                    "kpm": self.config.w_kpm,
                    "intervals_regular": self.config.w_intervals_regular,
                    "max_gap": self.config.w_max_gap,
                    "hours": self.config.w_hour_spread_or_ratio,
                    "short_intervals": self.config.w_short_intervals,
                    "ultra_short_intervals": self.config.w_ultra_short_intervals,  # НОВОЕ
                    "marathon_sessions": self.config.w_marathon_sessions,  # НОВОЕ
                    "pve_penalty": self.config.w_pve_penalty,
                }
            }
        }
    
    async def _analyze_time_patterns(self, player_id: int, days: int) -> Dict[str, Any]:
        """Анализ временных паттернов игрока.
        Возвращает:
          - too_regular: bool — низкая дисперсия интервалов между боями
          - intervals: List[float] — интервалы в секундах
          - max_gap_hours: float — максимальная пауза между боями в часах
          - intervals_count: int — число интервалов
          - active_hour_spread: float — ширина минимального окна часов, покрывающего 80% боёв
          - active_hours_ratio: float — доля активных часов (уникальные часы / 24)
          - short_ratio: float — доля коротких интервалов (≤ threshold)
          - short_streak_max: int — максимальная длина серии подряд коротких интервалов
          - ultra_short_ratio: float — НОВОЕ: доля ультра-коротких интервалов (< 0.5 сек) - ГЛАВНЫЙ ПРИЗНАК БОТА!
          - ultra_short_count: int — НОВОЕ: количество ультра-коротких интервалов
          - marathon_count: int — НОВОЕ: количество марафон-сессий (3+ часа без перерывов > 5 мин)
          - longest_marathon_hours: float — НОВОЕ: самая длинная марафон-сессия в часах
          - total_marathon_battles: int — НОВОЕ: всего боев в марафон-сессиях
        """
        query = """
            SELECT b.ts
            FROM battles b
            JOIN battle_participants bp ON b.id = bp.battle_id
            WHERE bp.player_id = $1
            AND b.ts >= $2
            ORDER BY b.ts
        """
        
        cutoff_date = datetime.now() - timedelta(days=days)
        results = await self.db._execute_query(query, player_id, cutoff_date)
        
        if len(results) < 3:
            # Соберём хотя бы базовую почасовую активность
            hours = [row["ts"].hour for row in results] if results else []
            unique_hours = set(hours)
            return {
                "too_regular": False,
                "intervals": [],
                "max_gap_hours": 0.0,
                "intervals_count": 0,
                "active_hour_spread": 24.0,
                "active_hours_ratio": (len(unique_hours) / 24.0) if unique_hours else 0.0,
                "short_ratio": 0.0,
                "short_streak_max": 0,
                # НОВЫЕ МЕТРИКИ:
                "ultra_short_ratio": 0.0,
                "ultra_short_count": 0,
                "marathon_count": 0,
                "longest_marathon_hours": 0.0,
                "total_marathon_battles": 0,
            }
        
        # Вычисляем интервалы между боями
        timestamps = [row["ts"] for row in results]
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        # Проверяем на слишком регулярные интервалы
        if len(intervals) > 2:
            mean_interval = sum(intervals) / len(intervals)
            variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
            std_dev = variance ** 0.5
            
            # Если стандартное отклонение меньше 10% от среднего, считаем слишком регулярным
            too_regular = std_dev < mean_interval * 0.1
        else:
            too_regular = False
        # Максимальная пауза в часах
        max_gap_hours = (max(intervals) / 3600.0) if intervals else 0.0
        
        # Короткие интервалы
        thr = self.config.short_interval_sec
        short_flags = [1 if x <= thr else 0 for x in intervals]
        short_ratio = (sum(short_flags) / len(intervals)) if intervals else 0.0
        # Максимальная серия коротких интервалов подряд
        streak = 0
        short_streak_max = 0
        for f in short_flags:
            if f:
                streak += 1
                if streak > short_streak_max:
                    short_streak_max = streak
            else:
                streak = 0
        
        # НОВОЕ: Ультра-короткие интервалы (< 0.5 сек - только боты!)
        ultra_thr = self.config.ultra_short_interval_sec
        ultra_short_count = sum(1 for x in intervals if x <= ultra_thr)
        ultra_short_ratio = (ultra_short_count / len(intervals)) if intervals else 0.0
        
        # НОВОЕ: Марафон-сессии (3+ часа без перерывов > 5 минут)
        marathon_sessions = []
        current_session_duration = 0
        current_session_battles = 0
        natural_break_sec = self.config.natural_break_minutes * 60
        marathon_threshold_sec = self.config.marathon_session_hours * 3600
        
        for interval in intervals:
            if interval <= natural_break_sec:  # продолжение сессии
                current_session_duration += interval
                current_session_battles += 1
            else:  # естественный перерыв
                if current_session_duration >= marathon_threshold_sec:
                    marathon_sessions.append({
                        'duration_hours': current_session_duration / 3600,
                        'battles': current_session_battles
                    })
                current_session_duration = 0
                current_session_battles = 0
        
        # Финальная сессия
        if current_session_duration >= marathon_threshold_sec:
            marathon_sessions.append({
                'duration_hours': current_session_duration / 3600,
                'battles': current_session_battles
            })
        
        marathon_count = len(marathon_sessions)
        longest_marathon_hours = max([s['duration_hours'] for s in marathon_sessions]) if marathon_sessions else 0.0
        total_marathon_battles = sum([s['battles'] for s in marathon_sessions]) if marathon_sessions else 0
        # Почасовая активность
        hours = [ts.hour for ts in timestamps]
        unique_hours = set(hours)
        active_hours_ratio = len(unique_hours) / 24.0
        # Минимальное окно часов, покрывающее 80% боёв (через скользящее окно по кругу 24ч)
        from collections import Counter
        cnt = Counter(hours)
        # Развернём по кругу для цикличности
        hour_list = list(range(24))
        freq = [cnt.get(h, 0) for h in hour_list]
        total = sum(freq)
        target = total * 0.8
        best_span = 24
        if total > 0:
            # Дублируем массив для циклического окна
            freq2 = freq + freq
            for start in range(24):
                s = 0
                span = 0
                for end in range(start, start + 24):
                    s += freq2[end]
                    span += 1
                    if s >= target:
                        if span < best_span:
                            best_span = span
                        break
        active_hour_spread = float(best_span)
        
        return {
            "too_regular": too_regular,
            "intervals": intervals,
            "max_gap_hours": max_gap_hours,
            "intervals_count": len(intervals),
            "active_hour_spread": active_hour_spread,
            "active_hours_ratio": active_hours_ratio,
            "short_ratio": short_ratio,
            "short_streak_max": short_streak_max,
            # НОВЫЕ МЕТРИКИ:
            "ultra_short_ratio": ultra_short_ratio,
            "ultra_short_count": ultra_short_count,
            "marathon_count": marathon_count,
            "longest_marathon_hours": longest_marathon_hours,
            "total_marathon_battles": total_marathon_battles,
        }

    def _estimate_sessions_len(self, player_id: int, days: int) -> List[int]:
        """Быстрая оценка длин сессий на основе уже доступных данных времени.
        Примечание: для точности лучше вынести расчёт в _analyze_time_patterns и кешировать,
        здесь делаем упрощённый повтор запроса синхронно через событийный цикл.
        """
        import asyncio as _aio
        async def _calc(db: BattleDatabase, pid: int, d: int) -> List[int]:
            cutoff_date = datetime.now() - timedelta(days=d)
            rows = await db._execute_query(
                """
                SELECT b.ts
                FROM battles b
                JOIN battle_participants bp ON b.id = bp.battle_id
                WHERE bp.player_id = $1 AND b.ts >= $2
                ORDER BY b.ts ASC
                """,
                pid, cutoff_date
            )
            ts = [r["ts"] for r in rows]
            if not ts:
                return []
            session_gap = 30*60
            sessions: List[List[int]] = [[0]]
            for i in range(1, len(ts)):
                gap = (ts[i] - ts[i-1]).total_seconds()
                if gap > session_gap:
                    sessions.append([i])
                else:
                    sessions[-1].append(i)
            return [len(s) for s in sessions]
        # создаём временный db, чтобы не ломать текущий self.db контекст
        try:
            db = self.db
            # используем уже открытое соединение
            return _aio.get_event_loop().run_until_complete(_calc(db, player_id, days))
        except Exception:
            return []
    
    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====
    
    async def _get_player_id_by_login(self, login: str) -> Optional[int]:
        """Получение ID игрока по логину"""
        query = "SELECT id FROM players WHERE login = $1"
        result = await self.db._execute_one(query, login)
        return result["id"] if result else None
    
    async def _get_playstyle(self, player_id: int, days: int = 90) -> Optional[Dict[str, Any]]:
        """Получает стиль игры из K-means (если модель обучена)"""
        try:
            from app.ml.playstyle_classifier import PlaystyleClassifier, SKLEARN_AVAILABLE
            
            if not SKLEARN_AVAILABLE:
                return None
            
            classifier = PlaystyleClassifier()
            if not classifier.load_model():
                return None
            
            return await classifier.classify_player(player_id, self.db, days=days)
        except Exception:
            return None
    
    async def _get_clan_id_by_name(self, name: str) -> Optional[int]:
        """Получение ID клана по названию"""
        query = "SELECT id FROM clans WHERE name = $1"
        result = await self.db._execute_one(query, name)
        return result["id"] if result else None
    
    async def _get_clan_name_by_id(self, clan_id: int) -> Optional[str]:
        """Получение имени клана по ID"""
        query = "SELECT name FROM clans WHERE id = $1"
        result = await self.db._execute_one(query, clan_id)
        return result["name"] if result else None
    
    async def _get_resource_id_by_name(self, name: str) -> Optional[int]:
        """Получение ID ресурса по названию"""
        query = "SELECT id FROM resource_names WHERE name = $1"
        result = await self.db._execute_one(query, name)
        return result["id"] if result else None
    
    async def _get_monster_id_by_kind(self, kind: str) -> Optional[int]:
        """Получение ID монстра по виду"""
        query = "SELECT id FROM monster_catalog WHERE kind = $1 LIMIT 1"
        result = await self.db._execute_one(query, kind)
        return result["id"] if result else None
    
    # ===== ОБЩАЯ СТАТИСТИКА =====
    
    async def get_general_stats(self, days: int = 30) -> Dict[str, Any]:
        """Общая статистика системы"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Статистика боёв
        battles_query = """
            SELECT 
                COUNT(*) as total_battles,
                COUNT(DISTINCT DATE(ts)) as active_days,
                AVG(players_cnt) as avg_players_per_battle,
                AVG(monsters_cnt) as avg_monsters_per_battle
            FROM battles
            WHERE ts >= $1
        """
        battles_stats = await self.db._execute_one(battles_query, cutoff_date)
        
        # Статистика игроков
        players_query = """
            SELECT 
                COUNT(DISTINCT bp.player_id) as unique_players,
                COUNT(DISTINCT bp.clan) as unique_clans
            FROM battle_participants bp
            JOIN battles b ON bp.battle_id = b.id
            WHERE b.ts >= $1
        """
        players_stats = await self.db._execute_one(players_query, cutoff_date)
        
        # Статистика ресурсов
        resources_query = """
            SELECT 
                COUNT(DISTINCT bl.resource_id) as unique_resources,
                SUM(bl.qty) as total_resources
            FROM battle_loot bl
            JOIN battles b ON bl.battle_id = b.id
            WHERE bl.kind = 'resource'
            AND b.ts >= $1
        """
        resources_stats = await self.db._execute_one(resources_query, cutoff_date)
        
        return {
            "period_days": days,
            "battles": {
                "total": battles_stats["total_battles"] or 0,
                "active_days": battles_stats["active_days"] or 0,
                "avg_players_per_battle": float(battles_stats["avg_players_per_battle"] or 0),
                "avg_monsters_per_battle": float(battles_stats["avg_monsters_per_battle"] or 0)
            },
            "players": {
                "unique_players": players_stats["unique_players"] or 0,
                "unique_clans": players_stats["unique_clans"] or 0
            },
            "resources": {
                "unique_resources": resources_stats["unique_resources"] or 0,
                "total_quantity": resources_stats["total_resources"] or 0
            }
        }

    async def get_resources_economy(self, days: int = 30) -> Dict[str, Any]:
        """Экономика ресурсов: приток по дням, доли, суммарные величины и z-score всплесков."""
        cutoff = date.today() - timedelta(days=days)
        # Сутки x ресурс
        per_day_query = """
            SELECT DATE(b.ts) AS day, r.name AS resource, SUM(bl.qty) AS qty
            FROM battle_loot bl
            JOIN battles b ON b.id = bl.battle_id
            JOIN resource_names r ON r.id = bl.resource_id
            WHERE bl.kind = 'resource' AND b.ts >= $1
            GROUP BY DATE(b.ts), r.name
            ORDER BY DATE(b.ts) ASC, r.name ASC
        """
        rows = await self.db._execute_query(per_day_query, cutoff)
        # Сумма по дню
        daily_totals: Dict[date, int] = {}
        for r in rows:
            d = r["day"]
            daily_totals[d] = (daily_totals.get(d, 0) + (r["qty"] or 0))
        # Доли по дню
        series: List[Dict[str, Any]] = []
        for r in rows:
            d = r["day"]; q = int(r["qty"] or 0); total = int(daily_totals.get(d, 0) or 0)
            share = (q / total) if total else 0.0
            series.append({"date": d, "resource": r["resource"], "qty": q, "share": share})
        # Топ всплесков из уже реализованной аномалистики
        anomalies = await self.get_resource_anomalies(days=min(days, 30))
        anomalies_out = [
            {
                "resource": a.resource_name,
                "date": a.date,
                "quantity": a.quantity,
                "z_score": a.z_score,
                "is_anomaly": a.is_anomaly,
            }
            for a in anomalies
        ]
        return {"period_days": days, "daily": series, "daily_totals": [{"date": d, "total": t} for d, t in sorted(daily_totals.items())], "anomalies": anomalies_out}

    # ===== ЭКОНОМИКА С ФИЛЬТРАМИ ПО ЛОКАЦИИ =====
    async def get_resources_series(self, days: int = 30, bucket: str = "day", loc_x: Optional[int] = None, loc_y: Optional[int] = None,
                                   from_date: Optional[date] = None, to_date: Optional[date] = None) -> Dict[str, Any]:
        """Приток каждого ресурса по дням/неделям с опциональным фильтром по локации (loc_x, loc_y) и периодом (from_date..to_date)."""
        time_expr = "bl.battle_ts" if bucket == "day" else "DATE_TRUNC('week', bl.battle_ts)::date"
        # Период
        if from_date and to_date:
            period_clause = "bl.battle_ts BETWEEN $1 AND $2"
            params: List[Any] = [from_date, to_date]
            next_arg = 3
        else:
            cutoff = date.today() - timedelta(days=days)
            period_clause = "bl.battle_ts >= $1"
            params = [cutoff]
            next_arg = 2
        where_loc = []
        if loc_x is not None:
            where_loc.append(f"b.loc_x = ${next_arg}"); params.append(loc_x); next_arg += 1
        if loc_y is not None:
            where_loc.append(f"b.loc_y = ${next_arg}"); params.append(loc_y); next_arg += 1
        loc_clause = (" AND " + " AND ".join(where_loc)) if where_loc else ""

        per_bucket_query = f"""
            SELECT {time_expr} AS bucket_day,
                   COALESCE(r.name, bl.item_name) AS resource,
                   SUM(bl.qty) AS qty
            FROM battle_loot bl
            LEFT JOIN resource_names r ON r.id = bl.resource_id
            JOIN battles b ON bl.battle_id = b.id
            WHERE bl.kind = 'resource' AND {period_clause} {loc_clause}
            GROUP BY bucket_day, resource
            ORDER BY bucket_day ASC, resource ASC
        """
        rows = await self.db._execute_query(per_bucket_query, *params)
        # Сумма по бакету
        bucket_totals: Dict[date, int] = {}
        for r in rows:
            d = r["bucket_day"]
            bucket_totals[d] = (bucket_totals.get(d, 0) + (r["qty"] or 0))
        series: List[Dict[str, Any]] = []
        for r in rows:
            d = r["bucket_day"]; q = int(r["qty"] or 0); total = int(bucket_totals.get(d, 0) or 0)
            share = (q / total) if total else 0.0
            series.append({"date": d, "resource": r["resource"], "qty": q, "share": share})
        return {"period_days": days, "bucket": bucket, "series": series}

    async def get_resources_summary(self, *, loc_x: Optional[int] = None, loc_y: Optional[int] = None,
                                    from_date: Optional[date] = None, to_date: Optional[date] = None,
                                    days: int = 30) -> Dict[str, Any]:
        """Суммарный приток ресурсов за период по каждому ресурсу и число боёв, где он встречался."""
        if from_date and to_date:
            period_clause = "bl.battle_ts BETWEEN $1 AND $2"
            params: List[Any] = [from_date, to_date]
            next_arg = 3
            df, dt = from_date, to_date
        else:
            cutoff = date.today() - timedelta(days=days)
            period_clause = "bl.battle_ts >= $1"
            params = [cutoff]
            next_arg = 2
            df, dt = cutoff, date.today()
        where_loc = []
        if loc_x is not None:
            where_loc.append(f"b.loc_x = ${next_arg}"); params.append(loc_x); next_arg += 1
        if loc_y is not None:
            where_loc.append(f"b.loc_y = ${next_arg}"); params.append(loc_y); next_arg += 1
        loc_clause = (" AND " + " AND ".join(where_loc)) if where_loc else ""
        q = f"""
            SELECT COALESCE(r.name, bl.item_name) AS resource,
                   SUM(bl.qty) AS qty,
                   COUNT(DISTINCT bl.battle_id) AS battles
            FROM battle_loot bl
            LEFT JOIN resource_names r ON r.id = bl.resource_id
            JOIN battles b ON bl.battle_id = b.id
            WHERE bl.kind = 'resource' AND {period_clause} {loc_clause}
            GROUP BY resource
            ORDER BY qty DESC NULLS LAST
        """
        rows = await self.db._execute_query(q, *params)
        items = [{"resource": r["resource"], "qty": int(r["qty"] or 0), "battles": int(r["battles"] or 0)} for r in rows]
        return {"date_from": df, "date_to": dt, "loc": [loc_x, loc_y] if (loc_x is not None and loc_y is not None) else None, "items": items}

    async def get_resources_top_miners(self, days: int = 30, loc_x: Optional[int] = None, loc_y: Optional[int] = None, limit: int = 10, by: str = "player",
                                       from_date: Optional[date] = None, to_date: Optional[date] = None, exclude_bots: bool = False) -> List[Dict[str, Any]]:
        """Топ игроков/кланов по добыче ресурса в локации за период. by in {'player','clan'}. exclude_bots фильтрует ботов."""
        if from_date and to_date:
            period_clause = "bl.battle_ts BETWEEN $1 AND $2"
            params: List[Any] = [from_date, to_date]
            next_arg = 3
        else:
            cutoff = date.today() - timedelta(days=days)
            period_clause = "bl.battle_ts >= $1"
            params = [cutoff]
            next_arg = 2
        group_col = "p.login" if by == "player" else "bp.clan"
        where_loc = []
        if loc_x is not None:
            where_loc.append(f"b.loc_x = ${next_arg}"); params.append(loc_x); next_arg += 1
        if loc_y is not None:
            where_loc.append(f"b.loc_y = ${next_arg}"); params.append(loc_y); next_arg += 1
        loc_clause = (" AND " + " AND ".join(where_loc)) if where_loc else ""
        
        # Берём больше если нужно фильтровать ботов
        fetch_limit = limit * 5 if (exclude_bots and by == "player") else limit
        
        q = f"""
            SELECT {group_col} AS subject, p.id as player_id, SUM(bl.qty) AS total_qty
            FROM battle_loot bl
            JOIN battles b ON bl.battle_id = b.id
            JOIN battle_participants bp ON bp.battle_id = b.id
            JOIN players p ON p.id = bp.player_id
            WHERE bl.kind = 'resource' AND {period_clause} {loc_clause}
            GROUP BY subject, p.id
            ORDER BY total_qty DESC NULLS LAST
            LIMIT {fetch_limit}
        """
        rows = await self.db._execute_query(q, *params)
        
        result = []
        for r in rows:
            if not r["subject"]:
                continue
            
            item = {by: r["subject"], "total_qty": int(r["total_qty"] or 0)}
            
            # УЛУЧШЕНИЕ: Фильтр ботов с Voting Ensemble (K-means + IF)
            # Всегда добавляем метаданные для игроков
            if by == "player":
                player_id = r["player_id"] if "player_id" in r else None
                if player_id:
                    try:
                        # Пробуем Voting Ensemble
                        voting_result = None
                        try:
                            from app.ml.bot_detector import BotDetector
                            detector = BotDetector()
                            if detector.load_model():
                                voting_result = await detector.detect(player_id, self.db, days=180)
                        except:
                            pass
                        
                        if voting_result and 'is_bot' in voting_result:
                            # Используем Voting Ensemble
                            is_bot_val = voting_result.get('is_bot', False)
                            confidence = voting_result.get('confidence', 0)
                            
                            item['bot_score'] = round(confidence, 2)
                            item['playstyle'] = voting_result.get('playstyle')
                            item['detection'] = voting_result.get('method')
                            
                            # Фильтруем ботов по Voting confidence
                            if exclude_bots and confidence >= 0.70:  # порог для фильтрации
                                continue
                            
                            # Статус
                            if confidence >= 0.95:
                                item['status'] = '🔴 Бот (95%+)'
                            elif confidence >= 0.70:
                                item['status'] = '⚠️ Подозрительный'
                            else:
                                item['status'] = '✅ Честный'
                        else:
                            # Fallback: K-means если Voting недоступен
                            playstyle_data = await self._get_playstyle(player_id, days=180)
                            if playstyle_data:
                                bd = playstyle_data.get('bot_detection', {})
                                bot_score_val = bd.get('bot_score', 0)
                                
                                item['bot_score'] = round(bot_score_val, 2)
                                item['playstyle'] = playstyle_data.get('display_name')
                                item['detection'] = 'kmeans'
                                
                                if exclude_bots and bot_score_val >= 0.75:
                                    continue
                                
                                if bot_score_val < 0.5:
                                    item['status'] = '✅ Честный'
                                elif bot_score_val < 0.75:
                                    item['status'] = '⚠️ Подозрительный'
                                else:
                                    item['status'] = '🔴 Бот'
                    except Exception as e:
                        pass
            
            result.append(item)
            
            if len(result) >= limit:
                break
        
        return result[:limit]

    # ===== PvE НАГРУЗКА =====
    async def get_pve_load(self, days: int = 30, bucket: str = "day", loc_x: Optional[int] = None, loc_y: Optional[int] = None,
                           from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Суммарная PvE-нагрузка (monsters_cnt) по периодам и локациям за период."""
        time_expr = "DATE(b.ts)" if bucket == "day" else "DATE_TRUNC('week', b.ts)::date"
        if from_date and to_date:
            period_clause = "b.ts BETWEEN $1 AND $2"
            params: List[Any] = [from_date, to_date]
            next_arg = 3
        else:
            cutoff = datetime.now() - timedelta(days=days)
            period_clause = "b.ts >= $1"
            params = [cutoff]
            next_arg = 2
        where_loc = []
        if loc_x is not None:
            where_loc.append(f"b.loc_x = ${next_arg}"); params.append(loc_x); next_arg += 1
        if loc_y is not None:
            where_loc.append(f"b.loc_y = ${next_arg}"); params.append(loc_y); next_arg += 1
        loc_clause = (" AND " + " AND ".join(where_loc)) if where_loc else ""
        q = f"""
            SELECT {time_expr} AS bucket_day, COALESCE(b.loc_x,0) AS lx, COALESCE(b.loc_y,0) AS ly,
                   SUM(COALESCE(b.monsters_cnt,0)) AS monsters_sum,
                   COUNT(*) AS battles
            FROM battles b
            WHERE {period_clause} {loc_clause}
            GROUP BY bucket_day, lx, ly
            ORDER BY bucket_day ASC, monsters_sum DESC
        """
        rows = await self.db._execute_query(q, *params)
        series = [{"date": r["bucket_day"], "loc": [r["lx"], r["ly"]], "monsters": int(r["monsters_sum"] or 0), "battles": int(r["battles"] or 0)} for r in rows]
        return {"period_days": days, "bucket": bucket, "series": series}

    async def get_pve_top_locations(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Локации с наибольшей PvE-нагрузкой за период."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT COALESCE(loc_x,0) AS lx, COALESCE(loc_y,0) AS ly,
                   SUM(COALESCE(monsters_cnt,0)) AS monsters_sum,
                   COUNT(*) AS battles
            FROM battles
            WHERE ts >= $1
            GROUP BY lx, ly
            ORDER BY monsters_sum DESC
            LIMIT $2
        """
        rows = await self.db._execute_query(q, cutoff, limit)
        return [{"loc": [r["lx"], r["ly"]], "monsters": int(r["monsters_sum"] or 0), "battles": int(r["battles"] or 0)} for r in rows]

    async def get_pve_monster_breakdown(
        self,
        *,
        loc_x: Optional[int] = None,
        loc_y: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        days: int = 30,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Разбивка по видам монстров за период и локацию: сумма count и число боёв по каждому виду.
        Возвращает: {date_from, date_to, loc, monsters: [{kind, spec, count, battles}]}
        """
        if from_date and to_date:
            period_clause = "b.ts BETWEEN $1 AND $2"
            params: List[Any] = [from_date, to_date]
            next_arg = 3
            date_from = from_date
            date_to = to_date
        else:
            cutoff = datetime.now() - timedelta(days=days)
            period_clause = "b.ts >= $1"
            params = [cutoff]
            next_arg = 2
            date_from = cutoff
            date_to = datetime.now()

        where_loc = []
        if loc_x is not None:
            where_loc.append(f"b.loc_x = ${next_arg}"); params.append(loc_x); next_arg += 1
        if loc_y is not None:
            where_loc.append(f"b.loc_y = ${next_arg}"); params.append(loc_y); next_arg += 1
        loc_clause = (" AND " + " AND ".join(where_loc)) if where_loc else ""

        q = f"""
            SELECT mc.kind, mc.spec,
                   SUM(COALESCE(bm.count,0)) AS total_count,
                   COUNT(DISTINCT bm.battle_id) AS battles
            FROM battle_monsters bm
            JOIN battles b ON b.id = bm.battle_id
            JOIN monster_catalog mc ON mc.id = bm.monster_id
            WHERE {period_clause} {loc_clause}
            GROUP BY mc.kind, mc.spec
            ORDER BY total_count DESC NULLS LAST
            LIMIT $ {next_arg}
        """.replace("$ ", "$")
        params.append(limit)
        rows = await self.db._execute_query(q, *params)
        monsters = [{
            "kind": r["kind"],
            "spec": r["spec"],
            "count": int(r["total_count"] or 0),
            "battles": int(r["battles"] or 0),
        } for r in rows]
        return {
            "date_from": date_from,
            "date_to": date_to,
            "loc": [loc_x, loc_y] if (loc_x is not None and loc_y is not None) else None,
            "monsters": monsters,
        }

    # ===== СОЦИАЛЬНЫЕ АНАЛИТИКИ =====

    async def get_player_allies(self, login: str, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Топ союзников игрока (с синергией стилей K-means)."""
        pid = await self._get_player_id_by_login(login)
        if not pid:
            return []
        cutoff = datetime.now() - timedelta(days=days)
        
        # УЛУЧШЕНИЕ: Получаем стиль игрока
        player_playstyle_data = await self._get_playstyle(pid, days=180)
        player_style = player_playstyle_data.get('playstyle') if player_playstyle_data else None
        
        # МАТРИЦА СИНЕРГИИ СТИЛЕЙ
        SYNERGY = {
            ('aggressive_pvp', 'safe_farmer'): 0.95,  # атака + танк = идеал
            ('aggressive_pvp', 'balanced'): 0.85,
            ('aggressive_pvp', 'aggressive_pvp'): 0.75,  # два атакующих - конкуренция
            ('aggressive_pvp', 'elite_pvp'): 0.90,
            ('elite_pvp', 'safe_farmer'): 0.92,
            ('elite_pvp', 'balanced'): 0.88,
            ('elite_pvp', 'elite_pvp'): 0.85,
            ('safe_farmer', 'safe_farmer'): 0.50,  # два танка - плохо
            ('safe_farmer', 'balanced'): 0.75,
            ('safe_farmer', 'pve_grinder'): 0.70,
            ('balanced', 'balanced'): 0.70,
            ('pvp_novice', 'safe_farmer'): 0.90,  # новичок + защита
            ('pvp_novice', 'elite_pvp'): 0.88,  # учитель + ученик
            ('pvp_novice', 'balanced'): 0.80,
            ('pve_grinder', 'pve_grinder'): 0.65,
            ('pve_grinder', 'safe_farmer'): 0.70,
        }
        
        q = """
            SELECT p2.login AS ally, p2.id as ally_player_id, COUNT(DISTINCT b.id) AS battles_together
            FROM battle_participants bp1
            JOIN battle_participants bp2 ON bp1.battle_id = bp2.battle_id AND bp1.side = bp2.side AND bp1.player_id != bp2.player_id
            JOIN battles b ON bp1.battle_id = b.id
            JOIN players p2 ON bp2.player_id = p2.id
            WHERE bp1.player_id = $1 AND b.ts >= $2
            GROUP BY p2.login, p2.id
            ORDER BY battles_together DESC
            LIMIT $3
        """
        rows = await self.db._execute_query(q, pid, cutoff, limit * 2)
        
        result = []
        for r in rows:
            battles_score = int(r["battles_together"])
            
            item = {
                "ally": r["ally"],
                "battles_together": battles_score
            }
            
            # УЛУЧШЕНИЕ: Добавляем синергию стилей
            if player_style and r.get("ally_player_id"):
                ally_playstyle_data = await self._get_playstyle(r["ally_player_id"], days=180)
                if ally_playstyle_data:
                    ally_style = ally_playstyle_data.get('playstyle')
                    item['ally_playstyle'] = ally_playstyle_data.get('display_name')
                    
                    # Ищем синергию (в обе стороны)
                    key = (player_style, ally_style)
                    key_reverse = (ally_style, player_style)
                    synergy = SYNERGY.get(key) or SYNERGY.get(key_reverse) or 0.65
                    
                    item['synergy_score'] = round(synergy, 2)
                    
                    # Комбинированный score (60% история + 40% синергия)
                    item['recommendation_score'] = round(battles_score * 0.6 + synergy * 100 * 0.4, 2)
                    
                    # Объяснение
                    if synergy >= 0.9:
                        item['synergy_text'] = '🌟 Отличная синергия'
                    elif synergy >= 0.75:
                        item['synergy_text'] = '✅ Хорошая синергия'
                    elif synergy >= 0.60:
                        item['synergy_text'] = '🟡 Средняя синергия'
                    else:
                        item['synergy_text'] = '❌ Слабая синергия'
                else:
                    item['recommendation_score'] = battles_score * 0.6
            else:
                item['recommendation_score'] = battles_score * 0.6
            
            result.append(item)
        
        # Пересортировка по recommendation_score
        result.sort(key=lambda x: x.get('recommendation_score', 0), reverse=True)
        
        return result[:limit]

    async def get_player_rivals(self, login: str, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Топ противников игрока (те, против кого чаще воевал)."""
        pid = await self._get_player_id_by_login(login)
        if not pid:
            return []
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT p2.login AS rival, COUNT(DISTINCT b.id) AS battles_against
            FROM battle_participants bp1
            JOIN battle_participants bp2 ON bp1.battle_id = bp2.battle_id AND bp1.side != bp2.side AND bp1.player_id != bp2.player_id
            JOIN battles b ON bp1.battle_id = b.id
            JOIN players p2 ON bp2.player_id = p2.id
            WHERE bp1.player_id = $1 AND b.ts >= $2
            GROUP BY p2.login
            ORDER BY battles_against DESC
            LIMIT $3
        """
        rows = await self.db._execute_query(q, pid, cutoff, limit)
        return [{"rival": r["rival"], "battles_against": int(r["battles_against"])} for r in rows]

    async def get_clan_wars(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Матрица межклановых войн: пары кланов и число их столкновений."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT bp1.clan AS clan1, bp2.clan AS clan2, COUNT(DISTINCT b.id) AS battles
            FROM battle_participants bp1
            JOIN battle_participants bp2 ON bp1.battle_id = bp2.battle_id AND bp1.side != bp2.side AND bp1.player_id != bp2.player_id
            JOIN battles b ON bp1.battle_id = b.id
            WHERE b.ts >= $1 AND bp1.clan IS NOT NULL AND bp2.clan IS NOT NULL AND bp1.clan < bp2.clan
            GROUP BY bp1.clan, bp2.clan
            ORDER BY battles DESC
            LIMIT $2
        """
        rows = await self.db._execute_query(q, cutoff, limit)
        return [{"clan1": r["clan1"], "clan2": r["clan2"], "battles": int(r["battles"])} for r in rows]

    # ===== ТЕРРИТОРИАЛЬНЫЕ АНАЛИТИКИ =====

    async def get_map_heatmap(self, days: int = 30, limit: int = 100) -> List[Dict[str, Any]]:
        """Тепловая карта боёв: плотность боёв по координатам."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT COALESCE(loc_x,0) AS x, COALESCE(loc_y,0) AS y, COUNT(*) AS battles
            FROM battles
            WHERE ts >= $1
            GROUP BY x, y
            ORDER BY battles DESC
            LIMIT $2
        """
        rows = await self.db._execute_query(q, cutoff, limit)
        return [{"loc": [r["x"], r["y"]], "battles": int(r["battles"])} for r in rows]

    async def get_pvp_hotspots(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Горячие точки PvP: локации с высокой долей PvP боёв."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT COALESCE(loc_x,0) AS x, COALESCE(loc_y,0) AS y,
                   COUNT(*) AS total_battles,
                   SUM(CASE WHEN players_cnt > 1 THEN 1 ELSE 0 END) AS pvp_battles
            FROM battles
            WHERE ts >= $1
            GROUP BY x, y
            HAVING COUNT(*) >= 5
            ORDER BY (SUM(CASE WHEN players_cnt > 1 THEN 1 ELSE 0 END)::float / COUNT(*)) DESC
            LIMIT $2
        """
        rows = await self.db._execute_query(q, cutoff, limit)
        return [{"loc": [r["x"], r["y"]], "total_battles": int(r["total_battles"]), "pvp_battles": int(r["pvp_battles"]), "pvp_ratio": float(r["pvp_battles"]) / float(r["total_battles"]) if r["total_battles"] > 0 else 0.0} for r in rows]

    async def get_clan_control(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Доминирование кланов по локациям: какой клан чаще воюет в каждой зоне."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT COALESCE(b.loc_x,0) AS x, COALESCE(b.loc_y,0) AS y, bp.clan,
                   COUNT(*) AS battles
            FROM battles b
            JOIN battle_participants bp ON bp.battle_id = b.id
            WHERE b.ts >= $1 AND bp.clan IS NOT NULL
            GROUP BY x, y, bp.clan
            ORDER BY x, y, battles DESC
        """
        rows = await self.db._execute_query(q, cutoff)
        # Группируем по локации и берём топ клан для каждой
        loc_map: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for r in rows:
            loc = (r["x"], r["y"])
            if loc not in loc_map:
                loc_map[loc] = {"loc": [r["x"], r["y"]], "dominant_clan": r["clan"], "battles": int(r["battles"])}
        return sorted(loc_map.values(), key=lambda x: x["battles"], reverse=True)[:limit]

    # ===== ВРЕМЕННЫЕ АНАЛИТИКИ =====

    async def get_activity_heatmap(self, days: int = 30) -> Dict[str, Any]:
        """24x7 карта активности: распределение боёв по часам и дням недели."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT EXTRACT(HOUR FROM ts) AS hour,
                   EXTRACT(DOW FROM ts) AS dow,
                   COUNT(*) AS battles
            FROM battles
            WHERE ts >= $1
            GROUP BY hour, dow
        """
        rows = await self.db._execute_query(q, cutoff)
        
        # Создаём словарь для быстрого поиска
        data_dict = {(int(r["dow"]), int(r["hour"])): int(r["battles"]) for r in rows}
        
        # Названия дней недели (0 = воскресенье в PostgreSQL DOW)
        day_names = {
            0: "воскресенье",
            1: "понедельник",
            2: "вторник",
            3: "среда",
            4: "четверг",
            5: "пятница",
            6: "суббота"
        }
        
        # Заполняем ВСЕ 7 дней x 24 часа
        heatmap = []
        for dow in range(7):
            for hour in range(24):
                heatmap.append({
                    "day_of_week": dow,
                    "day_name": day_names[dow],
                    "hour": hour,
                    "battles": data_dict.get((dow, hour), 0)
                })
        
        return {"period_days": days, "heatmap": heatmap}

    async def get_peak_hours(self, days: int = 30) -> Dict[str, Any]:
        """Пиковые часы для PvP и PvE - возвращает ВСЕ 24 часа."""
        cutoff = datetime.now() - timedelta(days=days)
        q_pvp = """
            SELECT EXTRACT(HOUR FROM ts) AS hour, COUNT(*) AS battles
            FROM battles
            WHERE ts >= $1 AND players_cnt > 1
            GROUP BY hour
        """
        q_pve = """
            SELECT EXTRACT(HOUR FROM ts) AS hour, COUNT(*) AS battles
            FROM battles
            WHERE ts >= $1 AND monsters_cnt > 0
            GROUP BY hour
        """
        pvp_rows = await self.db._execute_query(q_pvp, cutoff)
        pve_rows = await self.db._execute_query(q_pve, cutoff)
        
        # Создаём словари для быстрого поиска
        pvp_dict = {int(r["hour"]): int(r["battles"]) for r in pvp_rows}
        pve_dict = {int(r["hour"]): int(r["battles"]) for r in pve_rows}
        
        # Заполняем ВСЕ 24 часа (0-23)
        all_hours = []
        for hour in range(24):
            all_hours.append({
                "hour": hour,
                "pvp_battles": pvp_dict.get(hour, 0),
                "pve_battles": pve_dict.get(hour, 0),
                "total_battles": pvp_dict.get(hour, 0) + pve_dict.get(hour, 0)
            })
        
        return {
            "period_days": days,
            "hours": all_hours
        }

    # ===== ЭКОНОМИКА РАСШИРЕННАЯ =====

    async def get_farm_efficiency(self, login: str, days: int = 30) -> Dict[str, Any]:
        """Эффективность фарма игрока: ресурсов в час."""
        pid = await self._get_player_id_by_login(login)
        if not pid:
            return {"error": "Player not found"}
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT SUM(bl.qty) AS total_resources,
                   MIN(b.ts) AS first_battle,
                   MAX(b.ts) AS last_battle
            FROM battle_loot bl
            JOIN battles b ON bl.battle_id = b.id
            JOIN battle_participants bp ON bp.battle_id = b.id
            WHERE bp.player_id = $1 AND b.ts >= $2 AND bl.kind = 'resource'
        """
        row = await self.db._execute_one(q, pid, cutoff)
        if not row or not row["total_resources"]:
            return {"login": login, "period_days": days, "total_resources": 0, "hours_played": 0, "resources_per_hour": 0}
        hours = (row["last_battle"] - row["first_battle"]).total_seconds() / 3600.0 if row["last_battle"] and row["first_battle"] else 0
        return {
            "login": login,
            "period_days": days,
            "total_resources": int(row["total_resources"]),
            "hours_played": round(hours, 2),
            "resources_per_hour": round(float(row["total_resources"]) / hours, 2) if hours > 0 else 0,
        }

    async def get_rare_items(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Редкий лут за период: предметы с низкой частотой дропа."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT COALESCE(r.name, bl.item_name, 'неизвестный') AS item, bl.kind, COUNT(*) AS drop_count, SUM(bl.qty) AS total_qty
            FROM battle_loot bl
            LEFT JOIN resource_names r ON r.id = bl.resource_id
            JOIN battles b ON bl.battle_id = b.id
            WHERE b.ts >= $1 AND COALESCE(r.name, bl.item_name) IS NOT NULL
            GROUP BY item, bl.kind
            ORDER BY drop_count ASC
            LIMIT $2
        """
        rows = await self.db._execute_query(q, cutoff, limit)
        return [{"item": r["item"], "kind": r["kind"], "drop_count": int(r["drop_count"]), "total_qty": int(r["total_qty"] or 0)} for r in rows]

    # ===== СОРЕВНОВАТЕЛЬНЫЕ МЕТРИКИ =====

    async def get_player_elo_pvp(self, days: int = 30, limit: int = 50) -> List[Dict[str, Any]]:
        """ELO рейтинг для PvP боёв (players_cnt > 1)."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT p.login,
                   SUM(CASE WHEN bp.survived = true THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN bp.survived = false THEN 1 ELSE 0 END) AS losses,
                   COUNT(*) AS total_battles
            FROM battle_participants bp
            JOIN battles b ON bp.battle_id = b.id
            JOIN players p ON bp.player_id = p.id
            WHERE b.ts >= $1 AND b.players_cnt > 1 AND p.login NOT LIKE '$%'
            GROUP BY p.login
            HAVING COUNT(*) >= 10
            ORDER BY (SUM(CASE WHEN bp.survived = true THEN 1 ELSE 0 END)::float / COUNT(*)) DESC
            LIMIT $2
        """
        rows = await self.db._execute_query(q, cutoff, limit)
        result = []
        base_elo = 1000
        for r in rows:
            win_rate = float(r["wins"]) / float(r["total_battles"]) if r["total_battles"] > 0 else 0
            elo = base_elo + (r["wins"] - r["losses"]) * 10
            result.append({"login": r["login"], "elo": int(elo), "wins": int(r["wins"]), "losses": int(r["losses"]), "win_rate": round(win_rate, 3), "total_battles": int(r["total_battles"])})
        return sorted(result, key=lambda x: x["elo"], reverse=True)

    async def get_player_elo_pve(self, days: int = 30, limit: int = 50) -> List[Dict[str, Any]]:
        """ELO рейтинг для PvE боёв (monsters_cnt > 0)."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT p.login,
                   SUM(CASE WHEN bp.survived = true THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN bp.survived = false THEN 1 ELSE 0 END) AS losses,
                   COUNT(*) AS total_battles
            FROM battle_participants bp
            JOIN battles b ON bp.battle_id = b.id
            JOIN players p ON bp.player_id = p.id
            WHERE b.ts >= $1 AND b.monsters_cnt > 0 AND p.login NOT LIKE '$%'
            GROUP BY p.login
            HAVING COUNT(*) >= 10
            ORDER BY (SUM(CASE WHEN bp.survived = true THEN 1 ELSE 0 END)::float / COUNT(*)) DESC
            LIMIT $2
        """
        rows = await self.db._execute_query(q, cutoff, limit)
        result = []
        base_elo = 1000
        for r in rows:
            win_rate = float(r["wins"]) / float(r["total_battles"]) if r["total_battles"] > 0 else 0
            elo = base_elo + (r["wins"] - r["losses"]) * 10
            result.append({"login": r["login"], "elo": int(elo), "wins": int(r["wins"]), "losses": int(r["losses"]), "win_rate": round(win_rate, 3), "total_battles": int(r["total_battles"])})
        return sorted(result, key=lambda x: x["elo"], reverse=True)

    async def get_player_streaks(self, login: str, days: int = 30) -> Dict[str, Any]:
        """Текущие и рекордные серии побед/поражений игрока."""
        pid = await self._get_player_id_by_login(login)
        if not pid:
            return {"error": "Player not found"}
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT bp.survived, b.ts
            FROM battle_participants bp
            JOIN battles b ON bp.battle_id = b.id
            WHERE bp.player_id = $1 AND b.ts >= $2
            ORDER BY b.ts ASC
        """
        rows = await self.db._execute_query(q, pid, cutoff)
        current_win_streak = 0
        current_loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        last_result = None
        for r in rows:
            if r["survived"]:
                if last_result == "win":
                    current_win_streak += 1
                else:
                    current_win_streak = 1
                    current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
                last_result = "win"
            else:
                if last_result == "loss":
                    current_loss_streak += 1
                else:
                    current_loss_streak = 1
                    current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
                last_result = "loss"
        return {
            "login": login,
            "period_days": days,
            "current_win_streak": current_win_streak,
            "current_loss_streak": current_loss_streak,
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
        }

    # ===== МЕТА-АНАЛИЗ =====

    async def get_profession_stats(self, days: int = 30, battle_type: str = "all") -> List[Dict[str, Any]]:
        """Статистика по профессиям: winrate, популярность (только реальные игроки, без монстров)."""
        cutoff = datetime.now() - timedelta(days=days)
        
        # Определяем фильтр по типу боя
        # PvE = есть монстры (логин начинается с $)
        # PvP = только игроки (все логины НЕ начинаются с $)
        battle_type_filter = ""
        if battle_type == "pve":
            # Только бои где есть хотя бы один монстр
            battle_type_filter = """
                AND b.id IN (
                    SELECT DISTINCT bp2.battle_id 
                    FROM battle_participants bp2
                    JOIN players p2 ON bp2.player_id = p2.id
                    WHERE p2.login LIKE '$%'
                )
            """
        elif battle_type == "pvp":
            # Только бои где НЕТ монстров (все игроки)
            battle_type_filter = """
                AND b.id NOT IN (
                    SELECT DISTINCT bp2.battle_id 
                    FROM battle_participants bp2
                    JOIN players p2 ON bp2.player_id = p2.id
                    WHERE p2.login LIKE '$%'
                )
            """
        
        q = f"""
            SELECT bp.profession,
                   COUNT(*) AS total_battles,
                   SUM(CASE WHEN bp.survived = true THEN 1 ELSE 0 END) AS wins
            FROM battle_participants bp
            JOIN battles b ON bp.battle_id = b.id
            JOIN players p ON bp.player_id = p.id
            WHERE b.ts >= $1 
              AND bp.profession IS NOT NULL
              AND p.login NOT LIKE '$%'  -- Исключаем монстров из статистики игроков
              {battle_type_filter}
            GROUP BY bp.profession
            ORDER BY total_battles DESC
        """
        rows = await self.db._execute_query(q, cutoff)
        return [{
            "profession_id": r["profession"],  # Название профессии
            "total_battles": int(r["total_battles"]),
            "wins": int(r["wins"]),
            "win_rate": round(float(r["wins"]) / float(r["total_battles"]), 3) if r["total_battles"] > 0 else 0,
        } for r in rows]

    async def get_players_by_profession(self, profession: str, limit: int = 50, days: int = 365, min_battles: int = 1) -> List[Dict[str, Any]]:
        """Список игроков по профессии."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT p.login,
                   bp.profession,
                   COUNT(*) AS total_battles,
                   SUM(CASE WHEN bp.survived = true THEN 1 ELSE 0 END) AS wins,
                   MAX(b.ts) AS last_battle
            FROM battle_participants bp
            JOIN battles b ON bp.battle_id = b.id
            JOIN players p ON bp.player_id = p.id
            WHERE b.ts >= $1 AND bp.profession = $2
            GROUP BY p.login, bp.profession
            HAVING COUNT(*) >= $3
            ORDER BY total_battles DESC
            LIMIT $4
        """
        rows = await self.db._execute_query(q, cutoff, profession, min_battles, limit)
        return [{
            "login": r["login"],
            "profession": r["profession"],
            "total_battles": int(r["total_battles"]),
            "wins": int(r["wins"]),
            "win_rate": round(float(r["wins"]) / float(r["total_battles"]), 3) if r["total_battles"] > 0 else 0,
            "last_battle": r["last_battle"].isoformat() if r["last_battle"] else None,
        } for r in rows]

    async def get_balance_report(self, days: int = 30, battle_type: str = "all") -> Dict[str, Any]:
        """Отчёт о дисбалансе: выявление OP/UP профессий и стилей игры."""
        prof_stats = await self.get_profession_stats(days, battle_type)
        if not prof_stats:
            return {"period_days": days, "professions": [], "imbalanced": []}
        avg_winrate = sum(p["win_rate"] for p in prof_stats) / len(prof_stats)
        threshold = 0.1  # +/- 10% от средней
        imbalanced = []
        for p in prof_stats:
            if abs(p["win_rate"] - avg_winrate) > threshold:
                status = "OP" if p["win_rate"] > avg_winrate else "UP"
                imbalanced.append({"profession_id": p["profession_id"], "win_rate": p["win_rate"], "status": status, "deviation": round(p["win_rate"] - avg_winrate, 3)})
        
        # УЛУЧШЕНИЕ: Баланс по стилям игры (K-means)
        style_balance = await self._get_playstyle_balance(days)
        
        return {
            "period_days": days,
            "avg_win_rate": round(avg_winrate, 3),
            "professions": prof_stats,
            "imbalanced": sorted(imbalanced, key=lambda x: abs(x["deviation"]), reverse=True),
            "playstyle_balance": style_balance,  # НОВОЕ
        }
    
    async def _get_playstyle_balance(self, days: int = 30) -> Dict[str, Any]:
        """Анализ баланса стилей игры."""
        try:
            from app.ml.playstyle_classifier import PlaystyleClassifier, SKLEARN_AVAILABLE
            
            if not SKLEARN_AVAILABLE:
                return {"error": "sklearn not available"}
            
            classifier = PlaystyleClassifier()
            if not classifier.load_model():
                return {"error": "model not trained"}
            
            # Получаем все кластеры
            clusters = classifier.get_cluster_stats()
            
            style_winrates = {}
            cutoff = datetime.now() - timedelta(days=days)
            
            # Для каждого стиля рассчитываем winrate
            for cluster in clusters:
                style = cluster['playstyle']
                style_name = cluster['display_name']
                
                # Получаем всех игроков этого стиля
                q = """
                    SELECT AVG(CASE WHEN bp.survived::int = 1 THEN 1.0 ELSE 0.0 END) as wr,
                           COUNT(*) as battles
                    FROM battle_participants bp
                    JOIN battles b ON b.id = bp.battle_id
                    WHERE b.ts >= $1
                    AND bp.player_id IN (
                        SELECT player_id 
                        FROM (
                            SELECT DISTINCT ON (bp2.player_id) bp2.player_id
                            FROM battle_participants bp2
                            JOIN battles b2 ON b2.id = bp2.battle_id
                            WHERE b2.ts >= $1
                            LIMIT 10000
                        ) recent_players
                    )
                """
                
                # Упрощённый подход: берём винрейт из фичей кластера
                wr = cluster.get('avg_features', {}).get('survival_rate', 0.5)
                
                style_winrates[style_name] = {
                    'winrate': round(wr, 3),
                    'player_count': cluster.get('player_count', 0),
                }
            
            # Выявление дисбаланса
            if style_winrates:
                avg_wr = sum(s['winrate'] for s in style_winrates.values()) / len(style_winrates)
                
                imbalanced_styles = []
                for style, data in style_winrates.items():
                    deviation = data['winrate'] - avg_wr
                    if abs(deviation) > 0.10:  # >10% отклонение
                        status = 'OP' if deviation > 0 else 'UP'
                        imbalanced_styles.append({
                            'playstyle': style,
                            'winrate': data['winrate'],
                            'player_count': data['player_count'],
                            'status': status,
                            'deviation': round(deviation, 3),
                            'issue': f'Стиль {"слишком сильный" if status == "OP" else "слишком слабый"}'
                        })
                
                return {
                    'avg_winrate': round(avg_wr, 3),
                    'by_style': style_winrates,
                    'imbalanced': sorted(imbalanced_styles, key=lambda x: abs(x['deviation']), reverse=True),
                }
            
            return {"error": "no data"}
            
        except Exception as e:
            return {"error": str(e)}

    # ===== ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА =====

    async def get_churn_prediction(self, days: int = 30, limit: int = 50) -> List[Dict[str, Any]]:
        """Риск ухода игроков: игроки со снижением активности."""
        cutoff = datetime.now() - timedelta(days=days)
        mid_point = datetime.now() - timedelta(days=days // 2)
        q = """
            SELECT p.login,
                   COUNT(CASE WHEN b.ts < $2 THEN 1 END) AS battles_first_half,
                   COUNT(CASE WHEN b.ts >= $2 THEN 1 END) AS battles_second_half,
                   MAX(b.ts) AS last_battle
            FROM battle_participants bp
            JOIN battles b ON bp.battle_id = b.id
            JOIN players p ON bp.player_id = p.id
            WHERE b.ts >= $1
            GROUP BY p.login
            HAVING COUNT(*) >= 5
            ORDER BY (COUNT(CASE WHEN b.ts >= $2 THEN 1 END)::float / NULLIF(COUNT(CASE WHEN b.ts < $2 THEN 1 END), 0)) ASC
            LIMIT $3
        """
        rows = await self.db._execute_query(q, cutoff, mid_point, limit * 2)  # берём больше для фильтрации
        
        # ЦЕННОСТЬ СТИЛЕЙ для приоритизации
        STYLE_VALUE = {
            'elite_pvp': 1.0,
            'aggressive_pvp': 0.9,
            'balanced': 0.7,
            'safe_farmer': 0.6,
            'pvp_novice': 0.5,
            'pve_grinder': 0.3,
            'bot_farmer': 0.0,
        }
        
        result = []
        for r in rows:
            first_half = int(r["battles_first_half"] or 0)
            second_half = int(r["battles_second_half"] or 0)
            churn_score = 1.0 - (float(second_half) / float(first_half)) if first_half > 0 else 0
            days_since_last = (datetime.now(r["last_battle"].tzinfo) - r["last_battle"]).days if r["last_battle"] else 999
            
            player_id = await self._get_player_id_by_login(r["login"])
            
            item = {
                "login": r["login"],
                "battles_first_half": first_half,
                "battles_second_half": second_half,
                "churn_score": round(churn_score, 3),
                "days_since_last_battle": days_since_last,
            }
            
            # УЛУЧШЕНИЕ: Добавляем playstyle и приоритизацию с Voting Ensemble
            if player_id:
                # Пробуем Voting Ensemble для более точной детекции ботов
                voting_result = None
                try:
                    from app.ml.bot_detector import BotDetector
                    detector = BotDetector()
                    if detector.load_model():
                        voting_result = await detector.detect(player_id, self.db, days=days)
                except:
                    pass
                
                # Определяем стиль и бот-статус
                style = 'balanced'
                is_bot = False
                bot_confidence = 0.0
                
                if voting_result and 'is_bot' in voting_result:
                    # Используем Voting Ensemble
                    is_bot = voting_result.get('is_bot', False)
                    bot_confidence = voting_result.get('confidence', 0)
                    item['playstyle'] = voting_result.get('playstyle')
                    item['detection'] = voting_result.get('method')
                    
                    # Определяем style для STYLE_VALUE
                    playstyle_mapping = {
                        'Агрессивный PvP': 'aggressive_pvp',
                        'Элитный PvP': 'elite_pvp',
                        'PvP новичок': 'pvp_novice',
                        'Безопасный фармер': 'safe_farmer',
                        'PvE гриндер': 'pve_grinder',
                        'Сбалансированный': 'balanced',
                    }
                    display_name = voting_result.get('playstyle', 'balanced')
                    style = playstyle_mapping.get(display_name, 'balanced')
                else:
                    # Fallback: K-means
                    playstyle_data = await self._get_playstyle(player_id, days=days)
                    if playstyle_data:
                        style = playstyle_data.get('playstyle', 'balanced')
                        item['playstyle'] = playstyle_data.get('display_name')
                        item['detection'] = 'kmeans'
                        
                        bd = playstyle_data.get('bot_detection', {})
                        is_bot = bd.get('is_likely_bot', False)
                        bot_confidence = bd.get('bot_score', 0)
                
                # Ценность игрока
                value = STYLE_VALUE.get(style, 0.5)
                item['player_value'] = round(value, 2)
                
                # Если Voting Ensemble уверен что это бот - снижаем ценность
                if is_bot and bot_confidence >= 0.95:
                    value = 0.0  # бот с 95% уверенностью = нулевая ценность
                    item['bot_confidence'] = round(bot_confidence, 2)
                elif is_bot and bot_confidence >= 0.70:
                    value = value * 0.3  # снижаем ценность на 70%
                    item['bot_confidence'] = round(bot_confidence, 2)
                
                # Приоритет = churn × ценность
                priority_score = churn_score * value
                item['priority_score'] = round(priority_score, 3)
                
                # Категория приоритета
                if is_bot and bot_confidence >= 0.70:
                    item['priority'] = 'LOW'
                    item['action'] = f'🤖 Бот ({bot_confidence:.0%}) - игнорировать'
                elif value >= 0.8 and churn_score > 0.6:
                    item['priority'] = 'CRITICAL'
                    item['action'] = '🚨 Срочно retention меры'
                elif value >= 0.5 and churn_score > 0.7:
                    item['priority'] = 'HIGH'
                    item['action'] = '⚠️ Обратить внимание'
                elif value < 0.3:
                    item['priority'] = 'LOW'
                    item['action'] = '🤖 Вероятно бот - игнорировать'
                else:
                    item['priority'] = 'MEDIUM'
                    item['action'] = '📊 Мониторить'
            
            result.append(item)
        
        # Сортировка по priority_score если есть, иначе по churn_score
        result.sort(key=lambda x: x.get('priority_score', x.get('churn_score', 0)), reverse=True)
        return result[:limit]

    async def get_farming_recommendations(self, login: str, days: int = 30) -> Dict[str, Any]:
        """Рекомендации по фармингу: где лучше фармить ресурсы для данного игрока (с персонализацией K-means)."""
        pid = await self._get_player_id_by_login(login)
        if not pid:
            return {"error": "Player not found"}
        cutoff = datetime.now() - timedelta(days=days)
        
        # УЛУЧШЕНИЕ: Получаем стиль игрока
        playstyle_data = await self._get_playstyle(pid, days=180)
        playstyle = playstyle_data.get('playstyle') if playstyle_data else 'balanced'
        
        # Анализируем, где игрок фармил и какой был выход; затем сравниваем с глобальной статистикой
        q_player = """
            SELECT b.loc_x, b.loc_y, SUM(bl.qty) AS total_resources, COUNT(DISTINCT b.id) AS battles
            FROM battle_loot bl
            JOIN battles b ON bl.battle_id = b.id
            JOIN battle_participants bp ON bp.battle_id = b.id
            WHERE bp.player_id = $1 AND b.ts >= $2 AND bl.kind = 'resource'
            GROUP BY b.loc_x, b.loc_y
        """
        q_global = """
            SELECT b.loc_x, b.loc_y, AVG(loot.qty) AS avg_resources_per_battle
            FROM (
                SELECT bl.battle_id, SUM(bl.qty) AS qty
                FROM battle_loot bl
                JOIN battles b ON bl.battle_id = b.id
                WHERE b.ts >= $1 AND bl.kind = 'resource'
                GROUP BY bl.battle_id
            ) loot
            JOIN battles b ON loot.battle_id = b.id
            GROUP BY b.loc_x, b.loc_y
            HAVING COUNT(*) >= 10
            ORDER BY avg_resources_per_battle DESC
            LIMIT 20
        """
        player_rows = await self.db._execute_query(q_player, pid, cutoff)
        global_rows = await self.db._execute_query(q_global, cutoff)
        player_locs = {(r["loc_x"], r["loc_y"]): float(r["total_resources"]) / float(r["battles"]) for r in player_rows if r["battles"] > 0}
        recommendations = []
        for r in global_rows:
            loc = (r["loc_x"], r["loc_y"])
            global_avg = float(r["avg_resources_per_battle"] or 0)
            player_avg = player_locs.get(loc, 0)
            if global_avg > player_avg * 1.2:  # Если глобальная средняя на 20% выше, чем у игрока — рекомендуем
                base_score = global_avg - player_avg if player_avg > 0 else global_avg
                
                # УЛУЧШЕНИЕ: Получаем PvP риск локации
                pvp_risk = await self._get_location_pvp_risk(r["loc_x"], r["loc_y"], days)
                
                # УЛУЧШЕНИЕ: Персонализация по стилю
                score = base_score
                notes = []
                
                if playstyle in ['safe_farmer', 'bot_farmer', 'pve_grinder']:
                    # Фармеры избегают PvP
                    if pvp_risk > 0.3:
                        score = base_score * 0.5
                        notes.append('⚠️ Опасная зона (много PvP)')
                    else:
                        score = base_score * 1.2
                        notes.append('✅ Безопасная зона')
                
                elif playstyle in ['aggressive_pvp', 'elite_pvp']:
                    # PvP'еры любят действие
                    if pvp_risk > 0.3:
                        score = base_score * 1.5
                        notes.append('⚔️ Много PvP действия!')
                    else:
                        score = base_score * 0.8
                        notes.append('😴 Мало PvP')
                
                elif playstyle == 'pvp_novice':
                    # Новички в PvP - умеренный риск OK
                    if 0.1 < pvp_risk < 0.4:
                        score = base_score * 1.1
                        notes.append('📚 Хорошо для обучения PvP')
                    elif pvp_risk > 0.5:
                        score = base_score * 0.7
                        notes.append('⚠️ Слишком опасно для новичка')
                
                recommendations.append({
                    "loc": [r["loc_x"], r["loc_y"]],
                    "avg_resources_per_battle": round(global_avg, 2),
                    "player_avg": round(player_avg, 2) if player_avg > 0 else None,
                    "improvement_potential": round(base_score, 2),
                    "personalized_score": round(score, 2),
                    "pvp_risk": round(pvp_risk, 3),
                    "notes": notes,
                })
        
        # Сортировка по персонализированному score
        recommendations.sort(key=lambda x: x["personalized_score"], reverse=True)
        
        return {
            "login": login,
            "period_days": days,
            "playstyle": playstyle_data.get('display_name') if playstyle_data else 'Неизвестный',
            "recommendations": recommendations[:5],
        }
    
    async def _get_location_pvp_risk(self, loc_x: int, loc_y: int, days: int = 30) -> float:
        """Рассчитывает PvP риск локации (доля PvP боёв)."""
        cutoff = datetime.now() - timedelta(days=days)
        q = """
            SELECT 
                COUNT(*) as total_battles,
                SUM(CASE WHEN b.battle_type IN ('B', 'C') THEN 1 ELSE 0 END) as pvp_battles
            FROM battles b
            WHERE b.loc_x = $1 AND b.loc_y = $2 AND b.ts >= $3
        """
        r = await self.db._execute_one(q, loc_x, loc_y, cutoff)
        if not r or r["total_battles"] == 0:
            return 0.0
        return float(r["pvp_battles"]) / float(r["total_battles"])
