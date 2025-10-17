-- Витрина: Ежедневные фичи кланов
-- Назначение: Агрегированные метрики кланов за день
-- Частота обновления: Ежедневно

CREATE OR REPLACE VIEW daily_clan_features AS
WITH clan_daily_stats AS (
    SELECT 
        bp.clan,
        c.name as clan_name,
        DATE(b.ts) as battle_date,
        COUNT(DISTINCT bp.player_id) as members_count,
        COUNT(b.id) as battles_count,
        SUM(CASE WHEN bp.survived = 1 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN bp.survived = 0 THEN 1 ELSE 0 END) as losses,
        SUM(bp.kills_monsters) as kills_monsters,
        SUM(bp.kills_players) as kills_players,
        SUM(bp.rank_points) as total_rank_points,
        SUM(bp.pve_points) as total_pve_points,
        AVG(bp.rank_points) as avg_rank_points,
        AVG(bp.pve_points) as avg_pve_points,
        SUM(b.turns) as total_turns,
        AVG(b.turns) as avg_turns_per_battle
    FROM battle_participants bp
    JOIN clans c ON bp.clan = c.name
    JOIN battles b ON bp.battle_id = b.id
    WHERE b.ts >= CURRENT_DATE - INTERVAL '30 days'
    AND bp.clan IS NOT NULL
    GROUP BY bp.clan, c.name, DATE(b.ts)
),
clan_features AS (
    SELECT 
        clan,
        clan_name,
        battle_date,
        members_count,
        battles_count,
        wins,
        losses,
        kills_monsters,
        kills_players,
        total_rank_points,
        total_pve_points,
        avg_rank_points,
        avg_pve_points,
        total_turns,
        avg_turns_per_battle,
        -- Вычисляем коэффициенты
        CASE 
            WHEN battles_count > 0 THEN wins::float / battles_count 
            ELSE 0 
        END as avg_survival_rate,
        CASE 
            WHEN total_turns > 0 THEN (kills_monsters + kills_players)::float / total_turns 
            ELSE 0 
        END as avg_kills_per_turn,
        -- Оценка активности клана
        CASE 
            WHEN battles_count > 0 AND total_turns > 0 THEN
                (battles_count::float / 20.0) * 0.4 +  -- Нормализованное количество боёв
                (wins::float / battles_count) * 0.3 +  -- Средний коэффициент выживания
                ((kills_monsters + kills_players)::float / total_turns) * 0.3  -- Средние убийства за ход
            ELSE 0
        END as clan_activity_score,
        -- Эффективность клана (бои на участника)
        CASE 
            WHEN members_count > 0 THEN battles_count::float / members_count 
            ELSE 0 
        END as battles_per_member
    FROM clan_daily_stats
)
SELECT 
        clan,
    clan_name,
    battle_date,
    members_count,
    battles_count,
    wins,
    losses,
    kills_monsters,
    kills_players,
    total_rank_points,
    total_pve_points,
    avg_rank_points,
    avg_pve_points,
    total_turns,
    avg_turns_per_battle,
    avg_survival_rate,
    avg_kills_per_turn,
    clan_activity_score,
    battles_per_member,
    -- Дополнительные метрики
    CASE 
        WHEN battles_count >= 20 THEN 'high_activity'
        WHEN battles_count >= 10 THEN 'medium_activity'
        WHEN battles_count >= 5 THEN 'low_activity'
        ELSE 'inactive'
    END as activity_level,
    -- Рейтинг клана по активности
    RANK() OVER (PARTITION BY battle_date ORDER BY clan_activity_score DESC) as daily_rank,
    -- Z-score для обнаружения аномалий
    CASE 
        WHEN battles_count > 0 THEN
            (battles_count - AVG(battles_count) OVER (PARTITION BY battle_date)) / 
            NULLIF(STDDEV(battles_count) OVER (PARTITION BY battle_date), 0)
        ELSE 0
    END as battles_z_score
FROM clan_features
ORDER BY battle_date DESC, clan_activity_score DESC;

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_daily_clan_features_clan_date 
ON daily_clan_features (clan, battle_date);

CREATE INDEX IF NOT EXISTS idx_daily_clan_features_activity 
ON daily_clan_features (clan_activity_score DESC);

CREATE INDEX IF NOT EXISTS idx_daily_clan_features_rank 
ON daily_clan_features (battle_date, daily_rank);

-- Комментарии
COMMENT ON VIEW daily_clan_features IS 'Ежедневные фичи кланов для аналитики';
COMMENT ON COLUMN daily_clan_features.clan_activity_score IS 'Комбинированная оценка активности клана (0-1)';
COMMENT ON COLUMN daily_clan_features.avg_survival_rate IS 'Средний коэффициент выживания участников клана';
COMMENT ON COLUMN daily_clan_features.avg_kills_per_turn IS 'Среднее количество убийств за ход по клану';
COMMENT ON COLUMN daily_clan_features.battles_per_member IS 'Количество боёв на участника клана';
COMMENT ON COLUMN daily_clan_features.daily_rank IS 'Рейтинг клана по активности за день';
