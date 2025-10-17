from typing import Optional

import pymysql

from infrastructure.db import get_dsn_and_db
from ports.user_repository import UserRepository


class MysqlUserRepository(UserRepository):
    async def count_telegram_players(self, telegram_id: int) -> int:
        """Проверка существования пользователя (в новой схеме - только 1 аккаунт на telegram_id)"""
        dsn, _ = get_dsn_and_db()
        conn = pymysql.connect(**dsn)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM tgplayers WHERE telegram_id=%s", (telegram_id,))
                row = cur.fetchone()
                return int(row["c"]) if row else 0
        finally:
            conn.close()

    async def is_login_taken(self, login: str) -> bool:
        """Проверка уникальности логина в tgplayers"""
        dsn, _ = get_dsn_and_db()
        conn = pymysql.connect(**dsn)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM tgplayers WHERE login=%s", (login,))
                return cur.fetchone() is not None
        finally:
            conn.close()

    async def insert_user_and_tgplayer(self, login: str, gender: int, telegram_id: int, username: Optional[str]) -> None:
        """Создание пользователя в tgplayers (минимальная схема из example)"""
        dsn, _ = get_dsn_and_db()
        conn = pymysql.connect(**dsn)
        try:
            conn.autocommit(False)
            with conn.cursor() as cur:
                # Минимальная схема: только telegram_id, username, login
                # gender передается в game_server, но не сохраняется в БД
                cur.execute(
                    """INSERT INTO tgplayers (telegram_id, username, login) 
                       VALUES (%s, %s, %s)""",
                    (telegram_id, username, login)
                )
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass


