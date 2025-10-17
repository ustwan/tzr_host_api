"""
Главная точка входа WebSocket агента
"""
import asyncio
import signal
import time
import uuid
from typing import Optional

from ..domain.dto import JobMessage, ResultMessage, AgentConfig
from ..adapters.hmac_signer import HmacSha256Signer
from ..adapters.aes_gcm_crypto import AesGcmCryptoImpl
from ..adapters.http_local_api_client import HttpLocalApiClient
from ..adapters.ws_client import WsClientImpl
from ..usecases.process_register import ProcessRegisterUseCase
from ..usecases.process_server_status import ProcessServerStatusUseCase
from ..infrastructure.config import load_config
from shared.utils.logger import setup_logger


logger = setup_logger(__name__)


class SiteAgent:
    """
    WebSocket агент для обработки задач от сайта
    
    Orchestrator всех use cases и адаптеров
    """
    
    def __init__(self, config: AgentConfig):
        """
        Args:
            config: Конфигурация агента из ENV
        """
        self.config = config
        
        # Криптография
        self.hmac_signer = HmacSha256Signer(config.hmac_secret)
        self.aes_crypto = AesGcmCryptoImpl(config.aes_gcm_key)
        
        # HTTP клиент для локальных API
        self.api_client = HttpLocalApiClient(
            register_url=config.local_register_url,
            status_url=config.local_status_url,
            timeout=config.request_timeout
        )
        
        # Use Cases
        self.register_uc = ProcessRegisterUseCase(
            crypto=self.aes_crypto,
            hmac_signer=self.hmac_signer,
            api_client=self.api_client,
            job_ttl=config.job_ttl
        )
        
        self.status_uc = ProcessServerStatusUseCase(
            hmac_signer=self.hmac_signer,
            api_client=self.api_client,
            job_ttl=config.job_ttl
        )
        
        # WebSocket клиент
        self.ws_client = WsClientImpl(
            ws_url=config.site_ws_url,
            auth_jwt=config.auth_jwt,
            ping_interval=config.ws_ping_interval,
            reconnect_backoff_min=config.reconnect_backoff_min,
            reconnect_backoff_max=config.reconnect_backoff_max
        )
        
        # Graceful shutdown
        self._should_stop = False
    
    async def handle_job(self, job: JobMessage) -> ResultMessage:
        """
        Обработать задачу и создать результат
        
        Args:
            job: Задача от сайта
            
        Returns:
            ResultMessage с результатом обработки
        """
        start_time = time.time()
        
        try:
            # Выбираем обработчик по типу задачи
            if job.job_type == "register":
                result_data = await self.register_uc.execute(
                    job_id=job.id,
                    payload=job.payload,
                    ts=job.ts,
                    nonce=job.nonce,
                    sig=job.sig
                )
                
                # RegisterResult -> dict
                result_payload = {
                    "ok": result_data.ok,
                    "user_id": result_data.user_id,
                    "error": result_data.error
                }
                
                ok = result_data.ok
                error = result_data.error
            
            elif job.job_type == "get_server_status":
                result_data = await self.status_uc.execute(
                    job_id=job.id,
                    payload=job.payload,
                    ts=job.ts,
                    nonce=job.nonce,
                    sig=job.sig
                )
                
                # ServerStatusResult -> dict
                result_payload = {
                    "server_status": result_data.server_status,
                    "rates": result_data.rates,
                    "generated_at": result_data.generated_at,
                    "revision": result_data.revision
                }
                
                ok = True
                error = None
            
            else:
                # Неизвестный тип задачи
                logger.error(f"Неизвестный тип задачи: {job.job_type}")
                result_payload = None
                ok = False
                error = f"Unknown job_type: {job.job_type}"
        
        except ValueError as e:
            # Ошибки валидации (TTL, HMAC, и т.д.)
            logger.error(f"Задача {job.id}: ошибка валидации: {e}")
            result_payload = None
            ok = False
            error = str(e)
        
        except ConnectionError as e:
            # Локальный API недоступен
            logger.error(f"Задача {job.id}: локальный API недоступен: {e}")
            result_payload = None
            ok = False
            error = str(e)
        
        except Exception as e:
            # Неожиданная ошибка
            logger.error(f"Задача {job.id}: неожиданная ошибка: {e}", exc_info=True)
            result_payload = None
            ok = False
            error = f"Unexpected error: {e}"
        
        # Создаем ResultMessage
        result = ResultMessage(
            type="result",
            id=job.id,
            ok=ok,
            result=result_payload if ok else None,
            error=error,
            ts=int(time.time()),
            nonce=str(uuid.uuid4()),
            sig=""  # Заполним ниже
        )
        
        # Подписываем HMAC
        result_dict = {
            "type": result.type,
            "id": result.id,
            "ok": result.ok,
            "result": result.result,
            "error": result.error,
            "ts": result.ts,
            "nonce": result.nonce
        }
        
        result.sig = self.hmac_signer.sign(result_dict)
        
        duration = time.time() - start_time
        logger.info(
            f"Задача {job.id} обработана за {duration:.2f}s "
            f"(ok={ok}, type={job.job_type})"
        )
        
        return result
    
    async def run(self) -> None:
        """
        Запустить агента (основной цикл)
        """
        logger.info("=" * 60)
        logger.info("🚀 WebSocket Agent запускается...")
        logger.info(f"URL: {self.config.site_ws_url}")
        logger.info(f"Local Register: {self.config.local_register_url}")
        logger.info(f"Local Status: {self.config.local_status_url}")
        logger.info(f"Request Timeout: {self.config.request_timeout}s")
        logger.info(f"Ping Interval: {self.config.ws_ping_interval}s")
        logger.info("=" * 60)
        
        # Запускаем WebSocket цикл
        await self.ws_client.run(
            on_job=self.handle_job,
            reconnect=True
        )
    
    async def stop(self) -> None:
        """Graceful shutdown"""
        logger.info("Остановка агента...")
        self._should_stop = True
        await self.ws_client.stop()


async def main() -> None:
    """
    Главная функция (точка входа)
    """
    # Загружаем конфигурацию из ENV
    config = load_config()
    
    # Создаем агента
    agent = SiteAgent(config)
    
    # Graceful shutdown на SIGINT/SIGTERM
    loop = asyncio.get_event_loop()
    
    def shutdown_handler(sig):
        logger.info(f"Получен сигнал {sig}, остановка...")
        asyncio.create_task(agent.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: shutdown_handler(s))
    
    # Запускаем агента
    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt, остановка...")
        await agent.stop()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        await agent.stop()
        raise
    finally:
        logger.info("Агент остановлен")


if __name__ == "__main__":
    asyncio.run(main())

