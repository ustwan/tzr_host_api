-- Flyway V1: initial schema for tzserver database (based on example/sql.md)

-- 1) База данных tzserver
CREATE DATABASE IF NOT EXISTS tzserver
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE tzserver;

-- 2) Таблица констант
CREATE TABLE IF NOT EXISTS tzserver.constants (
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

-- Seed data для констант
INSERT INTO tzserver.constants (Name, Value, Description) VALUES
  ('ServerStatus', 1.0, '1 = всем доступен серв'),
  ('RateExp',      1.0, 'Опыт'),
  ('RatePvp',      1.0, 'ПВП'),
  ('RatePve',      1.0, 'ПВЕ'),
  ('RateColorMob', 1.0, 'x1'),
  ('RateSkill',    1.0, 'Скиллы'),
  ('CLIENT_STATUS',256.0,'статус')
ON DUPLICATE KEY UPDATE Value=VALUES(Value), Description=VALUES(Description);

-- 3) Пользователи бота ↔ учётка игры
CREATE TABLE IF NOT EXISTS tzserver.tgplayers (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'PK',
  telegram_id   BIGINT UNSIGNED NOT NULL COMMENT 'ID пользователя в Telegram',
  tg_chat_id    BIGINT          NULL COMMENT 'ЛС-чат или групповой чат',
  username      VARCHAR(64)     NULL COMMENT '@username',
  first_name    VARCHAR(64)     NULL,
  last_name     VARCHAR(64)     NULL,
  login         VARCHAR(64)     NOT NULL COMMENT 'Логин в игре',
  status        ENUM('pending','active','blocked') NOT NULL DEFAULT 'active',
  is_admin      TINYINT(1)      NOT NULL DEFAULT 0,
  locale        VARCHAR(16)     NULL,
  created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_seen_at  TIMESTAMP       NULL DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tgplayers_telegram_id (telegram_id),
  UNIQUE KEY uq_tgplayers_login (login),
  KEY ix_tgplayers_chat (tg_chat_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 4) Токены восстановления пароля (/recover)
CREATE TABLE IF NOT EXISTS tzserver.recover_tokens (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  player_id    BIGINT UNSIGNED NOT NULL,
  login        VARCHAR(64)     NOT NULL,
  token        CHAR(64)        NOT NULL COMMENT 'hex SHA-256/UUID-в-hex',
  expires_at   DATETIME        NOT NULL,
  used_at      DATETIME        NULL,
  created_at   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_recover_token (token),
  KEY ix_recover_login (login),
  CONSTRAINT fk_recover_player
    FOREIGN KEY (player_id) REFERENCES tzserver.tgplayers(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 5) Лог исходящих/входящих XML к игровому серверу (порт 5190)
CREATE TABLE IF NOT EXISTS tzserver.xml_outbox (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  player_id    BIGINT UNSIGNED NULL,
  target_host  VARCHAR(128)    NOT NULL DEFAULT '127.0.0.1',
  target_port  INT             NOT NULL DEFAULT 5190,
  direction    ENUM('out','in') NOT NULL DEFAULT 'out',
  payload      MEDIUMTEXT      NOT NULL,
  status       ENUM('queued','sent','ok','error') NOT NULL DEFAULT 'sent',
  error_text   VARCHAR(512)    NULL,
  sent_at      DATETIME        NULL,
  response_at  DATETIME        NULL,
  created_at   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_xml_outbox_port (target_port),
  CONSTRAINT fk_outbox_player
    FOREIGN KEY (player_id) REFERENCES tzserver.tgplayers(id) ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;










