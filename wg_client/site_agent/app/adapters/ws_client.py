"""
Реализация WebSocket клиента с auto-reconnect
"""
import asyncio
import json
import random
from typing import Callable, Awaitable, Optional
import websockets
from websockets.client import WebSocketClientProtocol

from ..domain.dto import JobMessage, ResultMessage
from ..ports.websocket_client import WebSocketClient
from shared.utils.logger import setup_logger


logger = setup_logger(__name__)


class WsClientImpl(WebSocketClient):
    """
    WebSocket клиент к сайту с:
    - JWT авторизацией
    - Auto-reconnect с exponential backoff
    - Ping/pong keepalive
    - Graceful disconnect
    """
    
    def __init__(
        self,
        ws_url: str,
        auth_jwt: str,
        ping_interval: float = 20.0,
        reconnect_backoff_min: float = 3.0,
        reconnect_backoff_max: float = 30.0
    ):
        """
        Args:
            ws_url: WSS URL сайта (wss://site.example.com/ws/pull)
            auth_jwt: JWT токен для авторизации
            ping_interval: Интервал ping в секундах
            reconnect_backoff_min: Минимальный backoff при переподключении
            reconnect_backoff_max: Максимальный backoff при переподключении
        """
        self._ws_url = ws_url
        self._auth_jwt = auth_jwt
        self._ping_interval = ping_interval
        self._backoff_min = reconnect_backoff_min
        self._backoff_max = reconnect_backoff_max
        
        self._ws: Optional[WebSocketClientProtocol] = None
        self._current_backoff = reconnect_backoff_min
        self._is_connected = False
        self._should_stop = False
    
    async def connect(self) -> None:
        """
        Установить WebSocket соединение с JWT авторизацией
        """
        try:
            logger.info(f"Подключение к {self._ws_url}...")
            
            # Добавляем JWT в заголовок Authorization
            headers = {
                "Authorization": f"Bearer {self._auth_jwt}"
            }
            
            self._ws = await websockets.connect(
                self._ws_url,
                extra_headers=headers,
                ping_interval=self._ping_interval,
                ping_timeout=self._ping_interval * 2,
                close_timeout=10
            )
            
            self._is_connected = True
            self._current_backoff = self._backoff_min  # Сброс backoff после успешного подключения
            
            logger.info("✅ WebSocket подключен")
        
        except Exception as e:
            self._is_connected = False
            logger.error(f"❌ Ошибка подключения: {e}")
            raise ConnectionError(f"WebSocket connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Закрыть WebSocket соединение"""
        if self._ws and not self._ws.closed:
            logger.info("Закрытие WebSocket...")
            await self._ws.close()
            self._is_connected = False
            logger.info("WebSocket закрыт")
    
    async def send_result(self, result: ResultMessage) -> None:
        """
        Отправить результат обработки задачи
        """
        if not self._ws or self._ws.closed:
            raise ConnectionError("WebSocket не подключен")
        
        # Конвертируем dataclass в dict
        result_dict = {
            "type": result.type,
            "id": result.id,
            "ok": result.ok,
            "result": result.result,
            "error": result.error,
            "ts": result.ts,
            "nonce": result.nonce,
            "sig": result.sig
        }
        
        # Отправляем JSON
        message = json.dumps(result_dict, ensure_ascii=False)
        await self._ws.send(message)
        
        logger.debug(f"📤 Отправлен результат для задачи {result.id}")
    
    async def receive_job(self) -> Optional[JobMessage]:
        """
        Получить задачу от сайта
        
        Returns:
            JobMessage или None если таймаут/ошибка
        """
        if not self._ws or self._ws.closed:
            return None
        
        try:
            # Ждем сообщение (с таймаутом)
            message = await asyncio.wait_for(self._ws.recv(), timeout=60.0)
            
            # Парсим JSON
            data = json.loads(message)
            
            # Валидация типа сообщения
            if data.get("type") != "job":
                logger.warning(f"Получен неизвестный тип сообщения: {data.get('type')}")
                return None
            
            # Создаем JobMessage
            job = JobMessage(
                type="job",
                id=data["id"],
                job_type=data["job_type"],
                payload=data["payload"],
                ts=data["ts"],
                nonce=data["nonce"],
                sig=data["sig"]
            )
            
            logger.info(f"📥 Получена задача: {job.job_type} (id={job.id})")
            return job
        
        except asyncio.TimeoutError:
            # Таймаут - это нормально, просто нет задач
            return None
        
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Ошибка получения задачи: {e}")
            return None
    
    async def run(
        self,
        on_job: Callable[[JobMessage], Awaitable[ResultMessage]],
        reconnect: bool = True
    ) -> None:
        """
        Запустить основной цикл обработки задач с auto-reconnect
        
        Args:
            on_job: Async callback для обработки задачи
            reconnect: Автоматически переподключаться при разрыве
        """
        logger.info("🚀 Запуск WebSocket агента...")
        
        while not self._should_stop:
            try:
                # Подключаемся
                await self.connect()
                
                # Основной цикл обработки
                while self._is_connected and not self._should_stop:
                    # Получаем задачу
                    job = await self.receive_job()
                    
                    if job is None:
                        # Нет задач - продолжаем ждать
                        continue
                    
                    # Обрабатываем задачу
                    try:
                        result = await on_job(job)
                        await self.send_result(result)
                    except Exception as e:
                        logger.error(f"Ошибка обработки задачи {job.id}: {e}")
            
            except ConnectionError as e:
                logger.error(f"Разрыв соединения: {e}")
                self._is_connected = False
                
                if not reconnect or self._should_stop:
                    break
                
                # Exponential backoff с jitter
                jitter = random.uniform(0, self._current_backoff * 0.3)
                wait_time = min(self._current_backoff + jitter, self._backoff_max)
                
                logger.info(f"⏳ Переподключение через {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                
                # Увеличиваем backoff
                self._current_backoff = min(self._current_backoff * 2, self._backoff_max)
            
            except Exception as e:
                logger.error(f"Неожиданная ошибка в цикле: {e}", exc_info=True)
                
                if not reconnect or self._should_stop:
                    break
                
                await asyncio.sleep(self._backoff_min)
        
        # Graceful shutdown
        await self.disconnect()
        logger.info("WebSocket агент остановлен")
    
    async def stop(self) -> None:
        """Остановить агента (для graceful shutdown)"""
        logger.info("Остановка агента...")
        self._should_stop = True
        await self.disconnect()

