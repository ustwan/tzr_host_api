-- Витрина: Ежедневный приток ресурсов
-- Назначение: Анализ экономики игры - приток ресурсов по дням
-- Частота обновления: Ежедневно

CREATE OR REPLACE VIEW daily_resource_inflow AS
WITH daily_resources AS (
    SELECT 
        bl.battle_ts as resource_date,
        bl.resource_id,
        rn.name as resource_name,
        SUM(bl.qty) as total_quantity,
        COUNT(DISTINCT bl.battle_id) as battles_with_resource,
        COUNT(DISTINCT bp.player_id) as unique_players,
        AVG(bl.qty) as avg_quantity_per_battle,
        MAX(bl.qty) as max_quantity_in_battle,
        MIN(bl.qty) as min_quantity_in_battle
    FROM battle_loot bl
    JOIN resource_names rn ON bl.resource_id = rn.resource_id
    JOIN battles b ON bl.battle_id = b.id
    LEFT JOIN battle_participants bp ON b.id = bp.battle_id
    WHERE bl.kind = 'resource'
    AND bl.battle_ts >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY bl.battle_ts, bl.resource_id, rn.name
),
resource_totals AS (
    SELECT 
        resource_date,
        SUM(total_quantity) as total_resources,
        COUNT(DISTINCT resource_id) as unique_resources,
        SUM(battles_with_resource) as total_battles_with_resources
    FROM daily_resources
    GROUP BY resource_date
),
resource_stats AS (
    SELECT 
        dr.*,
        rt.total_resources,
        rt.unique_resources,
        rt.total_battles_with_resources,
        -- Процент от общего притока ресурсов
        CASE 
            WHEN rt.total_resources > 0 THEN (dr.total_quantity::float / rt.total_resources) * 100
            ELSE 0
        END as resource_percentage,
        -- Процент боёв с этим ресурсом
        CASE 
            WHEN rt.total_battles_with_resources > 0 THEN (dr.battles_with_resource::float / rt.total_battles_with_resources) * 100
            ELSE 0
        END as battle_percentage,
        -- Среднее количество ресурса на игрока
        CASE 
            WHEN dr.unique_players > 0 THEN dr.total_quantity::float / dr.unique_players
            ELSE 0
        END as avg_quantity_per_player
    FROM daily_resources dr
    JOIN resource_totals rt ON dr.resource_date = rt.resource_date
),
resource_anomalies AS (
    SELECT 
        *,
        -- Z-score для обнаружения аномалий
        CASE 
            WHEN STDDEV(total_quantity) OVER (PARTITION BY resource_id ORDER BY resource_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) > 0 THEN
                (total_quantity - AVG(total_quantity) OVER (PARTITION BY resource_id ORDER BY resource_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)) /
                STDDEV(total_quantity) OVER (PARTITION BY resource_id ORDER BY resource_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
            ELSE 0
        END as z_score_7d,
        -- Тренд (рост/падение за последние 3 дня)
        CASE 
            WHEN LAG(total_quantity, 3) OVER (PARTITION BY resource_id ORDER BY resource_date) IS NOT NULL THEN
                (total_quantity - LAG(total_quantity, 3) OVER (PARTITION BY resource_id ORDER BY resource_date))::float /
                LAG(total_quantity, 3) OVER (PARTITION BY resource_id ORDER BY resource_date)
            ELSE 0
        END as trend_3d
    FROM resource_stats
)
SELECT 
    resource_date,
    resource_id,
    resource_name,
    total_quantity,
    battles_with_resource,
    unique_players,
    avg_quantity_per_battle,
    max_quantity_in_battle,
    min_quantity_in_battle,
    total_resources,
    unique_resources,
    total_battles_with_resources,
    resource_percentage,
    battle_percentage,
    avg_quantity_per_player,
    z_score_7d,
    trend_3d,
    -- Классификация аномалий
    CASE 
        WHEN ABS(z_score_7d) > 2 THEN 'high_anomaly'
        WHEN ABS(z_score_7d) > 1.5 THEN 'medium_anomaly'
        WHEN ABS(z_score_7d) > 1 THEN 'low_anomaly'
        ELSE 'normal'
    END as anomaly_level,
    -- Классификация трендов
    CASE 
        WHEN trend_3d > 0.5 THEN 'strong_growth'
        WHEN trend_3d > 0.2 THEN 'moderate_growth'
        WHEN trend_3d > -0.2 THEN 'stable'
        WHEN trend_3d > -0.5 THEN 'moderate_decline'
        ELSE 'strong_decline'
    END as trend_level,
    -- Рейтинг ресурса по количеству
    RANK() OVER (PARTITION BY resource_date ORDER BY total_quantity DESC) as daily_rank,
    -- Рейтинг ресурса по частоте появления
    RANK() OVER (PARTITION BY resource_date ORDER BY battles_with_resource DESC) as frequency_rank
FROM resource_anomalies
ORDER BY resource_date DESC, total_quantity DESC;

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_daily_resource_inflow_date 
ON daily_resource_inflow (resource_date);

CREATE INDEX IF NOT EXISTS idx_daily_resource_inflow_resource 
ON daily_resource_inflow (resource_id, resource_date);

CREATE INDEX IF NOT EXISTS idx_daily_resource_inflow_anomaly 
ON daily_resource_inflow (anomaly_level, resource_date);

CREATE INDEX IF NOT EXISTS idx_daily_resource_inflow_rank 
ON daily_resource_inflow (resource_date, daily_rank);

-- Комментарии
COMMENT ON VIEW daily_resource_inflow IS 'Ежедневный приток ресурсов для экономического анализа';
COMMENT ON COLUMN daily_resource_inflow.z_score_7d IS 'Z-score за 7 дней для обнаружения аномалий';
COMMENT ON COLUMN daily_resource_inflow.trend_3d IS 'Тренд изменения за 3 дня (-1 до +1)';
COMMENT ON COLUMN daily_resource_inflow.anomaly_level IS 'Уровень аномалии в притоке ресурса';
COMMENT ON COLUMN daily_resource_inflow.trend_level IS 'Уровень тренда изменения ресурса';
COMMENT ON COLUMN daily_resource_inflow.resource_percentage IS 'Процент от общего притока ресурсов за день';
COMMENT ON COLUMN daily_resource_inflow.battle_percentage IS 'Процент боёв с данным ресурсом за день';
