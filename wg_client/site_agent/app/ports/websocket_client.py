"""
Порт для WebSocket клиента
"""
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Optional
from ..domain.dto import JobMessage, ResultMessage


class WebSocketClient(ABC):
    """Интерфейс для WebSocket клиента к сайту"""
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Установить WebSocket соединение с сайтом
        
        Raises:
            ConnectionError: Если не удалось подключиться
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Закрыть WebSocket соединение"""
        pass
    
    @abstractmethod
    async def send_result(self, result: ResultMessage) -> None:
        """
        Отправить результат обработки задачи
        
        Args:
            result: Результат задачи
        """
        pass
    
    @abstractmethod
    async def receive_job(self) -> Optional[JobMessage]:
        """
        Получить задачу от сайта
        
        Returns:
            JobMessage если получено, None если таймаут/ошибка
        """
        pass
    
    @abstractmethod
    async def run(
        self,
        on_job: Callable[[JobMessage], Awaitable[ResultMessage]],
        reconnect: bool = True
    ) -> None:
        """
        Запустить основной цикл обработки задач
        
        Args:
            on_job: Callback для обработки задачи
            reconnect: Автоматически переподключаться при разрыве
        """
        pass

