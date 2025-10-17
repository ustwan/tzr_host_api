-- V6: Кэш профессий игроков
-- Цель: Хранить последнюю известную профессию для каждого игрока

CREATE TABLE IF NOT EXISTS players_profession_cache (
    login TEXT PRIMARY KEY,
    profession SMALLINT NOT NULL,
    profession_name TEXT NOT NULL,
    last_seen_battle_id BIGINT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    battles_count INTEGER DEFAULT 1
);

-- Индекс для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_players_prof_cache_profession ON players_profession_cache(profession);
CREATE INDEX IF NOT EXISTS idx_players_prof_cache_updated ON players_profession_cache(updated_at DESC);

-- Функция для обновления кэша
CREATE OR REPLACE FUNCTION update_profession_cache(
    p_login TEXT,
    p_profession SMALLINT,
    p_profession_name TEXT,
    p_battle_id BIGINT
) RETURNS VOID AS $$
BEGIN
    INSERT INTO players_profession_cache (login, profession, profession_name, last_seen_battle_id, battles_count)
    VALUES (p_login, p_profession, p_profession_name, p_battle_id, 1)
    ON CONFLICT (login) DO UPDATE SET
        profession = CASE 
            WHEN EXCLUDED.profession != 0 THEN EXCLUDED.profession 
            ELSE players_profession_cache.profession 
        END,
        profession_name = CASE 
            WHEN EXCLUDED.profession != 0 THEN EXCLUDED.profession_name 
            ELSE players_profession_cache.profession_name 
        END,
        last_seen_battle_id = EXCLUDED.last_seen_battle_id,
        updated_at = CURRENT_TIMESTAMP,
        battles_count = players_profession_cache.battles_count + 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE players_profession_cache IS 'Кэш последней известной профессии для каждого игрока';
COMMENT ON FUNCTION update_profession_cache IS 'Обновляет profession только если новое значение != 0';


