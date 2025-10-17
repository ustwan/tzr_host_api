-- Minimal schema based on updated example/sql.md

-- 1) Таблица констант
CREATE TABLE IF NOT EXISTS constants (
  my_row_id   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'PK',
  Name        VARCHAR(50)     NOT NULL COMMENT 'Системное имя константы',
  Value       DECIMAL(5,2)    NULL     COMMENT 'Значение (число -999.99..999.99)',
  Description VARCHAR(255)    NULL     COMMENT 'Описание для админки/операторов',
  created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                               ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (my_row_id),
  UNIQUE KEY uq_constants_name (Name),
  CHECK (Value IS NULL OR (Value >= -999.99 AND Value <= 999.99))
) ENGINE=InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT=DYNAMIC;

-- Seed data
INSERT INTO constants (Name, Value, Description) VALUES
  ('ServerStatus', 1.0, '1 = всем доступен серв'),
  ('RateExp',      1.0, 'Опыт'),
  ('RatePvp',      1.0, 'ПВП'),
  ('RatePve',      1.0, 'ПВЕ'),
  ('RateColorMob', 1.0, 'x1'),
  ('RateSkill',    1.0, 'Скиллы'),
  ('CLIENT_STATUS',256.0,'статус')
ON DUPLICATE KEY UPDATE Value=VALUES(Value), Description=VALUES(Description);

-- 2) Минимальная таблица tgplayers (только 3 поля из example)
CREATE TABLE IF NOT EXISTS tgplayers (
  telegram_id BIGINT       NOT NULL,
  username    VARCHAR(64)  NULL,
  login       VARCHAR(64)  NOT NULL,
  -- Добавляем индексы для производительности
  KEY ix_tgplayers_telegram (telegram_id),
  KEY ix_tgplayers_login (login)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

-- Примечание: НЕТ UNIQUE на telegram_id чтобы разрешить до 5 аккаунтов
-- login тоже НЕ unique в базовой версии (проверка в коде)










