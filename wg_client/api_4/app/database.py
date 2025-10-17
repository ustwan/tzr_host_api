"""
Модуль работы с базой данных для API_4
Обеспечивает работу с PostgreSQL для хранения и поиска данных о боях
"""

import asyncio
import uuid
import asyncpg
import os
import json
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
from pathlib import Path

from app.models import (
    BattleResponse, BattleListItem, BattleSearchResponse,
    BattleMeta, Participant, Monster, Loot, BattleInfo
)


class BattleDatabase:
    """Класс для работы с базой данных боёв"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_params = self._get_connection_params()
    
    def _get_connection_params(self) -> Dict[str, Any]:
        """Получение параметров подключения к БД"""
        db_mode = os.getenv("DB_MODE", "test")
        
        if db_mode == "test":
            return {
                "host": os.getenv("DB_API4_TEST_HOST", "localhost"),
                "port": int(os.getenv("DB_API4_TEST_PORT", "5432")),
                "database": os.getenv("DB_API4_TEST_NAME", "api4_battles"),
                "user": os.getenv("DB_API4_TEST_USER", "api4_user"),
                "password": os.getenv("DB_API4_TEST_PASSWORD", "api4_pass")
            }
        else:
            return {
                "host": os.getenv("DB_API4_PROD_HOST", "localhost"),
                "port": int(os.getenv("DB_API4_PROD_PORT", "5432")),
                "database": os.getenv("DB_API4_PROD_NAME", "api4_battles"),
                "user": os.getenv("DB_API4_PROD_USER", "api4_user"),
                "password": os.getenv("DB_API4_PROD_PASSWORD", "api4_pass")
            }
    
    async def connect(self):
        """Подключение к базе данных"""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                **self._connection_params,
                min_size=1,
                max_size=2,  # МИНИМУМ: api_mother создаёт МНОГО экземпляров BattleDatabase
                command_timeout=60,
                statement_cache_size=0,
                max_inactive_connection_lifetime=20,  # Быстро закрывать
                max_queries=1000  # Ограничение запросов на соединение
            )
    
    async def disconnect(self):
        """Отключение от базы данных"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def _execute_query(self, query: str, *args) -> List[Dict]:
        """Выполнение запроса к БД"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def _execute_one(self, query: str, *args) -> Optional[Dict]:
        """Выполнение запроса с возвратом одной записи"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def _execute_command(self, query: str, *args) -> str:
        """Выполнение команды (INSERT, UPDATE, DELETE)"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *args)
            return result
    
    # ===== МЕТОДЫ ДЛЯ РАБОТЫ СО СПРАВОЧНИКАМИ =====
    
    async def get_or_create_player(self, login: str) -> int:
        """Получить или создать игрока"""
        query = "SELECT get_or_create_player(CAST($1 AS TEXT)) as id"
        result = await self._execute_one(query, login)
        return result["id"]
    
    async def get_or_create_clan(self, name: str) -> Optional[int]:
        """Получить или создать клан"""
        if not name:
            return None
        query = "SELECT get_or_create_clan($1) as id"
        result = await self._execute_one(query, name)
        return result["id"]
    
    async def get_or_create_monster(self, kind: str, spec: str = None) -> int:
        """Получить или создать монстра"""
        query = "SELECT get_or_create_monster($1, $2) as id"
        result = await self._execute_one(query, kind, spec)
        return result["id"]
    
    async def get_or_create_resource(self, name: str) -> int:
        """Получить или создать ресурс"""
        query = "SELECT get_or_create_resource($1) as id"
        result = await self._execute_one(query, name)
        return result["id"]
    
    async def get_or_create_monster_part(self, name: str) -> int:
        """Получить или создать часть монстра"""
        query = "SELECT get_or_create_monster_part($1) as id"
        result = await self._execute_one(query, name)
        return result["id"]
    
    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С БОЯМИ =====
    
    async def save_battle(self, battle_data: Dict[str, Any]) -> int:
        """Сохранение боя в БД"""
        battle_declared_id = battle_data.get("id")
        
        # Сохраняем основной бой
        battle_query = """
            INSERT INTO battles (
                ts, size_bytes, sha256, storage_key, compressed,
                turns, battle_type, loc_x, loc_y, start_ts,
                players_cnt, monsters_cnt, entities_cnt, map_patch, data,
                source_id
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15,
                $16
            )
            ON CONFLICT (source_id) DO UPDATE SET
                ts = EXCLUDED.ts,
                size_bytes = EXCLUDED.size_bytes,
                sha256 = EXCLUDED.sha256,
                storage_key = EXCLUDED.storage_key,
                compressed = EXCLUDED.compressed,
                turns = EXCLUDED.turns,
                battle_type = EXCLUDED.battle_type,
                loc_x = EXCLUDED.loc_x,
                loc_y = EXCLUDED.loc_y,
                start_ts = EXCLUDED.start_ts,
                players_cnt = EXCLUDED.players_cnt,
                monsters_cnt = EXCLUDED.monsters_cnt,
                entities_cnt = EXCLUDED.entities_cnt,
                map_patch = EXCLUDED.map_patch,
                data = EXCLUDED.data
            RETURNING id
        """
        
        # Жёстко приводим потенциально неоднородные типы к ожидаемым БД
        sha256_value = str(battle_data.get("sha256") or "")
        storage_key_value = str(battle_data.get("storage_key") or "")

        # Подготавливаем все значения строго по типам столбцов
        ts_value = battle_data["ts"]
        size_bytes_value = int(battle_data.get("size_bytes") or 0)
        battle_type_value = str(battle_data.get("battle_type") or "")
        loc_x_value = int(battle_data.get("loc_x") or 0) if battle_data.get("loc_x") is not None else None
        loc_y_value = int(battle_data.get("loc_y") or 0) if battle_data.get("loc_y") is not None else None
        start_ts_value = battle_data.get("start_ts")
        players_cnt_value = int(battle_data.get("players_cnt") or 0)
        monsters_cnt_value = int(battle_data.get("monsters_cnt") or 0)
        entities_cnt_value = int(battle_data.get("entities_cnt") or 0)
        map_patch_value = json.dumps((battle_data.get("data", {}).get("battle") or {}).get("map_patch", {}))
        data_value = json.dumps(battle_data.get("data", {}))

        # удалён временный отладочный вывод аргументов для INSERT battles

        # Вычисляем source_id из имени файла, если не передан явно в battle_data['source_id']
        source_id_value = None
        if battle_data.get("source_id") is not None:
            try:
                source_id_value = int(battle_data.get("source_id"))
            except Exception:
                source_id_value = None
        if source_id_value is None:
            # Пытаемся извлечь из storage_key последний числовой компонент
            try:
                filename = os.path.basename(storage_key_value)
                base = filename.split('.')[0]
                source_id_value = int(base) if base.isdigit() else None
            except Exception:
                source_id_value = None

        inserted = await self._execute_one(
            battle_query,
            ts_value,
            size_bytes_value,
            sha256_value,
            storage_key_value,
            battle_data.get("compressed", False),
            int(battle_data.get("turns") or 0) if battle_data.get("turns") is not None else None,
            battle_type_value,
            loc_x_value,
            loc_y_value,
            start_ts_value,
            players_cnt_value,
            monsters_cnt_value,
            entities_cnt_value,
            map_patch_value,
            data_value,
            source_id_value
        )
        battle_id = inserted["id"] if inserted and "id" in inserted else battle_declared_id or 0
        
        # Сохраняем участников
        await self._save_battle_participants(battle_id, battle_data.get("meta", {}).get("participants", []))
        
        # Сохраняем монстров
        await self._save_battle_monsters(battle_id, battle_data.get("meta", {}).get("monsters", {}))
        
        # Сохраняем лут
        await self._save_battle_loot(battle_id, battle_data.get("meta", {}).get("loot", {}))
        
        return battle_id
    
    async def _save_battle_participants(self, battle_id: int, participants: List[Dict]):
        """Сохранение участников боя"""
        if not participants:
            return
        
        # Удаляем старых участников
        await self._execute_command(
            "DELETE FROM battle_participants WHERE battle_id = $1",
            battle_id
        )
        
        for participant in participants:
            # Нормализуем типы под схему БД
            login_value = str(participant.get("login", ""))
            clan_name = participant.get("clan")
            clan_value = str(clan_name) if clan_name is not None else None
            profession_value = participant.get("profession")
            if isinstance(profession_value, int):
                profession_value = str(profession_value)
            side_value = participant.get("side")
            if isinstance(side_value, int):
                side_value = str(side_value)
            gender_value = participant.get("gender")
            if isinstance(gender_value, int):
                gender_value = str(gender_value)
            survived_value = participant.get("survived", False)
            if isinstance(survived_value, int):
                survived_value = bool(survived_value)

            player_id = await self.get_or_create_player(login_value)

            # удалён временный диагностический вывод типов и значений параметров

            # Жестко приводим числовые поля к int
            rank_points_value = int(participant.get("rank_points", 0)) if participant.get("rank_points") is not None else 0
            pve_points_value = int(participant.get("pve_points", 0)) if participant.get("pve_points") is not None else 0
            level_value = int(participant.get("level", 0)) if participant.get("level") is not None else 0

            # JSONB поля
            intervened_value = json.dumps(participant.get("intervened") or {})
            kills_value = json.dumps(participant.get("kills") or {})
            damage_total_value = json.dumps(participant.get("damage_total") or {})
            loot_value = json.dumps(participant.get("loot") or {})
            # Берём счётчики убийств из participant['kills'] (если есть)
            kills_obj = participant.get("kills") or {}
            kills_monsters_cnt = kills_obj.get("monsters", participant.get("kills_monsters", 0))
            kills_players_cnt = kills_obj.get("players", participant.get("kills_players", 0))
            kills_monsters_value = int(kills_monsters_cnt) if kills_monsters_cnt is not None else 0
            kills_players_value = int(kills_players_cnt) if kills_players_cnt is not None else 0

            # Полный INSERT согласно схеме таблицы
            insert_sql = f"""
                INSERT INTO battle_participants (
                    battle_id, player_id, login, clan, side,
                    survived, rank_points, pve_points,
                    intervened, kills, damage_total, loot,
                    profession, gender, level, kills_monsters, kills_players
                ) VALUES (
                    $1::bigint, $2::int, $3::text, $4::text, $5::text,
                    $6::boolean, $7::int, $8::int,
                    $9::jsonb, $10::jsonb, $11::jsonb, $12::jsonb,
                    $13::text, $14::text, $15::int, $16::int, $17::int
                ) -- full_insert_bp_v2 {uuid.uuid4()}
            """
            await self._execute_command(
                insert_sql,
                battle_id, player_id, login_value, clan_value, side_value,
                survived_value, rank_points_value, pve_points_value,
                intervened_value, kills_value, damage_total_value, loot_value,
                profession_value, gender_value, level_value, kills_monsters_value, kills_players_value
            )
    
    async def _save_battle_monsters(self, battle_id: int, monsters: Dict[str, Dict]):
        """Сохранение монстров боя"""
        if not monsters:
            return
        
        # Удаляем старых монстров
        await self._execute_command(
            "DELETE FROM battle_monsters WHERE battle_id = $1",
            battle_id
        )
        
        for monster_name, monster_data in monsters.items():
            # Парсим имя монстра (kind|spec)
            parts = monster_name.split("|", 1)
            kind = parts[0]
            spec = parts[1] if len(parts) > 1 else None
            
            monster_id = await self.get_or_create_monster(kind, spec)
            # Нормализуем типы
            side_value = monster_data.get("side")
            if isinstance(side_value, int):
                side_value = str(side_value)
            count_value = int(monster_data.get("count", 0)) if monster_data.get("count") is not None else 0
            min_level_value = int(monster_data.get("min_level", 0)) if monster_data.get("min_level") is not None else 0
            max_level_value = int(monster_data.get("max_level", 0)) if monster_data.get("max_level") is not None else 0
            
            await self._execute_command("""
                INSERT INTO battle_monsters (
                    battle_id, monster_id, side, count, min_level, max_level
                ) VALUES ($1::bigint, $2::int, $3::text, $4::int, $5::int, $6::int)
            """,
                battle_id, monster_id, side_value,
                count_value, min_level_value,
                max_level_value
            )
    
    async def _save_battle_loot(self, battle_id: int, loot: Dict):
        """Сохранение лута боя"""
        if not loot:
            return
        
        # Удаляем старый лут
        await self._execute_command(
            "DELETE FROM battle_loot WHERE battle_id = $1",
            battle_id
        )
        
        battle_ts = date.today()
        
        # Сохраняем ресурсы
        for resource_name, quantity in loot.get("resources_total", {}).items():
            resource_id = await self.get_or_create_resource(resource_name)
            await self._execute_command("""
                INSERT INTO battle_loot (battle_id, battle_ts, kind, resource_id, qty)
                VALUES ($1, $2, 'resource', $3, $4)
            """, battle_id, battle_ts, resource_id, quantity)
        
        # Сохраняем части монстров
        for part_name, quantity in loot.get("monster_parts_total", {}).items():
            part_id = await self.get_or_create_monster_part(part_name)
            await self._execute_command("""
                INSERT INTO battle_loot (battle_id, battle_ts, kind, part_id, qty)
                VALUES ($1, $2, 'monster_part', $3, $4)
            """, battle_id, battle_ts, part_id, quantity)
        
        # Сохраняем другие предметы
        for item_name, quantity in loot.get("other_items", {}).items():
            await self._execute_command("""
                INSERT INTO battle_loot (battle_id, battle_ts, kind, item_id, item_name, qty)
                VALUES ($1, $2, 'other', $3, $4, $5)
            """, battle_id, battle_ts, hash(item_name) % 2147483647, item_name, quantity)
    
    async def get_battle(self, battle_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о бое по настоящему battle_id (source_id)"""
        query = """
            SELECT b.*, 
                   array_agg(DISTINCT p.login) as players,
                   array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL) as clans
            FROM battles b
            LEFT JOIN battle_participants bp ON b.id = bp.battle_id
            LEFT JOIN players p ON bp.player_id = p.id
            LEFT JOIN clans c ON bp.clan = c.name
            WHERE b.source_id = $1
            GROUP BY b.id
        """
        
        result = await self._execute_one(query, battle_id)
        if not result:
            return None
        
        # Преобразуем в нужный формат
        battle = dict(result)
        battle["players"] = list(set(battle["players"])) if battle["players"] else []
        battle["clans"] = list(set(battle["clans"])) if battle["clans"] else []
        
        return battle
    
    async def list_battles(self, page: int = 1, limit: int = 10) -> Tuple[List[Dict], int]:
        """Список боёв с пагинацией"""
        offset = (page - 1) * limit
        
        # Получаем общее количество
        count_query = "SELECT COUNT(*) as total FROM battles"
        total_result = await self._execute_one(count_query)
        total = total_result["total"]
        
        # Получаем список боёв
        battles_query = """
            SELECT b.id, b.ts, b.battle_type, b.turns, b.loc_x, b.loc_y,
                   b.source_id,
                   array_agg(DISTINCT p.login) as players,
                   COALESCE(SUM(bm.count), 0) as monsters_count
            FROM battles b
            LEFT JOIN battle_participants bp ON b.id = bp.battle_id
            LEFT JOIN players p ON bp.player_id = p.id
            LEFT JOIN battle_monsters bm ON b.id = bm.battle_id
            GROUP BY b.id, b.ts, b.battle_type, b.turns, b.loc_x, b.loc_y, b.source_id
            ORDER BY b.id DESC
            LIMIT $1 OFFSET $2
        """
        
        battles = await self._execute_query(battles_query, limit, offset)
        
        # Преобразуем в нужный формат
        for battle in battles:
            battle["players"] = list(set(battle["players"])) if battle["players"] else []
            battle["location"] = [battle["loc_x"], battle["loc_y"]] if battle["loc_x"] is not None else None
            battle["duration"] = battle.get("turns", 0)  # ✅ Количество ходов
        
        return battles, total
    
    async def search_battles(
        self,
        player: Optional[str] = None,
        clan: Optional[str] = None,
        battle_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        monsters: Optional[str] = None,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[Dict], int]:
        """Поиск боёв по критериям"""
        offset = (page - 1) * limit
        
        # Строим условия поиска
        conditions = []
        params = []
        param_count = 0
        
        if player:
            param_count += 1
            conditions.append(f"EXISTS (SELECT 1 FROM battle_participants bp JOIN players p ON bp.player_id = p.id WHERE bp.battle_id = b.id AND p.login ILIKE ${param_count})")
            params.append(f"%{player}%")
        
        if clan:
            param_count += 1
            # ✅ Упрощенный поиск по клану без JOIN с таблицей clans
            conditions.append(f"EXISTS (SELECT 1 FROM battle_participants bp WHERE bp.battle_id = b.id AND bp.clan ILIKE ${param_count})")
            params.append(f"%{clan}%")
        
        if battle_type:
            param_count += 1
            conditions.append(f"b.battle_type = ${param_count}")
            params.append(battle_type)
        
        if from_date:
            param_count += 1
            conditions.append(f"b.ts >= ${param_count}")
            params.append(from_date)
        
        if to_date:
            param_count += 1
            conditions.append(f"b.ts <= ${param_count}")
            params.append(to_date)
        
        if monsters:
            param_count += 1
            # ✅ Поиск по монстрам через monster_catalog (kind и spec)
            conditions.append(f"""EXISTS (
                SELECT 1 FROM battle_monsters bm 
                JOIN monster_catalog mc ON bm.monster_id = mc.id 
                WHERE bm.battle_id = b.id 
                AND (mc.kind ILIKE ${param_count} OR mc.spec ILIKE ${param_count})
            )""")
            params.append(f"%{monsters}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Получаем общее количество
        count_query = f"SELECT COUNT(*) as total FROM battles b WHERE {where_clause}"
        total_result = await self._execute_one(count_query, *params)
        total = total_result["total"]
        
        # Получаем результаты поиска
        search_query = f"""
            SELECT b.id, b.ts, b.battle_type, b.turns, b.loc_x, b.loc_y,
                   b.source_id,
                   array_agg(DISTINCT p.login) as players,
                   COALESCE(SUM(bm.count), 0) as monsters_count
            FROM battles b
            LEFT JOIN battle_participants bp ON b.id = bp.battle_id
            LEFT JOIN players p ON bp.player_id = p.id
            LEFT JOIN battle_monsters bm ON b.id = bm.battle_id
            WHERE {where_clause}
            GROUP BY b.id, b.ts, b.battle_type, b.turns, b.loc_x, b.loc_y, b.source_id
            ORDER BY b.id DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """
        
        params.extend([limit, offset])
        battles = await self._execute_query(search_query, *params)
        
        # Преобразуем в нужный формат
        for battle in battles:
            battle["players"] = list(set(battle["players"])) if battle["players"] else []
            battle["location"] = [battle["loc_x"], battle["loc_y"]] if battle["loc_x"] is not None else None
            battle["duration"] = battle.get("turns", 0)  # ✅ Количество ходов
        
        return battles, total
    
    async def find_new_files(self, logs_base: str) -> List[str]:
        """Поиск новых файлов логов"""
        logs_path = Path(logs_base)
        if not logs_path.exists():
            return []
        
        # Получаем список уже обработанных файлов
        processed_query = "SELECT storage_key FROM battles WHERE storage_key IS NOT NULL"
        processed_files = await self._execute_query(processed_query)
        processed_set = {row["storage_key"] for row in processed_files}
        
        # Ищем новые .tzb файлы
        new_files = []
        for tzb_file in logs_path.glob("*.tzb"):
            if str(tzb_file) not in processed_set:
                new_files.append(str(tzb_file))
        
        return new_files

    async def get_storage_key(self, battle_id: int) -> Optional[str]:
        """Вернуть путь к исходному файлу лога, если сохранён"""
        result = await self._execute_one("SELECT storage_key FROM battles WHERE id = $1", battle_id)
        return result["storage_key"] if result and result.get("storage_key") else None
    
    async def get_battle_raw_data(self, battle_id: int) -> Optional[str]:
        """Получение сырых данных боя"""
        query = "SELECT data FROM battles WHERE id = $1"
        result = await self._execute_one(query, battle_id)
        if result and result["data"]:
            return json.dumps(result["data"], ensure_ascii=False, indent=2)
        return None
    
    async def health_check(self) -> bool:
        """Проверка здоровья БД"""
        try:
            await self._execute_one("SELECT 1")
            return True
        except Exception:
            return False
