-- Полная миграция для API 4 с новым парсером
-- Создание всех необходимых таблиц

-- Таблица игроков
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    login TEXT UNIQUE NOT NULL
);

-- Таблица кланов
CREATE TABLE IF NOT EXISTS clans (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Таблица ресурсов
CREATE TABLE IF NOT EXISTS resource_names (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Таблица частей монстров
CREATE TABLE IF NOT EXISTS monster_part_names (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Таблица каталога монстров
CREATE TABLE IF NOT EXISTS monster_catalog (
    id SERIAL PRIMARY KEY,
    kind TEXT NOT NULL,
    spec TEXT,
    slug TEXT UNIQUE NOT NULL
);

-- Создание уникального индекса для kind + spec
CREATE UNIQUE INDEX IF NOT EXISTS monster_catalog_uq_kind_spec 
ON monster_catalog (kind, COALESCE(spec, ''));

-- Таблица боев
CREATE TABLE IF NOT EXISTS battles (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ,
    size_bytes INTEGER,
    sha256 TEXT,
    storage_key TEXT,
    compressed BOOLEAN DEFAULT FALSE,
    turns INTEGER,
    battle_type TEXT,
    loc_x INTEGER,
    loc_y INTEGER,
    start_ts TIMESTAMPTZ,
    players_cnt INTEGER,
    monsters_cnt INTEGER,
    entities_cnt INTEGER,
    map_patch JSONB,
    data JSONB
);

-- Таблица участников боев
CREATE TABLE IF NOT EXISTS battle_participants (
    id BIGSERIAL PRIMARY KEY,
    battle_id BIGINT REFERENCES battles(id) ON DELETE CASCADE,
    player_id INTEGER REFERENCES players(id),
    login TEXT NOT NULL,
    clan TEXT,
    side TEXT,
    survived BOOLEAN DEFAULT FALSE,
    rank_points INTEGER DEFAULT 0,
    pve_points INTEGER DEFAULT 0,
    profession TEXT,
    level INTEGER,
    gender TEXT,
    intervened JSONB,
    kills JSONB,
    kills_players INTEGER DEFAULT 0,
    kills_monsters INTEGER DEFAULT 0,
    damage_total JSONB,
    loot JSONB
);

-- Таблица монстров в боях
CREATE TABLE IF NOT EXISTS battle_monsters (
    id BIGSERIAL PRIMARY KEY,
    battle_id BIGINT REFERENCES battles(id) ON DELETE CASCADE,
    monster_id INTEGER REFERENCES monster_catalog(id),
    kind TEXT,
    spec TEXT,
    side TEXT,
    count INTEGER,
    min_level INTEGER,
    max_level INTEGER
);

-- Таблица лута в боях
CREATE TABLE IF NOT EXISTS battle_loot (
    id BIGSERIAL PRIMARY KEY,
    battle_id BIGINT REFERENCES battles(id) ON DELETE CASCADE,
    battle_ts DATE NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('resource', 'monster_part', 'other')),
    resource_id SMALLINT REFERENCES resource_names(id),
    part_id SMALLINT REFERENCES monster_part_names(id),
    item_id INTEGER,
    item_name TEXT,
    qty INTEGER NOT NULL CHECK (qty > 0)
);

-- Создание индексов для производительности
CREATE INDEX IF NOT EXISTS idx_battles_ts ON battles(ts);
CREATE INDEX IF NOT EXISTS idx_battles_battle_type ON battles(battle_type);
CREATE INDEX IF NOT EXISTS idx_battles_location ON battles(loc_x, loc_y);
CREATE INDEX IF NOT EXISTS idx_battles_map_patch ON battles USING GIN(map_patch);

CREATE INDEX IF NOT EXISTS idx_battle_participants_battle_id ON battle_participants(battle_id);
CREATE INDEX IF NOT EXISTS idx_battle_participants_player_id ON battle_participants(player_id);
CREATE INDEX IF NOT EXISTS idx_battle_participants_login ON battle_participants(login);
CREATE INDEX IF NOT EXISTS idx_battle_participants_intervened ON battle_participants USING GIN(intervened);
CREATE INDEX IF NOT EXISTS idx_battle_participants_kills ON battle_participants USING GIN(kills);
CREATE INDEX IF NOT EXISTS idx_battle_participants_damage_total ON battle_participants USING GIN(damage_total);
CREATE INDEX IF NOT EXISTS idx_battle_participants_loot ON battle_participants USING GIN(loot);

CREATE INDEX IF NOT EXISTS idx_battle_monsters_battle_id ON battle_monsters(battle_id);
CREATE INDEX IF NOT EXISTS idx_battle_monsters_monster_id ON battle_monsters(monster_id);

CREATE INDEX IF NOT EXISTS idx_battle_loot_battle_id ON battle_loot(battle_id);
CREATE INDEX IF NOT EXISTS idx_battle_loot_battle_ts ON battle_loot(battle_ts);
CREATE INDEX IF NOT EXISTS idx_battle_loot_kind ON battle_loot(kind);

-- Функция для получения или создания игрока
CREATE OR REPLACE FUNCTION get_or_create_player(player_login TEXT)
RETURNS INTEGER AS $$
DECLARE
  v_player_id INTEGER;
BEGIN
  -- Пытаемся найти существующего игрока
  SELECT p.id INTO v_player_id
  FROM players p
  WHERE p.login = player_login;
  
  -- Если не найден, создаём нового
  IF v_player_id IS NULL THEN
    INSERT INTO players (login) VALUES (player_login) RETURNING id INTO v_player_id;
  END IF;
  
  RETURN v_player_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения или создания клана
CREATE OR REPLACE FUNCTION get_or_create_clan(clan_name TEXT)
RETURNS INTEGER AS $$
DECLARE
  v_clan_id INTEGER;
BEGIN
  -- Пытаемся найти существующий клан
  SELECT c.id INTO v_clan_id
  FROM clans c
  WHERE c.name = clan_name;
  
  -- Если не найден, создаём новый
  IF v_clan_id IS NULL THEN
    INSERT INTO clans (name) VALUES (clan_name) RETURNING id INTO v_clan_id;
  END IF;
  
  RETURN v_clan_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения или создания ресурса
CREATE OR REPLACE FUNCTION get_or_create_resource(resource_name TEXT)
RETURNS INTEGER AS $$
DECLARE
  v_resource_id INTEGER;
BEGIN
  -- Пытаемся найти существующий ресурс
  SELECT r.id INTO v_resource_id
  FROM resource_names r
  WHERE r.name = resource_name;
  
  -- Если не найден, создаём новый
  IF v_resource_id IS NULL THEN
    INSERT INTO resource_names (name) VALUES (resource_name) RETURNING id INTO v_resource_id;
  END IF;
  
  RETURN v_resource_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения или создания части монстра
CREATE OR REPLACE FUNCTION get_or_create_monster_part(part_name TEXT)
RETURNS INTEGER AS $$
DECLARE
  v_part_id INTEGER;
BEGIN
  -- Пытаемся найти существующую часть
  SELECT p.id INTO v_part_id
  FROM monster_part_names p
  WHERE p.name = part_name;
  
  -- Если не найдена, создаём новую
  IF v_part_id IS NULL THEN
    INSERT INTO monster_part_names (name) VALUES (part_name) RETURNING id INTO v_part_id;
  END IF;
  
  RETURN v_part_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения или создания монстра
CREATE OR REPLACE FUNCTION get_or_create_monster(monster_kind TEXT, monster_spec TEXT DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
  v_monster_id INTEGER;
BEGIN
  INSERT INTO monster_catalog (kind, spec, slug)
  VALUES (
    monster_kind,
    monster_spec,
    LOWER(monster_kind || CASE WHEN monster_spec IS NOT NULL THEN '|' || monster_spec ELSE '' END)
  )
  ON CONFLICT (kind, COALESCE(spec, ''))
  DO UPDATE SET spec = EXCLUDED.spec
  RETURNING id INTO v_monster_id;

  RETURN v_monster_id;
END;
$$ LANGUAGE plpgsql;

-- Таблица для XML Sync логирования (для параллельной загрузки логов)
CREATE TABLE IF NOT EXISTS xml_sync_log (
    battle_id INTEGER PRIMARY KEY,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL,  -- success, failed, response_timeout
    error_message TEXT,
    file_path TEXT,
    size_bytes INTEGER
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_xml_sync_log_status ON xml_sync_log(status);
CREATE INDEX IF NOT EXISTS idx_xml_sync_log_requested_at ON xml_sync_log(requested_at DESC);
