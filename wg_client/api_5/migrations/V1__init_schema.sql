-- API 5 Shop Parser - Базовая схема БД
-- Версия: 1.0
-- Дата: 2025-10-11

-- 1. Магазины (3 города)
CREATE TABLE IF NOT EXISTS shops (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,  -- moscow, oasis, neva
    name TEXT NOT NULL,          -- Moscow, Oasis, Neva
    bot_login TEXT,              -- Sova
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Наполнить магазины
INSERT INTO shops (code, name, bot_login) VALUES
    ('moscow', 'Moscow', 'Sova'),
    ('oasis', 'Oasis', 'Sova'),
    ('neva', 'Neva', 'Sova')
ON CONFLICT (code) DO NOTHING;

-- 2. Шаблоны товаров (type + name + category)
CREATE TABLE IF NOT EXISTS item_templates (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,          -- 1.13, 2.32, etc
    name TEXT NOT NULL,          -- b2-k6, b2-p1, etc
    category TEXT NOT NULL,      -- k, p, v, h, etc
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(type, name, category)
);

CREATE INDEX IF NOT EXISTS idx_item_templates_category ON item_templates(category);
CREATE INDEX IF NOT EXISTS idx_item_templates_name ON item_templates(name);

-- 3. Товары (экземпляры в магазине)
CREATE TABLE IF NOT EXISTS shop_items (
    id BIGINT PRIMARY KEY,       -- ID из игры
    template_id INT REFERENCES item_templates(id),
    shop_id INT REFERENCES shops(id),
    
    -- Базовые поля
    txt TEXT,                    -- Название
    price NUMERIC(12, 2),
    current_quality INT,
    max_quality INT,
    weight INT,                  -- massa
    
    -- Урон и защита (JSONB для гибкости)
    damage JSONB,                -- [{type: "S", min: 2, max: 6}, ...]
    protection JSONB,            -- [{type: "S", min: 7, max: 16}, ...]
    
    -- Оружие
    caliber TEXT,
    range INT,
    grouping INT,                -- Кучность
    piercing NUMERIC(5, 2),      -- Бронебойность в %
    max_count INT,               -- Ёмкость магазина
    reload_od INT,               -- rOD
    attack_modes JSONB,          -- [{type: 2, od: 3}, {type: 3, od: 5}]
    skill INT,                   -- nskill
    
    -- Экипировка
    slots TEXT,                  -- st (G,H / GH / F / C)
    equip_od INT,                -- OD
    requirements JSONB,          -- {level: 6, strength: 14, ...}
    bonuses JSONB,               -- {int: 4, str: 2}
    build_in TEXT[],             -- Встройки
    
    -- Мета
    infinty BOOLEAN DEFAULT FALSE,
    owner TEXT,
    section INT,
    added_at TIMESTAMP,          -- put_day
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Сырые атрибуты (для трассировки)
    raw_attributes JSONB
);

CREATE INDEX IF NOT EXISTS idx_shop_items_template ON shop_items(template_id);
CREATE INDEX IF NOT EXISTS idx_shop_items_shop ON shop_items(shop_id);
CREATE INDEX IF NOT EXISTS idx_shop_items_price ON shop_items(price);
CREATE INDEX IF NOT EXISTS idx_shop_items_added_at ON shop_items(added_at);
CREATE INDEX IF NOT EXISTS idx_shop_items_owner ON shop_items(owner);

-- 4. Снимки магазина
CREATE TABLE IF NOT EXISTS snapshots (
    id SERIAL PRIMARY KEY,
    shop_id INT NOT NULL REFERENCES shops(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    items_count INT DEFAULT 0,
    worker_name TEXT             -- moscow_worker, oasis_worker, neva_worker
);

CREATE INDEX IF NOT EXISTS idx_snapshots_shop ON snapshots(shop_id, created_at DESC);

-- 5. Привязка товаров к снимку
CREATE TABLE IF NOT EXISTS snapshot_items (
    snapshot_id INT NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    item_id BIGINT NOT NULL REFERENCES shop_items(id),
    PRIMARY KEY(snapshot_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_items_snapshot ON snapshot_items(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_items_item ON snapshot_items(item_id);

-- 6. История изменений товаров
CREATE TABLE IF NOT EXISTS item_changes (
    id SERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES shop_items(id),
    snapshot_id INT NOT NULL REFERENCES snapshots(id),
    change_type TEXT NOT NULL,   -- added, removed, price_changed, quality_changed
    old_price NUMERIC(12, 2),
    new_price NUMERIC(12, 2),
    old_quality INT,
    new_quality INT,
    detected_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_item_changes_item ON item_changes(item_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_item_changes_snapshot ON item_changes(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_item_changes_type ON item_changes(change_type);

-- 7. Сессии ботов
CREATE TABLE IF NOT EXISTS bot_sessions (
    id SERIAL PRIMARY KEY,
    bot_login TEXT NOT NULL,
    shop_code TEXT NOT NULL,     -- moscow, oasis, neva
    session_id TEXT,
    authenticated BOOLEAN DEFAULT FALSE,
    last_activity TIMESTAMP,
    location TEXT,               -- Текущая локация бота
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(bot_login, shop_code)
);

CREATE INDEX IF NOT EXISTS idx_bot_sessions_shop ON bot_sessions(shop_code);
CREATE INDEX IF NOT EXISTS idx_bot_sessions_auth ON bot_sessions(authenticated, last_activity);

-- Комментарии к таблицам
COMMENT ON TABLE shops IS 'Магазины в трёх городах (Moscow, Oasis, Neva)';
COMMENT ON TABLE item_templates IS 'Шаблоны товаров (тип + имя + категория)';
COMMENT ON TABLE shop_items IS 'Экземпляры товаров в магазинах';
COMMENT ON TABLE snapshots IS 'Снимки ассортимента магазинов';
COMMENT ON TABLE snapshot_items IS 'Привязка товаров к снимкам';
COMMENT ON TABLE item_changes IS 'История изменений товаров (цены, качество, появление/исчезновение)';
COMMENT ON TABLE bot_sessions IS 'Сессии ботов-парсеров в игре';


