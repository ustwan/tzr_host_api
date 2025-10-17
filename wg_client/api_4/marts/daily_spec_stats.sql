-- Витрина: Ежедневная статистика по монстрам (баланс PvE)
-- Назначение: Анализ баланса PvE по монстрам и их подвидам
-- Частота обновления: Ежедневно

CREATE OR REPLACE VIEW daily_spec_stats AS
WITH monster_daily_stats AS (
    SELECT 
        bm.monster_id,
        mc.kind as monster_kind,
        mc.spec as monster_spec,
        DATE(b.ts) as battle_date,
        COUNT(DISTINCT bm.battle_id) as battles_count,
        SUM(bm.count) as total_monsters,
        AVG(bm.count) as avg_monsters_per_battle,
        MIN(bm.min_level) as min_level_seen,
        MAX(bm.max_level) as max_level_seen,
        AVG(bm.min_level) as avg_min_level,
        AVG(bm.max_level) as avg_max_level,
        -- Статистика по участникам боёв с этими монстрами
        COUNT(DISTINCT bp.player_id) as unique_players,
        SUM(CASE WHEN bp.survived = 1 THEN 1 ELSE 0 END) as player_wins,
        SUM(CASE WHEN bp.survived = 0 THEN 1 ELSE 0 END) as player_losses,
        SUM(bp.kills_monsters) as total_player_kills,
        AVG(bp.kills_monsters) as avg_kills_per_player,
        -- Статистика по луту
        SUM(bl.qty) as total_loot_quantity,
        COUNT(DISTINCT bl.battle_id) as battles_with_loot
    FROM battle_monsters bm
    JOIN monster_catalog mc ON bm.monster_id = mc.monster_id
    JOIN battles b ON bm.battle_id = b.id
    LEFT JOIN battle_participants bp ON b.id = bp.battle_id
    LEFT JOIN battle_loot bl ON b.id = bl.battle_id 
        AND bl.kind = 'monster_part' 
        AND bl.part_id IN (
            SELECT part_id FROM monster_part_names 
            WHERE name ILIKE '%' || mc.kind || '%' 
            OR name ILIKE '%' || COALESCE(mc.spec, '') || '%'
        )
    WHERE b.ts >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY bm.monster_id, mc.kind, mc.spec, DATE(b.ts)
),
monster_balance_analysis AS (
    SELECT 
        *,
        -- Коэффициент выживания игроков против монстров
        CASE 
            WHEN (player_wins + player_losses) > 0 THEN 
                player_wins::float / (player_wins + player_losses)
            ELSE 0
        END as player_survival_rate,
        -- Эффективность убийств монстров
        CASE 
            WHEN total_monsters > 0 THEN 
                total_player_kills::float / total_monsters
            ELSE 0
        END as kill_efficiency,
        -- Средний уровень монстров
        (avg_min_level + avg_max_level) / 2 as avg_monster_level,
        -- Разброс уровней
        (avg_max_level - avg_min_level) as level_range,
        -- Частота появления лута
        CASE 
            WHEN battles_count > 0 THEN 
                battles_with_loot::float / battles_count
            ELSE 0
        END as loot_frequency,
        -- Среднее количество лута за бой
        CASE 
            WHEN battles_count > 0 THEN 
                total_loot_quantity::float / battles_count
            ELSE 0
        END as avg_loot_per_battle
    FROM monster_daily_stats
),
monster_difficulty_scoring AS (
    SELECT 
        *,
        -- Оценка сложности монстра (0-1, где 1 = очень сложный)
        CASE 
            WHEN player_survival_rate < 0.3 THEN 1.0
            WHEN player_survival_rate < 0.5 THEN 0.8
            WHEN player_survival_rate < 0.7 THEN 0.6
            WHEN player_survival_rate < 0.9 THEN 0.4
            ELSE 0.2
        END as difficulty_score,
        -- Оценка награды (0-1, где 1 = очень выгодный)
        CASE 
            WHEN avg_loot_per_battle > 100 THEN 1.0
            WHEN avg_loot_per_battle > 50 THEN 0.8
            WHEN avg_loot_per_battle > 20 THEN 0.6
            WHEN avg_loot_per_battle > 10 THEN 0.4
            ELSE 0.2
        END as reward_score,
        -- Баланс сложности и награды
        CASE 
            WHEN difficulty_score > 0.8 AND reward_score < 0.4 THEN 'overpowered'
            WHEN difficulty_score < 0.4 AND reward_score > 0.8 THEN 'underpowered'
            WHEN ABS(difficulty_score - reward_score) < 0.2 THEN 'balanced'
            WHEN difficulty_score > reward_score THEN 'too_hard'
            ELSE 'too_easy'
        END as balance_status
    FROM monster_balance_analysis
)
SELECT 
    monster_id,
    monster_kind,
    monster_spec,
    battle_date,
    battles_count,
    total_monsters,
    avg_monsters_per_battle,
    min_level_seen,
    max_level_seen,
    avg_min_level,
    avg_max_level,
    avg_monster_level,
    level_range,
    unique_players,
    player_wins,
    player_losses,
    player_survival_rate,
    total_player_kills,
    avg_kills_per_player,
    kill_efficiency,
    total_loot_quantity,
    battles_with_loot,
    loot_frequency,
    avg_loot_per_battle,
    difficulty_score,
    reward_score,
    balance_status,
    -- Дополнительные метрики
    CASE 
        WHEN battles_count >= 20 THEN 'high_activity'
        WHEN battles_count >= 10 THEN 'medium_activity'
        WHEN battles_count >= 5 THEN 'low_activity'
        ELSE 'rare'
    END as activity_level,
    -- Рейтинг по сложности
    RANK() OVER (PARTITION BY battle_date ORDER BY difficulty_score DESC) as difficulty_rank,
    -- Рейтинг по награде
    RANK() OVER (PARTITION BY battle_date ORDER BY reward_score DESC) as reward_rank,
    -- Рейтинг по популярности
    RANK() OVER (PARTITION BY battle_date ORDER BY battles_count DESC) as popularity_rank
FROM monster_difficulty_scoring
ORDER BY battle_date DESC, difficulty_score DESC;

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_daily_spec_stats_monster_date 
ON daily_spec_stats (monster_id, battle_date);

CREATE INDEX IF NOT EXISTS idx_daily_spec_stats_balance 
ON daily_spec_stats (balance_status, battle_date);

CREATE INDEX IF NOT EXISTS idx_daily_spec_stats_difficulty 
ON daily_spec_stats (difficulty_score DESC, battle_date);

CREATE INDEX IF NOT EXISTS idx_daily_spec_stats_activity 
ON daily_spec_stats (activity_level, battle_date);

-- Комментарии
COMMENT ON VIEW daily_spec_stats IS 'Ежедневная статистика по монстрам для анализа баланса PvE';
COMMENT ON COLUMN daily_spec_stats.difficulty_score IS 'Оценка сложности монстра (0-1)';
COMMENT ON COLUMN daily_spec_stats.reward_score IS 'Оценка награды от монстра (0-1)';
COMMENT ON COLUMN daily_spec_stats.balance_status IS 'Статус баланса монстра';
COMMENT ON COLUMN daily_spec_stats.player_survival_rate IS 'Коэффициент выживания игроков против монстра';
COMMENT ON COLUMN daily_spec_stats.kill_efficiency IS 'Эффективность убийств монстров игроками';
COMMENT ON COLUMN daily_spec_stats.loot_frequency IS 'Частота появления лута от монстра';
