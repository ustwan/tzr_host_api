ПРИМЕРНАЯ ЛОГИКА ИЗ register.py

База: tzserver (из MYSQL_CONFIG).

Единственная таблица, с которой работает файл: tgplayers.

Ровно 3 поля, которые код читает/пишет:

telegram_id — ID пользователя Telegram.

username — ник в Telegram (может быть NULL, т.к. не у всех он есть).

login — игровой логин.

Минимальный DDL (ровно под эти обращения):

CREATE DATABASE IF NOT EXISTS tzserver;

CREATE TABLE IF NOT EXISTS tzserver.tgplayers (
  telegram_id BIGINT NOT NULL,
  username    VARCHAR(64) NULL,
  login       VARCHAR(64) NOT NULL
);

В файле задано подключение:

MYSQL_CONFIG = {'host': 'localhost','user': 'root','password': '','database': 'tzserver'}


На запись используется только этот INSERT:

INSERT INTO tgplayers (telegram_id, username, login) VALUES (%s, %s, %s)


На чтение встречаются только такие запросы:

Проверка лимита/наличия записей по пользователю:

SELECT COUNT(*) FROM tgplayers WHERE telegram_id = %s


Получение логинов пользователя (для восстановления пароля):

SELECT login FROM tgplayers WHERE telegram_id = %s


UPDATE/DELETE/других таблиц в коде нет. Поля, которые влияют на XML (gender, password) в БД не сохраняются — они только уходят в <ADDUSER ...> на сокет :5190.