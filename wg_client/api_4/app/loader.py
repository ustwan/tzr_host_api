"""
Загрузчик данных для API_4
Потоковая загрузка и обработка файлов логов боёв
"""

import asyncio
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

from app.database import BattleDatabase
from .external_parser import run_new_parser, normalize_for_db
from app.utils import validate_battle_data, sanitize_filename, calculate_file_hash
from app.adapters.http_mother_client import HttpMotherClient
from shared.utils.settings import BaseSettings as Settings


class BattleLoader:
    """Загрузчик данных о боях"""
    
    def __init__(self, db: BattleDatabase):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # Настройки загрузки
        s = Settings()
        self.batch_size = s.batch_size
        self.max_workers = s.max_workers
        self.retry_attempts = s.retry_attempts
        self.retry_delay = s.retry_delay
    
    async def load_battles_from_directory(
        self, 
        directory: str, 
        pattern: str = "*.tzb*"
    ) -> Dict[str, Any]:
        """
        Загрузка всех боёв из директории
        
        Args:
            directory: Путь к директории с файлами
            pattern: Паттерн поиска файлов
            
        Returns:
            Статистика загрузки
        """
        directory_path = Path(directory)
        if not directory_path.exists():
            raise FileNotFoundError(f"Директория не найдена: {directory}")
        
        # Находим все файлы
        files = list(directory_path.glob(pattern))
        self.logger.info(f"Найдено {len(files)} файлов для обработки")
        
        if not files:
            return {
                "total_files": 0,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "errors": []
            }
        
        # Обрабатываем файлы батчами
        return await self._process_files_batch(files)
    
    async def load_battles_from_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Загрузка боёв из списка файлов
        
        Args:
            file_paths: Список путей к файлам
            
        Returns:
            Статистика загрузки
        """
        files = [Path(path) for path in file_paths if Path(path).exists()]
        return await self._process_files_batch(files)
    
    async def _process_files_batch(self, files: List[Path]) -> Dict[str, Any]:
        """Обработка файлов батчами"""
        total_files = len(files)
        processed = 0
        successful = 0
        failed = 0
        errors = []
        
        # Обрабатываем файлы батчами
        for i in range(0, total_files, self.batch_size):
            batch = files[i:i + self.batch_size]
            self.logger.info(f"Обрабатываем батч {i//self.batch_size + 1}: файлы {i+1}-{min(i+self.batch_size, total_files)}")
            
            # Создаем семафор для ограничения количества одновременных задач
            semaphore = asyncio.Semaphore(self.max_workers)
            
            # Создаем задачи для обработки файлов в батче
            tasks = [
                self._process_single_file(semaphore, file_path)
                for file_path in batch
            ]
            
            # Выполняем задачи
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            for result in results:
                processed += 1
                if isinstance(result, Exception):
                    failed += 1
                    error_msg = f"Ошибка обработки файла: {str(result)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                elif result:
                    successful += 1
                else:
                    failed += 1
                    error_msg = "Неизвестная ошибка обработки файла"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
        
        return {
            "total_files": total_files,
            "processed": processed,
            "successful": successful,
            "failed": failed,
            "errors": errors
        }
    
    async def _process_single_file(
        self, 
        semaphore: asyncio.Semaphore, 
        file_path: Path
    ) -> bool:
        """
        Обработка одного файла с повторными попытками
        
        Args:
            semaphore: Семафор для ограничения параллелизма
            file_path: Путь к файлу
            
        Returns:
            True, если файл успешно обработан
        """
        async with semaphore:
            for attempt in range(self.retry_attempts):
                try:
                    return await self._process_file_attempt(file_path)
                except Exception as e:
                    if attempt == self.retry_attempts - 1:
                        self.logger.error(f"Файл {file_path} не удалось обработать после {self.retry_attempts} попыток: {e}")
                        raise
                    else:
                        self.logger.warning(f"Попытка {attempt + 1} обработки файла {file_path} не удалась: {e}")
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
            
            return False
    
    async def _process_file_attempt(self, file_path: Path) -> bool:
        """
        Одна попытка обработки файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True, если файл успешно обработан
        """
        try:
            # Проверяем, не обработан ли уже файл
            if await self._is_file_already_processed(file_path):
                self.logger.debug(f"Файл {file_path} уже обработан, пропускаем")
                return True
            
            # Новый парсер — по умолчанию, без fallback.
            parsed = run_new_parser(str(file_path))
            battle_data = normalize_for_db(parsed)
            
            # КРИТИЧНО: Устанавливаем storage_key ПОСЛЕ парсинга
            battle_data["storage_key"] = str(file_path)
            
            # Валидируем данные
            is_valid, validation_errors = validate_battle_data(battle_data)
            if not is_valid:
                raise ValueError(f"Ошибки валидации: {', '.join(validation_errors)}")
            
            # ДЕБАГ: Проверяем profession перед сохранением
            meta_parts = battle_data.get('meta', {}).get('participants', [])
            for p in meta_parts:
                if not p.get('login', '').startswith('$'):
                    prof = p.get('profession')
                    self.logger.info(f"DEBUG: {p.get('login')} profession BEFORE save={prof} (type={type(prof).__name__})")
                    break
            
            # Сохраняем в БД
            await self.db.save_battle(battle_data)
            
            # Логируем успешную обработку
            self.logger.info(f"Файл {file_path} успешно обработан (ID: {battle_data['id']})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки файла {file_path}: {e}")
            raise
    
    async def _is_file_already_processed(self, file_path: Path) -> bool:
        """
        Проверка, обработан ли уже файл
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True, если файл уже обработан
        """
        try:
            # Проверяем по storage_key
            query = "SELECT 1 FROM battles WHERE storage_key = $1 LIMIT 1"
            result = await self.db._execute_one(query, str(file_path))
            return result is not None
        except Exception:
            return False
    
    async def sync_new_files(self, logs_base: str) -> Dict[str, Any]:
        """
        Синхронизация новых файлов
        
        Args:
            logs_base: Базовая директория с логами
            
        Returns:
            Статистика синхронизации
        """
        try:
            # 1) Тригерим синхронизацию через api_mother (если доступен)
            try:
                mother = HttpMotherClient()
                if await mother.health_check():
                    await mother.sync_logs()
                await mother.close()
            except Exception:
                pass

            # 2) Находим новые файлы в хранилище (лок. зеркало/смонтированный путь)
            new_files = await self.db.find_new_files(logs_base)
            
            if not new_files:
                return {
                    "new_files": 0,
                    "processed": 0,
                    "successful": 0,
                    "failed": 0,
                    "errors": []
                }
            
            self.logger.info(f"Найдено {len(new_files)} новых файлов для синхронизации")
            
            # 3) Обрабатываем новые файлы
            return await self.load_battles_from_files(new_files)
            
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации: {e}")
            return {
                "new_files": 0,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "errors": [str(e)]
            }
    
    async def reprocess_failed_files(self) -> Dict[str, Any]:
        """
        Повторная обработка файлов с ошибками
        
        Returns:
            Статистика повторной обработки
        """
        try:
            # Находим файлы с ошибками
            query = """
                SELECT storage_key, error_message 
                FROM battle_logs 
                WHERE status = 'error' 
                AND storage_key IS NOT NULL
            """
            failed_files = await self.db._execute_query(query)
            
            if not failed_files:
                return {
                    "failed_files": 0,
                    "processed": 0,
                    "successful": 0,
                    "failed": 0,
                    "errors": []
                }
            
            self.logger.info(f"Найдено {len(failed_files)} файлов с ошибками для повторной обработки")
            
            # Обрабатываем файлы
            file_paths = [row["storage_key"] for row in failed_files]
            return await self.load_battles_from_files(file_paths)
            
        except Exception as e:
            self.logger.error(f"Ошибка повторной обработки: {e}")
            return {
                "failed_files": 0,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "errors": [str(e)]
            }
    
    async def cleanup_old_logs(self, days_old: int = 30) -> int:
        """
        Очистка старых записей логов
        
        Args:
            days_old: Возраст записей в днях
            
        Returns:
            Количество удаленных записей
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Удаляем старые записи логов
            query = """
                DELETE FROM battle_logs 
                WHERE ingested_at < $1 
                AND status IN ('success', 'error')
            """
            result = await self.db._execute_command(query, cutoff_date)
            
            # Извлекаем количество удаленных записей из результата
            deleted_count = 0
            if "DELETE" in result:
                try:
                    deleted_count = int(result.split()[-1])
                except (ValueError, IndexError):
                    pass
            
            self.logger.info(f"Удалено {deleted_count} старых записей логов")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Ошибка очистки старых логов: {e}")
            return 0
    
    async def get_loading_stats(self) -> Dict[str, Any]:
        """
        Получение статистики загрузки
        
        Returns:
            Статистика загрузки
        """
        try:
            # Общая статистика
            total_battles_query = "SELECT COUNT(*) as total FROM battles"
            total_battles = await self.db._execute_one(total_battles_query)
            
            # Статистика по статусам
            status_query = """
                SELECT status, COUNT(*) as count 
                FROM battle_logs 
                GROUP BY status
            """
            status_stats = await self.db._execute_query(status_query)
            
            # Статистика по дням
            daily_query = """
                SELECT DATE(ingested_at) as date, COUNT(*) as count 
                FROM battle_logs 
                WHERE ingested_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(ingested_at)
                ORDER BY date DESC
            """
            daily_stats = await self.db._execute_query(daily_query)
            
            return {
                "total_battles": total_battles["total"] if total_battles else 0,
                "status_stats": {row["status"]: row["count"] for row in status_stats},
                "daily_stats": daily_stats,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики: {e}")
            return {
                "total_battles": 0,
                "status_stats": {},
                "daily_stats": [],
                "last_updated": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def process_file(self, file_path: str) -> Dict[str, Any]:
        """Обработать один файл"""
        try:
            result = await self._process_file_attempt(Path(file_path))
            if result:
                return {"battle_id": "processed", "status": "success"}
            else:
                return {"battle_id": None, "status": "failed"}
        except Exception as e:
            self.logger.error(f"Ошибка обработки файла {file_path}: {e}")
            return {"battle_id": None, "status": "error", "error": str(e)}
