-- Витрина: Ежедневные фичи игроков
-- Назначение: Агрегированные метрики игроков за день для аналитики и антибота
-- Частота обновления: Ежедневно

CREATE OR REPLACE VIEW daily_player_features AS
WITH player_daily_stats AS (
    SELECT 
        bp.player_id,
        p.login,
        DATE(b.ts) as battle_date,
        COUNT(b.id) as battles_count,
        SUM(CASE WHEN bp.survived = 1 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN bp.survived = 0 THEN 1 ELSE 0 END) as losses,
        SUM(bp.kills_monsters) as kills_monsters,
        SUM(bp.kills_players) as kills_players,
        SUM(bp.rank_points) as rank_points_total,
        SUM(bp.pve_points) as pve_points_total,
        AVG(bp.rank_points) as rank_points_avg,
        AVG(bp.pve_points) as pve_points_avg,
        SUM(b.turns) as total_turns,
        AVG(b.turns) as avg_turns_per_battle
    FROM battle_participants bp
    JOIN players p ON bp.player_id = p.id
    JOIN battles b ON bp.battle_id = b.id
    WHERE b.ts >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY bp.player_id, p.login, DATE(b.ts)
),
player_features AS (
    SELECT 
        player_id,
        login,
        battle_date,
        battles_count,
        wins,
        losses,
        kills_monsters,
        kills_players,
        rank_points_total,
        pve_points_total,
        rank_points_avg,
        pve_points_avg,
        total_turns,
        avg_turns_per_battle,
        -- Вычисляем коэффициенты
        CASE 
            WHEN battles_count > 0 THEN wins::float / battles_count 
            ELSE 0 
        END as survival_rate,
        CASE 
            WHEN total_turns > 0 THEN (kills_monsters + kills_players)::float / total_turns 
            ELSE 0 
        END as kills_per_turn,
        -- Оценка активности (комбинированная метрика)
        CASE 
            WHEN battles_count > 0 AND total_turns > 0 THEN
                (battles_count::float / 10.0) * 0.3 +  -- Нормализованное количество боёв
                (wins::float / battles_count) * 0.3 +  -- Коэффициент выживания
                ((kills_monsters + kills_players)::float / total_turns) * 0.4  -- Убийства за ход
            ELSE 0
        END as activity_score
    FROM player_daily_stats
)
SELECT 
    player_id,
    login,
    battle_date,
    battles_count,
    wins,
    losses,
    kills_monsters,
    kills_players,
    rank_points_total,
    pve_points_total,
    rank_points_avg,
    pve_points_avg,
    total_turns,
    avg_turns_per_battle,
    survival_rate,
    kills_per_turn,
    activity_score,
    -- Дополнительные метрики
    CASE 
        WHEN battles_count >= 10 THEN 'high_activity'
        WHEN battles_count >= 5 THEN 'medium_activity'
        WHEN battles_count >= 1 THEN 'low_activity'
        ELSE 'inactive'
    END as activity_level,
    -- Z-score для обнаружения аномалий
    CASE 
        WHEN battles_count > 0 THEN
            (battles_count - AVG(battles_count) OVER (PARTITION BY battle_date)) / 
            NULLIF(STDDEV(battles_count) OVER (PARTITION BY battle_date), 0)
        ELSE 0
    END as battles_z_score
FROM player_features
ORDER BY battle_date DESC, activity_score DESC;

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_daily_player_features_player_date 
ON daily_player_features (player_id, battle_date);

CREATE INDEX IF NOT EXISTS idx_daily_player_features_activity 
ON daily_player_features (activity_score DESC);

CREATE INDEX IF NOT EXISTS idx_daily_player_features_survival 
ON daily_player_features (survival_rate DESC);

-- Комментарии
COMMENT ON VIEW daily_player_features IS 'Ежедневные фичи игроков для аналитики и антибота';
COMMENT ON COLUMN daily_player_features.activity_score IS 'Комбинированная оценка активности игрока (0-1)';
COMMENT ON COLUMN daily_player_features.survival_rate IS 'Коэффициент выживания (0-1)';
COMMENT ON COLUMN daily_player_features.kills_per_turn IS 'Среднее количество убийств за ход';
COMMENT ON COLUMN daily_player_features.battles_z_score IS 'Z-score для обнаружения аномальной активности';
