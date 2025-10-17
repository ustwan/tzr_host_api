-- Витрина: Скоринг антибота
-- Назначение: Анализ подозрительной активности игроков для обнаружения ботов
-- Частота обновления: Ежедневно

CREATE OR REPLACE VIEW bot_suspicion AS
WITH player_behavior_analysis AS (
    SELECT 
        bp.player_id,
        p.login,
        DATE(b.ts) as analysis_date,
        -- Основные метрики активности
        COUNT(b.id) as battles_count,
        SUM(CASE WHEN bp.survived = 1 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN bp.survived = 0 THEN 1 ELSE 0 END) as losses,
        SUM(bp.kills_monsters) as kills_monsters,
        SUM(bp.kills_players) as kills_players,
        SUM(b.turns) as total_turns,
        AVG(b.turns) as avg_turns_per_battle,
        -- Временные метрики
        MIN(b.ts) as first_battle_time,
        MAX(b.ts) as last_battle_time,
        EXTRACT(EPOCH FROM (MAX(b.ts) - MIN(b.ts))) as total_playtime_seconds,
        -- Интервалы между боями
        AVG(EXTRACT(EPOCH FROM (b.ts - LAG(b.ts) OVER (PARTITION BY bp.player_id, DATE(b.ts) ORDER BY b.ts)))) as avg_battle_interval,
        STDDEV(EXTRACT(EPOCH FROM (b.ts - LAG(b.ts) OVER (PARTITION BY bp.player_id, DATE(b.ts) ORDER BY b.ts)))) as battle_interval_stddev,
        -- Паттерны поведения
        COUNT(DISTINCT DATE(b.ts)) as active_days,
        COUNT(DISTINCT EXTRACT(HOUR FROM b.ts)) as active_hours,
        COUNT(DISTINCT b.battle_type) as battle_types_used,
        COUNT(DISTINCT b.loc_x, b.loc_y) as unique_locations
    FROM battle_participants bp
    JOIN players p ON bp.player_id = p.id
    JOIN battles b ON bp.battle_id = b.id
    WHERE b.ts >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY bp.player_id, p.login, DATE(b.ts)
),
suspicion_factors AS (
    SELECT 
        *,
        -- Коэффициент выживания
        CASE 
            WHEN battles_count > 0 THEN wins::float / battles_count 
            ELSE 0 
        END as survival_rate,
        -- Убийства за ход
        CASE 
            WHEN total_turns > 0 THEN (kills_monsters + kills_players)::float / total_turns 
            ELSE 0 
        END as kills_per_turn,
        -- Регулярность интервалов (низкая вариативность = подозрительно)
        CASE 
            WHEN battle_interval_stddev > 0 AND avg_battle_interval > 0 THEN
                battle_interval_stddev / avg_battle_interval
            ELSE NULL
        END as regularity_coefficient,
        -- Интенсивность игры (бои в час)
        CASE 
            WHEN total_playtime_seconds > 0 THEN battles_count::float / (total_playtime_seconds / 3600)
            ELSE 0
        END as battles_per_hour,
        -- Разнообразие активности
        CASE 
            WHEN battles_count > 0 THEN 
                (active_days::float / 7) * 0.3 +  -- Активность по дням
                (active_hours::float / 24) * 0.2 +  -- Активность по часам
                (battle_types_used::float / 4) * 0.3 +  -- Разнообразие типов боёв
                (unique_locations::float / 10) * 0.2  -- Разнообразие локаций
            ELSE 0
        END as activity_diversity
    FROM player_behavior_analysis
),
suspicion_scoring AS (
    SELECT 
        *,
        -- Факторы подозрения (0-1 каждый)
        CASE 
            WHEN battles_count > 100 THEN 1.0  -- Слишком много боёв за день
            WHEN battles_count > 50 THEN 0.8
            WHEN battles_count > 20 THEN 0.4
            ELSE 0
        END as high_activity_suspicion,
        
        CASE 
            WHEN survival_rate > 0.98 THEN 1.0  -- Слишком высокий коэффициент выживания
            WHEN survival_rate > 0.95 THEN 0.8
            WHEN survival_rate > 0.90 THEN 0.4
            ELSE 0
        END as high_survival_suspicion,
        
        CASE 
            WHEN kills_per_turn > 5 THEN 1.0  -- Слишком много убийств за ход
            WHEN kills_per_turn > 3 THEN 0.8
            WHEN kills_per_turn > 2 THEN 0.4
            ELSE 0
        END as high_kills_suspicion,
        
        CASE 
            WHEN regularity_coefficient IS NOT NULL AND regularity_coefficient < 0.1 THEN 1.0  -- Слишком регулярные интервалы
            WHEN regularity_coefficient IS NOT NULL AND regularity_coefficient < 0.2 THEN 0.8
            WHEN regularity_coefficient IS NOT NULL AND regularity_coefficient < 0.3 THEN 0.4
            ELSE 0
        END as regularity_suspicion,
        
        CASE 
            WHEN battles_per_hour > 20 THEN 1.0  -- Слишком интенсивная игра
            WHEN battles_per_hour > 15 THEN 0.8
            WHEN battles_per_hour > 10 THEN 0.4
            ELSE 0
        END as intensity_suspicion,
        
        CASE 
            WHEN activity_diversity < 0.2 THEN 1.0  -- Слишком низкое разнообразие
            WHEN activity_diversity < 0.4 THEN 0.8
            WHEN activity_diversity < 0.6 THEN 0.4
            ELSE 0
        END as diversity_suspicion,
        
        CASE 
            WHEN total_playtime_seconds > 86400 THEN 1.0  -- Играет больше 24 часов в день
            WHEN total_playtime_seconds > 43200 THEN 0.8  -- Играет больше 12 часов в день
            WHEN total_playtime_seconds > 21600 THEN 0.4  -- Играет больше 6 часов в день
            ELSE 0
        END as excessive_playtime_suspicion
    FROM suspicion_factors
),
final_suspicion_scores AS (
    SELECT 
        *,
        -- Общий скоринг подозрения (взвешенная сумма)
        (high_activity_suspicion * 0.2 +
         high_survival_suspicion * 0.2 +
         high_kills_suspicion * 0.15 +
         regularity_suspicion * 0.2 +
         intensity_suspicion * 0.1 +
         diversity_suspicion * 0.1 +
         excessive_playtime_suspicion * 0.05) as total_suspicion_score,
        
        -- Количество сработавших факторов
        (CASE WHEN high_activity_suspicion > 0.5 THEN 1 ELSE 0 END +
         CASE WHEN high_survival_suspicion > 0.5 THEN 1 ELSE 0 END +
         CASE WHEN high_kills_suspicion > 0.5 THEN 1 ELSE 0 END +
         CASE WHEN regularity_suspicion > 0.5 THEN 1 ELSE 0 END +
         CASE WHEN intensity_suspicion > 0.5 THEN 1 ELSE 0 END +
         CASE WHEN diversity_suspicion > 0.5 THEN 1 ELSE 0 END +
         CASE WHEN excessive_playtime_suspicion > 0.5 THEN 1 ELSE 0 END) as triggered_factors_count
    FROM suspicion_scoring
)
SELECT 
    player_id,
    login,
    analysis_date,
    battles_count,
    wins,
    losses,
    survival_rate,
    kills_monsters,
    kills_players,
    kills_per_turn,
    total_turns,
    avg_turns_per_battle,
    total_playtime_seconds,
    battles_per_hour,
    activity_diversity,
    regularity_coefficient,
    -- Факторы подозрения
    high_activity_suspicion,
    high_survival_suspicion,
    high_kills_suspicion,
    regularity_suspicion,
    intensity_suspicion,
    diversity_suspicion,
    excessive_playtime_suspicion,
    -- Итоговые оценки
    total_suspicion_score,
    triggered_factors_count,
    -- Классификация
    CASE 
        WHEN total_suspicion_score > 0.8 THEN 'high_risk'
        WHEN total_suspicion_score > 0.6 THEN 'medium_risk'
        WHEN total_suspicion_score > 0.4 THEN 'low_risk'
        ELSE 'normal'
    END as risk_level,
    -- Рекомендации
    CASE 
        WHEN total_suspicion_score > 0.8 THEN 'Immediate investigation required'
        WHEN total_suspicion_score > 0.6 THEN 'Monitor closely and consider restrictions'
        WHEN total_suspicion_score > 0.4 THEN 'Review behavior patterns'
        WHEN total_suspicion_score > 0.2 THEN 'Note unusual activity'
        ELSE 'Normal player behavior'
    END as recommendation,
    -- Рейтинг подозрения
    RANK() OVER (PARTITION BY analysis_date ORDER BY total_suspicion_score DESC) as suspicion_rank
