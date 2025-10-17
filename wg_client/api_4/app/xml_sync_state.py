"""
Глобальное состояние для XML Sync операций
"""
import asyncio
from typing import Optional
from datetime import datetime


class XmlSyncState:
    """Singleton для управления состоянием XML Sync операций"""
    
    _instance: Optional['XmlSyncState'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.abort_requested = False
        self.is_running = False
        self.current_operation: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.progress = {
            "total": 0,
            "processed": 0,
            "success": 0,
            "failed": 0
        }
        self._lock = asyncio.Lock()
    
    async def start_operation(self, operation_name: str, total: int):
        """Начать новую операцию"""
        async with self._lock:
            if self.is_running:
                raise RuntimeError(f"Операция уже выполняется: {self.current_operation}")
            self.is_running = True
            self.abort_requested = False
            self.current_operation = operation_name
            self.started_at = datetime.utcnow()
            self.progress = {
                "total": total,
                "processed": 0,
                "success": 0,
                "failed": 0
            }
    
    async def finish_operation(self):
        """Завершить текущую операцию"""
        async with self._lock:
            self.is_running = False
            self.current_operation = None
            self.abort_requested = False
    
    async def request_abort(self):
        """Запросить прерывание текущей операции"""
        async with self._lock:
            if not self.is_running:
                raise RuntimeError("Нет активных операций для прерывания")
            self.abort_requested = True
    
    def check_abort(self) -> bool:
        """Проверить запрос на прерывание (без async)"""
        return self.abort_requested
    
    async def update_progress(self, success: int = 0, failed: int = 0):
        """Обновить прогресс"""
        async with self._lock:
            self.progress["processed"] += (success + failed)
            self.progress["success"] += success
            self.progress["failed"] += failed
    
    async def get_status(self) -> dict:
        """Получить текущий статус"""
        async with self._lock:
            return {
                "is_running": self.is_running,
                "abort_requested": self.abort_requested,
                "current_operation": self.current_operation,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "progress": self.progress.copy()
            }


# Глобальный экземпляр
_state = XmlSyncState()


def get_sync_state() -> XmlSyncState:
    """Получить глобальное состояние"""
    return _state









