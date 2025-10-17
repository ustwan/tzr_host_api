"""
XML Worker Client - HTTP клиент для общения с воркерами
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class XmlWorkerConfig:
    """Конфигурация XML воркеров"""
    
    WORKERS = [
        {"id": 1, "url": "http://host-api-xml-worker-1:9001", "account": "Sova Oasis"},
        {"id": 2, "url": "http://host-api-xml-worker-2:9002", "account": "Sova Neva"},
        {"id": 3, "url": "http://host-api-xml-worker-3:9003", "account": "Sova Jerusalem"},
        {"id": 4, "url": "http://host-api-xml-worker-4:9004", "account": "Sova Kabul"},
        {"id": 5, "url": "http://host-api-xml-worker-5:9005", "account": "Sova SYN"},
        {"id": 6, "url": "http://host-api-xml-worker-6:9006", "account": "Sova Moscow"},
    ]


class XmlWorkerClient:
    """
    HTTP клиент для управления XML воркерами
    Распределяет задачи по воркерам и собирает результаты
    """
    
    def __init__(self):
        self.workers = XmlWorkerConfig.WORKERS
        self.timeout = httpx.Timeout(300.0, connect=5.0)  # 300 сек (5 мин) на batch запрос, 5 сек на подключение
    
    async def check_workers_health(self) -> Dict[str, Any]:
        """Проверить здоровье всех воркеров"""
        results = {}
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            tasks = []
            for worker in self.workers:
                tasks.append(self._check_worker_health(client, worker))
            
            health_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for worker, result in zip(self.workers, health_results):
                worker_id = worker["id"]
                if isinstance(result, Exception):
                    results[f"worker_{worker_id}"] = {
                        "status": "error",
                        "error": str(result),
                        "account": worker["account"]
                    }
                else:
                    results[f"worker_{worker_id}"] = result
        
        return results
    
    async def _check_worker_health(self, client: httpx.AsyncClient, worker: Dict[str, Any]) -> Dict[str, Any]:
        """Проверить здоровье одного воркера"""
        try:
            response = await client.get(f"{worker['url']}/health")
            response.raise_for_status()
            data = response.json()
            return {
                "status": "healthy",
                "account": data.get("account"),
                "worker_id": data.get("worker_id")
            }
        except Exception as e:
            raise Exception(f"Worker {worker['id']} unavailable: {e}")
    
    async def fetch_battle(self, battle_id: int, worker_id: int, upload_to_mother: bool = True) -> Dict[str, Any]:
        """
        Запросить лог боя у конкретного воркера
        
        Args:
            battle_id: ID боя
            worker_id: ID воркера (1-6)
            upload_to_mother: Отправить ли в API_MOTHER
        
        Returns:
            Результат запроса
        """
        worker = next((w for w in self.workers if w["id"] == worker_id), None)
        if not worker:
            return {
                "battle_id": battle_id,
                "worker_id": worker_id,
                "status": "failed",
                "error": f"Worker {worker_id} not found"
            }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{worker['url']}/fetch/{battle_id}"
                params = {"upload_to_mother": upload_to_mother}
                
                logger.info(f"Запрос боя {battle_id} у воркера {worker_id} ({worker['account']})")
                
                response = await client.post(url, params=params)
                response.raise_for_status()
                result = response.json()
                
                # Добавляем worker_id к результату
                result["worker_id"] = worker_id
                result["worker_account"] = worker["account"]
                
                return result
                
        except httpx.TimeoutException:
            logger.warning(f"Таймаут при запросе боя {battle_id} у воркера {worker_id}")
            return {
                "battle_id": battle_id,
                "worker_id": worker_id,
                "worker_account": worker["account"],
                "status": "response_timeout",
                "error": "Worker timeout"
            }
        except Exception as e:
            logger.error(f"Ошибка при запросе боя {battle_id} у воркера {worker_id}: {e}")
            return {
                "battle_id": battle_id,
                "worker_id": worker_id,
                "worker_account": worker["account"],
                "status": "failed",
                "error": str(e)
            }
    
    async def fetch_battles_parallel(
        self,
        battle_ids: List[int],
        upload_to_mother: bool = True,
        use_batch: bool = True,
        batch_size: int = 10  # Размер батча на воркер
    ) -> Dict[str, Any]:
        """
        Параллельно запросить логи боев, распределив их по воркерам
        
        Args:
            battle_ids: Список ID боев
            upload_to_mother: Отправлять ли в API_MOTHER
            use_batch: Использовать batch endpoint (рекомендуется)
            batch_size: Размер батча на воркер
        
        Returns:
            Статистика выполнения
        """
        total = len(battle_ids)
        workers_count = len(self.workers)
        
        logger.info(f"Запуск параллельной загрузки {total} боев на {workers_count} воркерах (batch={'ON' if use_batch else 'OFF'})")
        
        if use_batch:
            # Новый метод: используем batch endpoint
            return await self._fetch_battles_batch(battle_ids, upload_to_mother, batch_size)
        else:
            # Старый метод: индивидуальные запросы (fallback)
            return await self._fetch_battles_individual(battle_ids, upload_to_mother)
    
    async def _fetch_battles_batch(
        self,
        battle_ids: List[int],
        upload_to_mother: bool,
        batch_size: int,
        concurrency_limit: int = 12  # Макс 12 параллельных батчей одновременно (по 2 на воркер)
    ) -> Dict[str, Any]:
        """
        Batch метод: Отправляем батчи боев каждому воркеру С ОГРАНИЧЕНИЕМ ПАРАЛЛЕЛИЗМА
        """
        from app.xml_sync_state import get_sync_state
        
        total = len(battle_ids)
        workers_count = len(self.workers)
        state = get_sync_state()
        
        # Распределяем бои по воркерам (round-robin)
        worker_batches = [[] for _ in range(workers_count)]
        for idx, battle_id in enumerate(battle_ids):
            worker_idx = idx % workers_count
            worker_batches[worker_idx].append(battle_id)
        
        # РАЗБИВАЕМ каждую пачку воркера на батчи по batch_size
        logger.info(f"Разбиваем на батчи по {batch_size} логов (concurrency={concurrency_limit})")
        
        # Создаём списки батчей для каждого воркера
        worker_batch_lists = []
        for worker_idx, worker in enumerate(self.workers):
            worker_battles = worker_batches[worker_idx]
            batches = []
            if worker_battles:
                for i in range(0, len(worker_battles), batch_size):
                    batch_chunk = worker_battles[i:i+batch_size]
                    batches.append((worker, batch_chunk))
            worker_batch_lists.append(batches)
        
        # ЧЕРЕДУЕМ батчи по воркерам (round-robin) для равномерной загрузки
        all_batches = []
        max_batches_per_worker = max((len(b) for b in worker_batch_lists), default=0)
        for batch_idx in range(max_batches_per_worker):
            for worker_batches_list in worker_batch_lists:
                if batch_idx < len(worker_batches_list):
                    all_batches.append(worker_batches_list[batch_idx])
        
        logger.info(f"Всего батчей: {len(all_batches)}, concurrency_limit={concurrency_limit}")
        
        # Выполняем батчи с ограничением параллелизма
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            semaphore = asyncio.Semaphore(concurrency_limit)
            all_results = []
            worker_stats = {}
            aborted = False
            
            async def process_batch(worker, batch_chunk):
                """Обработать один батч с семафором"""
                async with semaphore:
                    # Проверка abort перед каждым батчем
                    if state.check_abort():
                        logger.warning(f"⚠️ Прерывание: пропускаем батч воркера {worker['id']}")
                        return None
                    
                    result = await self._fetch_worker_batch(
                        client,
                        worker,
                        batch_chunk,
                        upload_to_mother,
                        batch_size
                    )
                    
                    # Обновляем прогресс
                    await state.update_progress(
                        success=result.get("success", 0),
                        failed=result.get("failed", 0) + result.get("timeout", 0)
                    )
                    
                    return result
            
            # Запускаем все батчи с ограничением параллелизма
            tasks = [process_batch(worker, batch_chunk) for worker, batch_chunk in all_batches]
            batch_results = await asyncio.gather(*tasks)
            
            # Проверяем если была команда abort
            if state.check_abort():
                aborted = True
                logger.warning("🛑 Операция прервана по запросу")
            
            # Разворачиваем результаты из батчей
            for batch_result in batch_results:
                if batch_result is None:  # Пропущено из-за abort
                    continue
                    
                worker_id = batch_result["worker_id"]
                worker_account = batch_result["worker_account"]
                
                # Добавляем результаты боев
                for result in batch_result["results"]:
                    result["worker_id"] = worker_id
                    result["worker_account"] = worker_account
                    all_results.append(result)
                
                # Статистика по воркеру
                if worker_id not in worker_stats:
                    worker_stats[worker_id] = {
                        "account": worker_account,
                        "total": 0,
                        "success": 0,
                        "failed": 0,
                        "timeout": 0
                    }
                worker_stats[worker_id]["total"] += batch_result["total"]
                worker_stats[worker_id]["success"] += batch_result["success"]
                worker_stats[worker_id]["failed"] += batch_result["failed"]
                worker_stats[worker_id]["timeout"] += batch_result["timeout"]
        
        # Общая статистика
        success_count = sum(1 for r in all_results if r.get("status") == "success")
        failed_count = sum(1 for r in all_results if r.get("status") == "failed")
        timeout_count = sum(1 for r in all_results if r.get("status") == "response_timeout")
        
        if aborted:
            logger.info(
                f"🛑 Прервано: {success_count} успешно, {failed_count} ошибок, {timeout_count} таймаутов (из {total} запрошенных)"
            )
        else:
            logger.info(
                f"✅ Batch завершён: {success_count} успешно, {failed_count} ошибок, {timeout_count} таймаутов"
            )
        
        return {
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "timeout": timeout_count,
            "workers_used": len(worker_stats),
            "worker_stats": worker_stats,
            "results": all_results,
            "aborted": aborted
        }
    
    async def _fetch_worker_batch(
        self,
        client: httpx.AsyncClient,
        worker: Dict[str, Any],
        battle_ids: List[int],
        upload_to_mother: bool,
        max_parallel: int
    ) -> Dict[str, Any]:
        """Отправить batch запрос одному воркеру"""
        try:
            # КРИТИЧЕСКИ ВАЖНО: Сортируем battle_ids по возрастанию!
            battle_ids_sorted = sorted(battle_ids)
            
            url = f"{worker['url']}/fetch_batch"
            payload = {
                "battle_ids": battle_ids_sorted,
                "max_parallel": max_parallel,
                "upload_to_mother": upload_to_mother
            }
            
            logger.info(f"Отправка batch запроса воркеру {worker['id']} ({worker['account']}): {len(battle_ids_sorted)} боев ({battle_ids_sorted[0]}-{battle_ids_sorted[-1]})")
            
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Добавляем информацию о воркере
            result["worker_id"] = worker["id"]
            result["worker_account"] = worker["account"]
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при batch запросе к воркеру {worker['id']}: {e}")
            # Возвращаем failed результаты для всех боев
            return {
                "worker_id": worker["id"],
                "worker_account": worker["account"],
                "total": len(battle_ids),
                "success": 0,
                "failed": len(battle_ids),
                "timeout": 0,
                "results": [
                    {
                        "battle_id": bid,
                        "status": "failed",
                        "error": f"Worker error: {str(e)}"
                    }
                    for bid in battle_ids
                ]
            }
    
    async def _fetch_battles_individual(
        self,
        battle_ids: List[int],
        upload_to_mother: bool
    ) -> Dict[str, Any]:
        """
        Старый метод: индивидуальные запросы (fallback)
        """
        total = len(battle_ids)
        workers_count = len(self.workers)
        
        # Распределяем бои по воркерам (round-robin)
        tasks = []
        for idx, battle_id in enumerate(battle_ids):
            worker_id = (idx % workers_count) + 1  # 1-based worker IDs
            tasks.append(self.fetch_battle(battle_id, worker_id, upload_to_mother))
        
        # Выполняем параллельно
        results = await asyncio.gather(*tasks)
        
        # Собираем статистику
        success_count = sum(1 for r in results if r.get("status") == "success")
        failed_count = sum(1 for r in results if r.get("status") == "failed")
        timeout_count = sum(1 for r in results if r.get("status") == "response_timeout")
        
        # Группируем по воркерам для статистики
        worker_stats = {}
        for result in results:
            worker_id = result.get("worker_id")
            if worker_id:
                if worker_id not in worker_stats:
                    worker_stats[worker_id] = {
                        "account": result.get("worker_account"),
                        "total": 0,
                        "success": 0,
                        "failed": 0,
                        "timeout": 0
                    }
                worker_stats[worker_id]["total"] += 1
                status = result.get("status")
                if status == "success":
                    worker_stats[worker_id]["success"] += 1
                elif status == "failed":
                    worker_stats[worker_id]["failed"] += 1
                elif status == "response_timeout":
                    worker_stats[worker_id]["timeout"] += 1
        
        logger.info(
            f"Завершено: {success_count} успешно, {failed_count} ошибок, {timeout_count} таймаутов"
        )
        
        return {
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "timeout": timeout_count,
            "workers_used": workers_count,
            "worker_stats": worker_stats,
            "results": results
        }


