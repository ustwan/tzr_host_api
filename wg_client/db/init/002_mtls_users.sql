-- Создание БД-пользователей с разными правами для mTLS
-- Соответствие: client_register, client_readonly, client_admin

-- 1. Пользователь для регистрации (только INSERT в таблицы регистрации)
CREATE USER IF NOT EXISTS 'api_register'@'%' IDENTIFIED BY 'register_pass_change_me';
GRANT SELECT, INSERT ON gamedb.users TO 'api_register'@'%';
GRANT SELECT, INSERT ON gamedb.user_sessions TO 'api_register'@'%';
GRANT SELECT ON gamedb.constants TO 'api_register'@'%';
GRANT SELECT ON gamedb.servers TO 'api_register'@'%';
FLUSH PRIVILEGES;

-- 2. Пользователь для чтения (SELECT на все таблицы)
CREATE USER IF NOT EXISTS 'api_readonly'@'%' IDENTIFIED BY 'readonly_pass_change_me';
GRANT SELECT ON gamedb.* TO 'api_readonly'@'%';
FLUSH PRIVILEGES;

-- 3. Пользователь-администратор (все права)
CREATE USER IF NOT EXISTS 'api_admin'@'%' IDENTIFIED BY 'admin_pass_change_me';
GRANT ALL PRIVILEGES ON gamedb.* TO 'api_admin'@'%';
GRANT ALL PRIVILEGES ON api4_battles.* TO 'api_admin'@'%';
FLUSH PRIVILEGES;

-- Комментарии для документации
-- api_register: CN=api_register, certs: client_register/client.{crt,key}
-- api_readonly: CN=api_readonly, certs: client_readonly/client.{crt,key}
-- api_admin: CN=api_admin, certs: client_admin/client.{crt,key}










