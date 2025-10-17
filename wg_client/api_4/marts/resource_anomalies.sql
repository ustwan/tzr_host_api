-- Витрина: Аномалии в экономике ресурсов
-- Назначение: Обнаружение аномальных паттернов в притоке ресурсов
-- Частота обновления: Ежедневно

CREATE OR REPLACE VIEW resource_anomalies AS
WITH resource_daily_stats AS (
    SELECT 
        bl.resource_id,
        rn.name as resource_name,
        bl.battle_ts as resource_date,
        SUM(bl.qty) as daily_quantity,
        COUNT(DISTINCT bl.battle_id) as battles_count,
        COUNT(DISTINCT bp.player_id) as players_count,
        AVG(bl.qty) as avg_quantity_per_battle
    FROM battle_loot bl
    JOIN resource_names rn ON bl.resource_id = rn.resource_id
    JOIN battles b ON bl.battle_id = b.id
    LEFT JOIN battle_participants bp ON b.id = bp.battle_id
    WHERE bl.kind = 'resource'
    AND bl.battle_ts >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY bl.resource_id, rn.name, bl.battle_ts
),
resource_rolling_stats AS (
    SELECT 
        *,
        -- Скользящие средние и стандартные отклонения за 7 дней
        AVG(daily_quantity) OVER (
            PARTITION BY resource_id 
            ORDER BY resource_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) as mean_7d,
        STDDEV(daily_quantity) OVER (
            PARTITION BY resource_id 
            ORDER BY resource_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) as stddev_7d,
        -- Скользящие средние и стандартные отклонения за 14 дней
        AVG(daily_quantity) OVER (
            PARTITION BY resource_id 
            ORDER BY resource_date 
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) as mean_14d,
        STDDEV(daily_quantity) OVER (
            PARTITION BY resource_id 
            ORDER BY resource_date 
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) as stddev_14d,
        -- Предыдущие значения для трендов
        LAG(daily_quantity, 1) OVER (PARTITION BY resource_id ORDER BY resource_date) as prev_day,
        LAG(daily_quantity, 7) OVER (PARTITION BY resource_id ORDER BY resource_date) as prev_week,
        LAG(daily_quantity, 14) OVER (PARTITION BY resource_id ORDER BY resource_date) as prev_2weeks
    FROM resource_daily_stats
),
anomaly_detection AS (
    SELECT 
        *,
        -- Z-score за 7 дней
        CASE 
            WHEN stddev_7d > 0 THEN (daily_quantity - mean_7d) / stddev_7d
            ELSE 0
        END as z_score_7d,
        -- Z-score за 14 дней
        CASE 
            WHEN stddev_14d > 0 THEN (daily_quantity - mean_14d) / stddev_14d
            ELSE 0
        END as z_score_14d,
        -- Изменение относительно предыдущего дня
        CASE 
            WHEN prev_day > 0 THEN (daily_quantity - prev_day)::float / prev_day
            ELSE 0
        END as day_change_pct,
        -- Изменение относительно предыдущей недели
        CASE 
            WHEN prev_week > 0 THEN (daily_quantity - prev_week)::float / prev_week
            ELSE 0
        END as week_change_pct,
        -- Изменение относительно двух недель назад
        CASE 
            WHEN prev_2weeks > 0 THEN (daily_quantity - prev_2weeks)::float / prev_2weeks
            ELSE 0
        END as biweek_change_pct
    FROM resource_rolling_stats
),
anomaly_classification AS (
    SELECT 
        *,
        -- Классификация аномалий по Z-score
        CASE 
            WHEN ABS(z_score_7d) > 3 THEN 'extreme_anomaly'
            WHEN ABS(z_score_7d) > 2.5 THEN 'severe_anomaly'
            WHEN ABS(z_score_7d) > 2 THEN 'high_anomaly'
            WHEN ABS(z_score_7d) > 1.5 THEN 'medium_anomaly'
            WHEN ABS(z_score_7d) > 1 THEN 'low_anomaly'
            ELSE 'normal'
        END as anomaly_level_7d,
        CASE 
            WHEN ABS(z_score_14d) > 3 THEN 'extreme_anomaly'
            WHEN ABS(z_score_14d) > 2.5 THEN 'severe_anomaly'
            WHEN ABS(z_score_14d) > 2 THEN 'high_anomaly'
            WHEN ABS(z_score_14d) > 1.5 THEN 'medium_anomaly'
            WHEN ABS(z_score_14d) > 1 THEN 'low_anomaly'
            ELSE 'normal'
        END as anomaly_level_14d,
        -- Классификация изменений
        CASE 
            WHEN day_change_pct > 2 THEN 'massive_increase'
            WHEN day_change_pct > 1 THEN 'large_increase'
            WHEN day_change_pct > 0.5 THEN 'moderate_increase'
            WHEN day_change_pct > 0.1 THEN 'small_increase'
            WHEN day_change_pct > -0.1 THEN 'stable'
            WHEN day_change_pct > -0.5 THEN 'small_decrease'
            WHEN day_change_pct > -1 THEN 'moderate_decrease'
            WHEN day_change_pct > -2 THEN 'large_decrease'
            ELSE 'massive_decrease'
        END as day_change_level,
        -- Комбинированная оценка аномальности
        CASE 
            WHEN ABS(z_score_7d) > 2.5 OR ABS(z_score_14d) > 2.5 THEN 1.0
            WHEN ABS(z_score_7d) > 2 OR ABS(z_score_14d) > 2 THEN 0.8
            WHEN ABS(z_score_7d) > 1.5 OR ABS(z_score_14d) > 1.5 THEN 0.6
            WHEN ABS(z_score_7d) > 1 OR ABS(z_score_14d) > 1 THEN 0.4
            WHEN ABS(day_change_pct) > 1 THEN 0.3
            WHEN ABS(day_change_pct) > 0.5 THEN 0.2
            ELSE 0.0
        END as anomaly_score
    FROM anomaly_detection
)
SELECT 
    resource_id,
    resource_name,
    resource_date,
    daily_quantity,
    battles_count,
    players_count,
    avg_quantity_per_battle,
    mean_7d,
    stddev_7d,
    mean_14d,
    stddev_14d,
    z_score_7d,
    z_score_14d,
    day_change_pct,
    week_change_pct,
    biweek_change_pct,
    anomaly_level_7d,
    anomaly_level_14d,
    day_change_level,
    anomaly_score,
    -- Дополнительные метрики
    CASE 
        WHEN anomaly_score > 0.8 THEN 'critical'
        WHEN anomaly_score > 0.6 THEN 'high'
        WHEN anomaly_score > 0.4 THEN 'medium'
        WHEN anomaly_score > 0.2 THEN 'low'
        ELSE 'normal'
    END as overall_anomaly_level,
    -- Рекомендации
    CASE 
        WHEN anomaly_score > 0.8 THEN 'Investigate immediately - possible exploit or bug'
        WHEN anomaly_score > 0.6 THEN 'Monitor closely - unusual pattern detected'
        WHEN anomaly_score > 0.4 THEN 'Review trend - may indicate balance issue'
        WHEN anomaly_score > 0.2 THEN 'Note change - within normal variation'
        ELSE 'Normal activity'
    END as recommendation
