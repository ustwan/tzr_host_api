-- V5__parser_v2.sql — Расширение схемы под новый парсер example/parser
-- Добавляет поля в battles, battle_participants; уточняет battle_monsters, battle_loot; индексы

BEGIN;

-- battles: расширенные метаданные и карта
ALTER TABLE IF EXISTS battles
  ADD COLUMN IF NOT EXISTS start_ts_unix BIGINT,
  ADD COLUMN IF NOT EXISTS battle_type TEXT,
  ADD COLUMN IF NOT EXISTS loc_x INT,
  ADD COLUMN IF NOT EXISTS loc_y INT,
  ADD COLUMN IF NOT EXISTS map_patch JSONB,
  ADD COLUMN IF NOT EXISTS size_bytes BIGINT,
  ADD COLUMN IF NOT EXISTS sha256 TEXT,
  ADD COLUMN IF NOT EXISTS storage_key TEXT,
  ADD COLUMN IF NOT EXISTS compressed BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS turns INT,
  ADD COLUMN IF NOT EXISTS players_cnt INT,
  ADD COLUMN IF NOT EXISTS monsters_cnt INT,
  ADD COLUMN IF NOT EXISTS entities_cnt INT;

-- participants: новые поля статусов, урона и лута
ALTER TABLE IF EXISTS battle_participants
  ADD COLUMN IF NOT EXISTS survived SMALLINT,
  ADD COLUMN IF NOT EXISTS intervened JSONB,
  ADD COLUMN IF NOT EXISTS kills JSONB,
  ADD COLUMN IF NOT EXISTS damage_total JSONB,
  ADD COLUMN IF NOT EXISTS loot JSONB;

-- monsters: агрегаты от нового парсера
ALTER TABLE battle_monsters
  ADD COLUMN IF NOT EXISTS side SMALLINT,
  ADD COLUMN IF NOT EXISTS min_level INT,
  ADD COLUMN IF NOT EXISTS max_level INT;

-- Индексы
CREATE INDEX IF NOT EXISTS idx_battles_ts ON battles (ts);
CREATE INDEX IF NOT EXISTS idx_battles_players_cnt ON battles (players_cnt);
CREATE INDEX IF NOT EXISTS idx_battles_loc ON battles (loc_x, loc_y);
CREATE INDEX IF NOT EXISTS idx_battles_sha256 ON battles (sha256);
CREATE INDEX IF NOT EXISTS idx_battles_map_patch_gin ON battles USING GIN (map_patch);

CREATE INDEX IF NOT EXISTS idx_participants_battle_id ON battle_participants (battle_id);
CREATE INDEX IF NOT EXISTS idx_participants_damage_total_gin ON battle_participants USING GIN (damage_total);
CREATE INDEX IF NOT EXISTS idx_participants_intervened_gin ON battle_participants USING GIN (intervened);

CREATE INDEX IF NOT EXISTS idx_monsters_battle_id ON battle_monsters (battle_id);
-- battle_monsters хранит ссылки на monster_catalog; индексы по kind/spec не применимы здесь

-- Схема battle_loot остаётся по V3; индексы управляются в V3

COMMIT;


