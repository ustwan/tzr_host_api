"""
Порт для HTTP клиента к локальным API
"""
from abc import ABC, abstractmethod
from typing import Any, Optional


class LocalApiClient(ABC):
    """Интерфейс для вызова локальных API (API_2, API_1, API_Father)"""
    
    @abstractmethod
    async def call_register(
        self,
        login: str,
        password: str,
        gender: int,
        telegram_id: int,
        username: Optional[str],
        request_id: str
    ) -> dict[str, Any]:
        """
        Вызвать локальный API регистрации
        
        Args:
            login: Логин игрока
            password: Расшифрованный пароль
            gender: Пол (0 или 1)
            telegram_id: Telegram ID
            username: Telegram username (опционально)
            request_id: UUID задачи для идемпотентности
            
        Returns:
            {"ok": bool, "user_id": int | None, "error": str | None}
            
        Raises:
            TimeoutError: Если превышен таймаут
            ConnectionError: Если локальный API недоступен
        """
        pass
    
    @abstractmethod
    async def call_server_status(self) -> dict[str, Any]:
        """
        Вызвать локальный API для получения статуса сервера
        
        Returns:
            {"server_status": int, "rates": {...}, "constants": {...}}
            
        Raises:
            TimeoutError: Если превышен таймаут
            ConnectionError: Если локальный API недоступен
        """
        pass