FROM final_suspicion_scores
WHERE battles_count >= 5  -- Только игроки с достаточной активностью
ORDER BY analysis_date DESC, total_suspicion_score DESC;

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_bot_suspicion_player_date 
ON bot_suspicion (player_id, analysis_date);

CREATE INDEX IF NOT EXISTS idx_bot_suspicion_score 
ON bot_suspicion (total_suspicion_score DESC);

CREATE INDEX IF NOT EXISTS idx_bot_suspicion_risk 
ON bot_suspicion (risk_level, analysis_date);

CREATE INDEX IF NOT EXISTS idx_bot_suspicion_rank 
ON bot_suspicion (analysis_date, suspicion_rank);

-- Комментарии
COMMENT ON VIEW bot_suspicion IS 'Скоринг антибота для обнаружения подозрительной активности игроков';
COMMENT ON COLUMN bot_suspicion.total_suspicion_score IS 'Общий скоринг подозрения (0-1)';
COMMENT ON COLUMN bot_suspicion.triggered_factors_count IS 'Количество сработавших факторов подозрения';
COMMENT ON COLUMN bot_suspicion.risk_level IS 'Уровень риска (normal/low/medium/high)';
COMMENT ON COLUMN bot_suspicion.regularity_coefficient IS 'Коэффициент регулярности интервалов (низкий = подозрительно)';
COMMENT ON COLUMN bot_suspicion.activity_diversity IS 'Разнообразие активности игрока (0-1)';
COMMENT ON COLUMN bot_suspicion.recommendation IS 'Рекомендация по действиям';