FROM anomaly_classification
WHERE resource_date >= CURRENT_DATE - INTERVAL '7 days'  -- Показываем только последние 7 дней
ORDER BY anomaly_score DESC, resource_date DESC;

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_resource_anomalies_date 
ON resource_anomalies (resource_date);

CREATE INDEX IF NOT EXISTS idx_resource_anomalies_score 
ON resource_anomalies (anomaly_score DESC);

CREATE INDEX IF NOT EXISTS idx_resource_anomalies_level 
ON resource_anomalies (overall_anomaly_level, resource_date);

CREATE INDEX IF NOT EXISTS idx_resource_anomalies_resource 
ON resource_anomalies (resource_id, resource_date);

-- Комментарии
COMMENT ON VIEW resource_anomalies IS 'Аномалии в экономике ресурсов для обнаружения эксплойтов и проблем баланса';
COMMENT ON COLUMN resource_anomalies.anomaly_score IS 'Комбинированная оценка аномальности (0-1)';
COMMENT ON COLUMN resource_anomalies.z_score_7d IS 'Z-score за 7 дней для обнаружения краткосрочных аномалий';
COMMENT ON COLUMN resource_anomalies.z_score_14d IS 'Z-score за 14 дней для обнаружения долгосрочных аномалий';
COMMENT ON COLUMN resource_anomalies.day_change_pct IS 'Изменение относительно предыдущего дня в процентах';
COMMENT ON COLUMN resource_anomalies.overall_anomaly_level IS 'Общий уровень аномальности';
COMMENT ON COLUMN resource_anomalies.recommendation IS 'Рекомендация по действиям';
