-- V3: Создание таблиц для логов боёв
-- Основные таблицы для хранения данных о боях

-- Тип под вид лута
DO $$ BEGIN
  CREATE TYPE loot_kind AS ENUM ('resource','monster_part','other');
EXCEPTION WHEN duplicate_object THEN END $$;

-- ===== ОСНОВНЫЕ ТАБЛИЦЫ =====

-- Таблица боёв
CREATE TABLE battles (
  id               BIGINT PRIMARY KEY,
  ts               TIMESTAMPTZ NOT NULL,
  size_bytes       INTEGER,
  sha256           TEXT,
  storage_key      TEXT NOT NULL,
  compressed       BOOLEAN NOT NULL DEFAULT FALSE,

  turns            SMALLINT,
  battle_type      CHAR(1),
  loc_x            SMALLINT,
  loc_y            SMALLINT,
  start_ts         TIMESTAMPTZ,

  players_cnt      INTEGER,
  monsters_cnt     INTEGER,
  entities_cnt     INTEGER,

  data             JSONB
);

-- Индексы для таблицы battles
CREATE INDEX battles_ts_idx ON battles(ts);
CREATE INDEX battles_type_idx ON battles(battle_type);
CREATE INDEX battles_location_idx ON battles(loc_x, loc_y);
CREATE INDEX battles_data_idx ON battles USING GIN(data);

-- Таблица участников боёв
CREATE TABLE battle_participants (
  battle_id      BIGINT  REFERENCES battles(id) ON DELETE CASCADE,
  player_id      INTEGER REFERENCES players(player_id),
  clan_id        INTEGER REFERENCES clans(clan_id),

  profession     SMALLINT,
  side           SMALLINT,
  rank_points    NUMERIC(10,2),
  pve_points     INTEGER,
  level          SMALLINT,
  gender         SMALLINT,

  survived       SMALLINT NOT NULL DEFAULT 0 CHECK (survived IN (0,1)),
  kills_monsters INTEGER  NOT NULL DEFAULT 0 CHECK (kills_monsters >= 0),
  kills_players  INTEGER  NOT NULL DEFAULT 0 CHECK (kills_players  >= 0),

  PRIMARY KEY (battle_id, player_id)
);

-- Индексы для battle_participants
CREATE INDEX bp_player_battle_idx ON battle_participants(player_id, battle_id);
CREATE INDEX bp_clan_battle_idx   ON battle_participants(clan_id,   battle_id);
CREATE INDEX bp_side_idx ON battle_participants(side);
CREATE INDEX bp_survived_idx ON battle_participants(survived);

-- Таблица монстров в боях
CREATE TABLE battle_monsters (
  id         BIGSERIAL PRIMARY KEY,
  battle_id  BIGINT  REFERENCES battles(id) ON DELETE CASCADE,
  monster_id INTEGER REFERENCES monster_catalog(monster_id),
  side       SMALLINT,
  count      INTEGER NOT NULL CHECK (count >= 0),
  min_level  SMALLINT,
  max_level  SMALLINT,
  UNIQUE (battle_id, monster_id)
);

-- Индексы для battle_monsters
CREATE INDEX bm_monster_battle_idx ON battle_monsters(monster_id, battle_id);
CREATE INDEX bm_side_idx ON battle_monsters(side);

-- Таблица лута в боях
CREATE TABLE battle_loot (
  id          BIGSERIAL PRIMARY KEY,
  battle_id   BIGINT  REFERENCES battles(id) ON DELETE CASCADE,
  battle_ts   DATE    NOT NULL,
  kind        loot_kind NOT NULL,

  resource_id SMALLINT REFERENCES resource_names(resource_id),
  part_id     SMALLINT REFERENCES monster_part_names(part_id),
  item_id     INTEGER,
  item_name   TEXT,

  qty         INTEGER NOT NULL CHECK (qty > 0),

  CHECK (
    (kind='resource'     AND resource_id IS NOT NULL AND part_id IS NULL AND item_id IS NULL AND item_name IS NULL) OR
    (kind='monster_part' AND part_id     IS NOT NULL AND resource_id IS NULL AND item_id IS NULL AND item_name IS NULL) OR
    (kind='other'        AND item_id     IS NOT NULL AND item_name IS NOT NULL AND resource_id IS NULL AND part_id IS NULL)
  )
);

-- Индексы для battle_loot
CREATE UNIQUE INDEX bl_uq_resource      ON battle_loot (battle_id, resource_id) WHERE kind='resource';
CREATE UNIQUE INDEX bl_uq_monster_part  ON battle_loot (battle_id, part_id)     WHERE kind='monster_part';
CREATE UNIQUE INDEX bl_uq_other         ON battle_loot (battle_id, item_id)     WHERE kind='other';

CREATE INDEX bl_res_period_idx   ON battle_loot (battle_ts, resource_id) WHERE kind='resource';
CREATE INDEX bl_part_period_idx  ON battle_loot (battle_ts, part_id)     WHERE kind='monster_part';
CREATE INDEX bl_other_period_idx ON battle_loot (battle_ts, item_id)     WHERE kind='other';
CREATE INDEX bl_battle_idx       ON battle_loot (battle_id);

-- Таблица истории логов боёв
CREATE TABLE battle_logs (
  log_id          BIGSERIAL PRIMARY KEY,
  battle_id       BIGINT REFERENCES battles(id) ON DELETE CASCADE,
  storage_key     TEXT NOT NULL,
  size_bytes      INTEGER,
  sha256          TEXT,
  compressed      BOOLEAN,
  format          TEXT,
  source          TEXT,
  parser_version  TEXT,
  status          TEXT,
  ingested_at     TIMESTAMPTZ DEFAULT now(),
  parse_started_at  TIMESTAMPTZ,
  parse_finished_at TIMESTAMPTZ,
  error_message   TEXT
);

-- Индексы для battle_logs
CREATE INDEX battle_logs_battle_idx   ON battle_logs (battle_id);
CREATE INDEX battle_logs_ingested_idx ON battle_logs (ingested_at);
CREATE INDEX battle_logs_status_idx ON battle_logs (status);

-- Комментарии к таблицам
COMMENT ON TABLE battles IS 'Основная таблица боёв с метаданными';
COMMENT ON TABLE battle_participants IS 'Участники боёв с их характеристиками';
COMMENT ON TABLE battle_monsters IS 'Монстры в боях';
COMMENT ON TABLE battle_loot IS 'Лут полученный в боях';
COMMENT ON TABLE battle_logs IS 'История обработки логов боёв';
