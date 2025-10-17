-- Users and Telegram players tables for registration flow

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  login VARCHAR(16) COLLATE utf8mb4_bin NOT NULL UNIQUE,
  gender TINYINT UNSIGNED NULL,
  email VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS tgplayers (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  telegram_id BIGINT UNSIGNED NOT NULL,
  username VARCHAR(64) NULL,
  login VARCHAR(16) COLLATE utf8mb4_bin NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_tgplayers_telegram_id (telegram_id)
) CHARACTER SET utf8mb4;

-- Optional FK link (will succeed only if both tables exist with matching collation)
ALTER TABLE tgplayers
  ADD CONSTRAINT fk_tgplayers_users_login
  FOREIGN KEY (login) REFERENCES users(login)
  ON DELETE CASCADE;


