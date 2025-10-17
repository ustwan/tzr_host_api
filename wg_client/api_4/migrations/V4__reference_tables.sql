-- V4: Создание справочных таблиц для нормализации данных
-- Справочники для игроков, кланов, монстров, ресурсов

-- ===== СПРАВОЧНИКИ =====

-- Справочник игроков
CREATE TABLE players (
  player_id  SERIAL PRIMARY KEY,
  login      TEXT UNIQUE NOT NULL,
  slug       TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Индексы для players
CREATE INDEX players_login_idx ON players(login);
CREATE INDEX players_slug_idx ON players(slug);

-- Справочник кланов
CREATE TABLE clans (
  clan_id SERIAL PRIMARY KEY,
  name    TEXT UNIQUE NOT NULL,
  slug    TEXT UNIQUE
);

-- Индексы для clans
CREATE INDEX clans_name_idx ON clans(name);
CREATE INDEX clans_slug_idx ON clans(slug);

-- Каталог монстров
CREATE TABLE monster_catalog (
  monster_id SERIAL PRIMARY KEY,
  kind       TEXT NOT NULL,
  spec       TEXT,
  slug       TEXT UNIQUE
);

-- Уникальность по (kind, COALESCE(spec,''))
CREATE UNIQUE INDEX monster_catalog_uq_kind_spec
  ON monster_catalog (kind, COALESCE(spec,''));

-- Индексы для monster_catalog
CREATE INDEX monster_catalog_kind_idx ON monster_catalog(kind);
CREATE INDEX monster_catalog_slug_idx ON monster_catalog(slug);

-- Справочник имён ресурсов
CREATE TABLE resource_names (
  resource_id SMALLSERIAL PRIMARY KEY,
  name        TEXT UNIQUE NOT NULL,
  slug        TEXT UNIQUE
);

-- Индексы для resource_names
CREATE INDEX resource_names_name_idx ON resource_names(name);
CREATE INDEX resource_names_slug_idx ON resource_names(slug);

-- Справочник имён частей монстров
CREATE TABLE monster_part_names (
  part_id SMALLSERIAL PRIMARY KEY,
  name    TEXT UNIQUE NOT NULL,
  slug    TEXT UNIQUE
);

-- Индексы для monster_part_names
CREATE INDEX monster_part_names_name_idx ON monster_part_names(name);
CREATE INDEX monster_part_names_slug_idx ON monster_part_names(slug);

-- ===== ФУНКЦИИ ДЛЯ РАБОТЫ СО СПРАВОЧНИКАМИ =====

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
    INSERT INTO players (login, slug)
    VALUES (player_login, LOWER(REPLACE(player_login, ' ', '_')))
    RETURNING player_id INTO v_player_id;
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
  SELECT c.clan_id INTO v_clan_id
  FROM clans c
  WHERE c.name = clan_name;
  
  -- Если не найден, создаём новый
  IF v_clan_id IS NULL THEN
    INSERT INTO clans (name, slug)
    VALUES (clan_name, LOWER(REPLACE(clan_name, ' ', '_')))
    RETURNING clan_id INTO v_clan_id;
  END IF;
  
  RETURN v_clan_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения или создания монстра
CREATE OR REPLACE FUNCTION get_or_create_monster(monster_kind TEXT, monster_spec TEXT DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
  v_monster_id INTEGER;
BEGIN
  -- Пытаемся найти существующего монстра
  SELECT m.monster_id INTO v_monster_id
  FROM monster_catalog m
  WHERE m.kind = monster_kind 
  AND COALESCE(m.spec, '') = COALESCE(monster_spec, '');
  
  -- Если не найден, создаём нового
  IF v_monster_id IS NULL THEN
    INSERT INTO monster_catalog (kind, spec, slug)
    VALUES (
      monster_kind, 
      monster_spec,
      LOWER(monster_kind || CASE WHEN monster_spec IS NOT NULL THEN '|' || monster_spec ELSE '' END)
    )
    RETURNING monster_id INTO v_monster_id;
  END IF;
  
  RETURN v_monster_id;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения или создания ресурса
CREATE OR REPLACE FUNCTION get_or_create_resource(resource_name TEXT)
RETURNS INTEGER AS $$
DECLARE
  v_resource_id INTEGER;
BEGIN
  -- Пытаемся найти существующий ресурс
  SELECT r.resource_id INTO v_resource_id
  FROM resource_names r
  WHERE r.name = resource_name;
  
  -- Если не найден, создаём новый
  IF v_resource_id IS NULL THEN
    INSERT INTO resource_names (name, slug)
    VALUES (resource_name, LOWER(REPLACE(resource_name, ' ', '_')))
    RETURNING resource_id INTO v_resource_id;
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
  SELECT p.part_id INTO v_part_id
  FROM monster_part_names p
  WHERE p.name = part_name;
  
  -- Если не найдена, создаём новую
  IF v_part_id IS NULL THEN
    INSERT INTO monster_part_names (name, slug)
    VALUES (part_name, LOWER(REPLACE(part_name, ' ', '_')))
    RETURNING part_id INTO v_part_id;
  END IF;
  
  RETURN v_part_id;
END;
$$ LANGUAGE plpgsql;

-- ===== КОММЕНТАРИИ =====

COMMENT ON TABLE players IS 'Справочник игроков';
COMMENT ON TABLE clans IS 'Справочник кланов';
COMMENT ON TABLE monster_catalog IS 'Каталог монстров с видами и подвидами';
COMMENT ON TABLE resource_names IS 'Справочник названий ресурсов';
COMMENT ON TABLE monster_part_names IS 'Справочник названий частей монстров';

COMMENT ON FUNCTION get_or_create_player(TEXT) IS 'Получить или создать игрока по логину';
COMMENT ON FUNCTION get_or_create_clan(TEXT) IS 'Получить или создать клан по названию';
COMMENT ON FUNCTION get_or_create_monster(TEXT, TEXT) IS 'Получить или создать монстра по виду и подвиду';
COMMENT ON FUNCTION get_or_create_resource(TEXT) IS 'Получить или создать ресурс по названию';
COMMENT ON FUNCTION get_or_create_monster_part(TEXT) IS 'Получить или создать часть монстра по названию';
