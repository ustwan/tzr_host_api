"""
XML Sync Worker - система синхронизации логов через HTTP воркеры
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.xml_worker_client import XmlWorkerClient
from app.database import BattleDatabase

logger = logging.getLogger(__name__)


class XmlSyncWorker:
    """Воркер для синхронизации логов через HTTP воркеры"""
    
    def __init__(self):
        self.db: Optional[BattleDatabase] = None
        self.worker_client = XmlWorkerClient()
    
    async def _init_db(self):
        if not self.db:
            self.db = BattleDatabase()
    
    async def _close_db(self):
        if self.db:
            await self.db.disconnect()
    
    async def check_workers_health(self) -> Dict[str, Any]:
        """Проверить здоровье всех HTTP воркеров"""
        return await self.worker_client.check_workers_health()
    
    async def sync_range(
        self, 
        start_id: int, 
        end_id: int, 
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Синхронизация диапазона через HTTP воркеры
        """
        from app.xml_sync_state import get_sync_state
        
        await self._init_db()
        state = get_sync_state()
        
        # Получаем уже запрошенные ID
        skip_ids = set()
        if skip_existing:
            rows = await self.db._execute_query(
                "SELECT battle_id FROM xml_sync_log WHERE battle_id BETWEEN $1 AND $2 AND status = 'success'",
                start_id, end_id
            )
            skip_ids = {row['battle_id'] for row in rows}
        
        # Формируем список ID для загрузки
        to_download = [bid for bid in range(start_id, end_id + 1) if bid not in skip_ids]
        
        if not to_download:
            await self._close_db()
            return {
                "start_id": start_id,
                "end_id": end_id,
                "total_range": end_id - start_id + 1,
                "success": 0,
                "failed": 0,
                "skipped": len(skip_ids),
                "timeout": 0,
                "message": "Все бои уже синхронизированы"
            }
        
        # Используем HTTP воркеры для параллельной загрузки
        logger.info(f"Запуск параллельной загрузки {len(to_download)} боев через HTTP воркеры")
        
        # Воркеры САМИ отправляют в api_mother, нам нужно только собрать результаты
        worker_results = await self.worker_client.fetch_battles_parallel(
            battle_ids=to_download,
            upload_to_mother=True,
            batch_size=10  # 10 логов на батч
        )
        
        # Сохраняем результаты в БД (BATCH INSERT для производительности)
        results = worker_results.get('results', [])
        if results:
            # Подготавливаем данные для batch insert
            values_list = []
            now = datetime.utcnow()
            
            for result in results:
                battle_id = result.get('battle_id')
                status = result.get('status')
                error = result.get('error')
                size_bytes = result.get('size_bytes')
                uploaded = result.get('uploaded_to_mother', False)
                
                # Определяем file_path (если загружено в mother)
                file_path = None
                if uploaded and status == 'success':
                    # Путь в формате который использует api_mother
                    shard = battle_id // 50000
                    file_path = f"/srv/btl/raw/{shard}/{battle_id}.tzb"
                
                values_list.append((
                    battle_id,
                    now,
                    status,
                    error,
                    file_path,
                    size_bytes
                ))
            
            # Выполняем batch insert (1 запрос вместо N)
            if values_list:
                # Batch INSERT - выполняем по одному (пока нет executemany в BattleDatabase)
                for vals in values_list:
                    query = """
                        INSERT INTO xml_sync_log (battle_id, requested_at, status, error_message, file_path, size_bytes)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (battle_id) DO UPDATE SET
                            requested_at = EXCLUDED.requested_at,
                            status = EXCLUDED.status,
                            error_message = EXCLUDED.error_message,
                            file_path = EXCLUDED.file_path,
                            size_bytes = EXCLUDED.size_bytes
                    """
                    await self.db._execute_query(query, *vals)
                
                logger.info(f"📊 Сохранено в БД: {len(values_list)} записей")
        
        success_count = worker_results.get('success', 0)
        failed_count = worker_results.get('failed', 0)
        timeout_count = worker_results.get('timeout', 0)
        
        await self._close_db()
        
        return {
            "start_id": start_id,
            "end_id": end_id,
            "total_range": end_id - start_id + 1,
            "success": success_count,
            "failed": failed_count,
            "skipped": len(skip_ids),
            "timeout": timeout_count,
            "workers_used": worker_results.get('workers_used', 6),
            "worker_stats": worker_results.get('worker_stats', {})
        }
    
    async def sync_missing(self, limit: int = 100) -> Dict[str, Any]:
        """
        Докачать бои с ошибками (failed, response_timeout)
        """
        await self._init_db()
        
        # Получаем бои с ошибками
        rows = await self.db._execute_query(
            """
            SELECT battle_id 
            FROM xml_sync_log 
            WHERE status IN ('failed', 'response_timeout')
            ORDER BY battle_id DESC
            LIMIT $1
            """,
            limit
        )
        
        battle_ids = [row['battle_id'] for row in rows]
        
        if not battle_ids:
            await self._close_db()
            return {
                "message": "Нет боев для докачки",
                "success": 0,
                "failed": 0,
                "timeout": 0
            }
        
        logger.info(f"Докачка {len(battle_ids)} боев с ошибками")
        
        # Используем HTTP воркеры
        worker_results = await self.worker_client.fetch_battles_parallel(
            battle_ids=battle_ids,
            upload_to_mother=True,
            batch_size=10  # 10 логов на батч
        )
        
        # Обновляем результаты в БД (BATCH UPDATE для производительности)
        results = worker_results.get('results', [])
        if results:
            values_list = []
            now = datetime.utcnow()
            
            for result in results:
                battle_id = result.get('battle_id')
                status = result.get('status')
                error = result.get('error')
                size_bytes = result.get('size_bytes')
                uploaded = result.get('uploaded_to_mother', False)
                
                file_path = None
                if uploaded and status == 'success':
                    shard = battle_id // 50000
                    file_path = f"/srv/btl/raw/{shard}/{battle_id}.tzb"
                
                values_list.append((
                    now,
                    status,
                    error,
                    file_path,
                    size_bytes,
                    battle_id
                ))
            
            # Batch UPDATE - выполняем по одному (пока нет executemany)
            if values_list:
                for vals in values_list:
                    query = """
                        UPDATE xml_sync_log 
                        SET requested_at = $1, status = $2, error_message = $3, 
                            file_path = $4, size_bytes = $5
                        WHERE battle_id = $6
                    """
                    await self.db._execute_query(query, *vals)
                
                logger.info(f"📊 Обновлено в БД: {len(values_list)} записей")
        
        await self._close_db()
        
        return {
            "attempted": len(battle_ids),
            "success": worker_results.get('success', 0),
            "failed": worker_results.get('failed', 0),
            "timeout": worker_results.get('timeout', 0),
            "workers_used": worker_results.get('workers_used', 6)
        }
    
    async def sync_auto_continue(self, batch_size: int = 1000) -> Dict[str, Any]:
        """
        Автоматическая синхронизация: продолжить с последнего успешного боя
        """
        await self._init_db()
        
        # Находим последний успешно загруженный бой
        last_success = await self.db._execute_one(
            """
            SELECT MAX(battle_id) as max_id 
            FROM xml_sync_log 
            WHERE status = 'success'
            """
        )
        
        last_id = last_success['max_id'] if last_success and last_success['max_id'] else 1475356
        
        # Определяем диапазон для загрузки (от последнего + 1)
        start_id = last_id + 1
        end_id = min(start_id + batch_size - 1, 3767706)  # Не превышаем известный максимум
        
        await self._close_db()
        
        if start_id > 3767706:
            return {
                "message": "Все доступные бои уже синхронизированы",
                "last_synced": last_id,
                "next_available": None
            }
        
        # Запускаем синхронизацию диапазона
        result = await self.sync_range(start_id, end_id, skip_existing=True)
        result["last_synced_before"] = last_id
        result["auto_continue"] = True
        
        return result
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Получить статус синхронизации"""
        await self._init_db()
        
        stats = await self.db._execute_one(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'success') as success,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'response_timeout') as timeout,
                MAX(battle_id) FILTER (WHERE status = 'success') as last_success,
                MIN(battle_id) FILTER (WHERE status = 'success') as first_success
            FROM xml_sync_log
            """
        )
        
        await self._close_db()
        
        return {
            "total_requested": int(stats['total']) if stats['total'] else 0,
            "success": int(stats['success']) if stats['success'] else 0,
            "failed": int(stats['failed']) if stats['failed'] else 0,
            "timeout": int(stats['timeout']) if stats['timeout'] else 0,
            "last_success_id": stats['last_success'],
            "first_success_id": stats['first_success']
        }
    
    async def get_requested_battles(
        self,
        limit: int = 50,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получить список запрошенных боев"""
        await self._init_db()
        
        query = "SELECT battle_id, requested_at, status, error_message, file_path, size_bytes FROM xml_sync_log"
        params = []
        
        if status:
            query += " WHERE status = $1"
            params.append(status)
        
        query += " ORDER BY battle_id DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        rows = await self.db._execute_query(query, *params)
        
        await self._close_db()
        
        battles = []
        for row in rows:
            battles.append({
                "battle_id": row['battle_id'],
                "requested_at": row['requested_at'].isoformat() if row['requested_at'] else None,
                "status": row['status'],
                "error_message": row['error_message'],
                "file_path": row['file_path'],
                "size_bytes": row['size_bytes']
            })
        
        return {
            "battles": battles,
            "count": len(battles)
        }
