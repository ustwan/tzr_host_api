"""
UseCase для обработки задачи get_server_status
"""
import time
from datetime import datetime, timezone
from typing import Any

from ..domain.dto import ServerStatusResult
from ..ports.crypto import HmacSigner
from ..ports.local_api_client import LocalApiClient
from shared.utils.logger import setup_logger


logger = setup_logger(__name__)


class ProcessServerStatusUseCase:
    """
    Обработка задачи get_server_status с:
    - HMAC верификацией
    - Нормализацией статуса
    - Монотонным revision
    """
    
    def __init__(
        self,
        hmac_signer: HmacSigner,
        api_client: LocalApiClient,
        job_ttl: int = 45
    ):
        """
        Args:
            hmac_signer: HMAC подписи
            api_client: Клиент для локальных API
            job_ttl: TTL задачи в секундах
        """
        self._hmac = hmac_signer
        self._api = api_client
        self._job_ttl = job_ttl
        self._last_revision = 0  # Монотонный счетчик
    
    async def execute(
        self,
        job_id: str,
        payload: dict[str, Any],
        ts: int,
        nonce: str,
        sig: str
    ) -> ServerStatusResult:
        """
        Обработать задачу get_server_status
        
        Args:
            job_id: UUID задачи
            payload: Payload (обычно пустой {})
            ts: Timestamp задачи
            nonce: Nonce для защиты от replay
            sig: HMAC подпись
            
        Returns:
            ServerStatusResult с нормализованным статусом
            
        Raises:
            ValueError: Если проверки не прошли
            ConnectionError: Если локальный API недоступен
        """
        start_time = time.time()
        
        # 1. Проверка TTL
        current_ts = int(time.time())
        age = current_ts - ts
        
        if age > self._job_ttl:
            logger.warning(f"Задача {job_id} просрочена (возраст: {age}s, TTL: {self._job_ttl}s)")
            raise ValueError(f"Job expired (age={age}s, ttl={self._job_ttl}s)")
        
        # 2. Проверка HMAC подписи
        job_data = {
            "type": "job",
            "id": job_id,
            "job_type": "get_server_status",
            "payload": payload,
            "ts": ts,
            "nonce": nonce
        }
        
        if not self._hmac.verify(job_data, sig):
            logger.error(f"Задача {job_id}: неверная HMAC подпись")
            raise ValueError("Invalid HMAC signature")
        
        # 3. Вызов локального API статуса
        try:
            data = await self._api.call_server_status()
            
            # 4. Нормализация результата
            server_status = data.get("server_status", 1)
            
            # Извлечение rates из различных форматов
            if "rates" in data:
                rates = data["rates"]
            elif "constants" in data:
                # Формат /internal/constants
                constants = data["constants"]
                rates = {
                    "exp": float(constants.get("RateExp", {}).get("value", 1.0)),
                    "pvp": float(constants.get("RatePvp", {}).get("value", 1.0)),
                    "pve": float(constants.get("RatePve", {}).get("value", 1.0)),
                    "color_mob": float(constants.get("RateColorMob", {}).get("value", 1.0)),
                    "skill": float(constants.get("RateSkill", {}).get("value", 1.0)),
                }
            else:
                # Дефолтные значения
                rates = {
                    "exp": 1.0,
                    "pvp": 1.0,
                    "pve": 1.0,
                    "color_mob": 1.0,
                    "skill": 1.0,
                }
            
            # 5. Генерация revision (монотонно растущий)
            # Используем unix timestamp как revision
            revision = int(time.time())
            
            # Убеждаемся что revision монотонный
            if revision <= self._last_revision:
                revision = self._last_revision + 1
            
            self._last_revision = revision
            
            # 6. ISO 8601 timestamp
            generated_at = datetime.now(timezone.utc).isoformat()
            
            duration = time.time() - start_time
            logger.info(
                f"✅ Статус сервера получен (server_status={server_status}, "
                f"revision={revision}, duration={duration:.2f}s)"
            )
            
            return ServerStatusResult(
                server_status=server_status,
                rates=rates,
                generated_at=generated_at,
                revision=revision
            )
        
        except (TimeoutError, ConnectionError) as e:
            duration = time.time() - start_time
            logger.error(
                f"Задача {job_id}: локальный API недоступен ({e}, duration={duration:.2f}s)"
            )
            raise ConnectionError(f"Local API error: {e}")

