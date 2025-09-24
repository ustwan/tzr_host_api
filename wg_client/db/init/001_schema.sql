-- Initial schema for test DB
CREATE TABLE IF NOT EXISTS constants (
  my_row_id INT PRIMARY KEY AUTO_INCREMENT,
  Name VARCHAR(64) NOT NULL UNIQUE,
  Value DECIMAL(10,2) NOT NULL DEFAULT 0,
  Description VARCHAR(255) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

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
