-- Витрина: Ежедневные сессии игроков для антибота
-- Назначение: Анализ паттернов активности игроков для обнаружения ботов
-- Частота обновления: Ежедневно

CREATE OR REPLACE VIEW daily_player_sessions AS
WITH player_sessions AS (
    SELECT 
        bp.player_id,
        p.login,
        DATE(b.ts) as session_date,
        b.ts as battle_timestamp,
        b.id as battle_id,
        bp.survived,
        bp.kills_monsters,
        bp.kills_players,
        b.turns,
        -- Вычисляем интервалы между боями
        LAG(b.ts) OVER (PARTITION BY bp.player_id, DATE(b.ts) ORDER BY b.ts) as prev_battle_time,
        -- Группируем сессии (если интервал > 2 часов, считаем новой сессией)
        CASE 
            WHEN LAG(b.ts) OVER (PARTITION BY bp.player_id, DATE(b.ts) ORDER BY b.ts) IS NULL THEN 1
            WHEN EXTRACT(EPOCH FROM (b.ts - LAG(b.ts) OVER (PARTITION BY bp.player_id, DATE(b.ts) ORDER BY b.ts))) > 7200 THEN 1
            ELSE 0
        END as is_new_session
    FROM battle_participants bp
    JOIN players p ON bp.player_id = p.id
    JOIN battles b ON bp.battle_id = b.id
    WHERE b.ts >= CURRENT_DATE - INTERVAL '30 days'
),
session_groups AS (
    SELECT 
        player_id,
        login,
        session_date,
        battle_timestamp,
        battle_id,
        survived,
        kills_monsters,
        kills_players,
        turns,
        -- Нумеруем сессии
        SUM(is_new_session) OVER (PARTITION BY player_id, session_date ORDER BY battle_timestamp) as session_number
    FROM player_sessions
),
session_stats AS (
    SELECT 
        player_id,
        login,
        session_date,
        session_number,
        COUNT(*) as battles_in_session,
        MIN(battle_timestamp) as session_start,
        MAX(battle_timestamp) as session_end,
        SUM(CASE WHEN survived = 1 THEN 1 ELSE 0 END) as session_wins,
        SUM(kills_monsters) as session_kills_monsters,
        SUM(kills_players) as session_kills_players,
        SUM(turns) as session_total_turns,
        AVG(turns) as avg_turns_per_battle
    FROM session_groups
    GROUP BY player_id, login, session_date, session_number
),
daily_session_features AS (
    SELECT 
        player_id,
        login,
        session_date,
        COUNT(DISTINCT session_number) as total_sessions,
        SUM(battles_in_session) as total_battles,
        SUM(session_wins) as total_wins,
        SUM(session_kills_monsters) as total_kills_monsters,
        SUM(session_kills_players) as total_kills_players,
        SUM(session_total_turns) as total_turns,
        -- Временные метрики
        MIN(session_start) as first_battle_time,
        MAX(session_end) as last_battle_time,
        EXTRACT(EPOCH FROM (MAX(session_end) - MIN(session_start))) as total_playtime_seconds,
        -- Средние метрики по сессиям
        AVG(battles_in_session) as avg_battles_per_session,
        AVG(session_wins::float / NULLIF(battles_in_session, 0)) as avg_session_survival_rate,
        AVG(session_kills_monsters + session_kills_players) as avg_kills_per_session,
        -- Анализ регулярности
        STDDEV(EXTRACT(EPOCH FROM (session_start - LAG(session_start) OVER (PARTITION BY player_id, session_date ORDER BY session_start)))) as session_interval_stddev,
        AVG(EXTRACT(EPOCH FROM (session_start - LAG(session_start) OVER (PARTITION BY player_id, session_date ORDER BY session_start)))) as avg_session_interval
    FROM session_stats
    GROUP BY player_id, login, session_date
)
SELECT 
    player_id,
    login,
    session_date,
    total_sessions,
    total_battles,
    total_wins,
    total_kills_monsters,
    total_kills_players,
    total_turns,
    first_battle_time,
    last_battle_time,
    total_playtime_seconds,
    avg_battles_per_session,
    avg_session_survival_rate,
    avg_kills_per_session,
    session_interval_stddev,
    avg_session_interval,
    -- Вычисляем подозрительные паттерны
    CASE 
        WHEN total_sessions > 10 THEN 'high_sessions'
        WHEN total_sessions > 5 THEN 'medium_sessions'
        WHEN total_sessions > 1 THEN 'low_sessions'
        ELSE 'single_session'
    END as session_activity_level,
    -- Регулярность сессий (низкая вариативность = подозрительно)
    CASE 
        WHEN session_interval_stddev IS NOT NULL AND avg_session_interval > 0 THEN
            session_interval_stddev / avg_session_interval
        ELSE NULL
    END as session_regularity_coefficient,
    -- Подозрение на бота
    CASE 
        WHEN total_sessions > 20 THEN 0.3  -- Слишком много сессий
        ELSE 0
    END + 
    CASE 
        WHEN session_regularity_coefficient IS NOT NULL AND session_regularity_coefficient < 0.1 THEN 0.4  -- Слишком регулярные интервалы
        ELSE 0
    END +
    CASE 
        WHEN avg_session_survival_rate > 0.95 THEN 0.2  -- Слишком высокий коэффициент выживания
        ELSE 0
    END +
    CASE 
        WHEN total_playtime_seconds > 86400 THEN 0.1  -- Играет больше 24 часов в день
        ELSE 0
    END as bot_suspicion_score
FROM daily_session_features
ORDER BY session_date DESC, bot_suspicion_score DESC;

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_daily_player_sessions_player_date 
ON daily_player_sessions (player_id, session_date);

CREATE INDEX IF NOT EXISTS idx_daily_player_sessions_suspicion 
ON daily_player_sessions (bot_suspicion_score DESC);

CREATE INDEX IF NOT EXISTS idx_daily_player_sessions_regularity 
ON daily_player_sessions (session_regularity_coefficient);

-- Комментарии
COMMENT ON VIEW daily_player_sessions IS 'Ежедневные сессии игроков для антибот анализа';
COMMENT ON COLUMN daily_player_sessions.session_regularity_coefficient IS 'Коэффициент регулярности сессий (низкий = подозрительно)';
COMMENT ON COLUMN daily_player_sessions.bot_suspicion_score IS 'Оценка подозрения на бота (0-1)';
COMMENT ON COLUMN daily_player_sessions.avg_session_survival_rate IS 'Средний коэффициент выживания в сессиях';
COMMENT ON COLUMN daily_player_sessions.total_playtime_seconds IS 'Общее время игры в секундах за день';
