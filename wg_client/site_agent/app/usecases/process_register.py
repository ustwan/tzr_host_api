"""
UseCase для обработки задачи register
"""
import time
import uuid
from typing import Any

from ..domain.dto import RegisterPayload, RegisterResult
from ..ports.crypto import AesGcmCrypto, HmacSigner
from ..ports.local_api_client import LocalApiClient
from shared.utils.logger import setup_logger


logger = setup_logger(__name__)


class ProcessRegisterUseCase:
    """
    Обработка задачи register с:
    - HMAC верификацией
    - AES-GCM расшифровкой пароля
    - Идемпотентностью через request_id
    """
    
    def __init__(
        self,
        crypto: AesGcmCrypto,
        hmac_signer: HmacSigner,
        api_client: LocalApiClient,
        job_ttl: int = 45
    ):
        """
        Args:
            crypto: AES-GCM шифрование/расшифровка
            hmac_signer: HMAC подписи
            api_client: Клиент для локальных API
            job_ttl: TTL задачи в секундах
        """
        self._crypto = crypto
        self._hmac = hmac_signer
        self._api = api_client
        self._job_ttl = job_ttl
    
    async def execute(
        self,
        job_id: str,
        payload: dict[str, Any],
        ts: int,
        nonce: str,
        sig: str
    ) -> RegisterResult:
        """
        Обработать задачу register
        
        Args:
            job_id: UUID задачи
            payload: Payload с зашифрованным паролем
            ts: Timestamp задачи
            nonce: Nonce для защиты от replay
            sig: HMAC подпись
            
        Returns:
            RegisterResult с результатом регистрации
        """
        start_time = time.time()
        
        # 1. Проверка TTL
        current_ts = int(time.time())
        age = current_ts - ts
        
        if age > self._job_ttl:
            logger.warning(f"Задача {job_id} просрочена (возраст: {age}s, TTL: {self._job_ttl}s)")
            return RegisterResult(
                ok=False,
                error=f"Job expired (age={age}s, ttl={self._job_ttl}s)"
            )
        
        # 2. Проверка HMAC подписи (защита от подделки)
        # Воссоздаем исходные данные задачи
        job_data = {
            "type": "job",
            "id": job_id,
            "job_type": "register",
            "payload": payload,
            "ts": ts,
            "nonce": nonce
        }
        
        if not self._hmac.verify(job_data, sig):
            logger.error(f"Задача {job_id}: неверная HMAC подпись")
            return RegisterResult(
                ok=False,
                error="Invalid HMAC signature"
            )
        
        # 3. Парсинг payload
        try:
            login = payload["login"]
            password_encrypted = payload["password_encrypted"]
            gender = payload["gender"]
            telegram_id = payload["telegram_id"]
            username = payload.get("username")
        except KeyError as e:
            logger.error(f"Задача {job_id}: отсутствует поле {e}")
            return RegisterResult(
                ok=False,
                error=f"Missing field: {e}"
            )
        
        # 4. Расшифровка пароля (AES-GCM)
        try:
            password = self._crypto.decrypt(password_encrypted)
            logger.debug(f"Пароль расшифрован для {login}")
        except ValueError as e:
            logger.error(f"Задача {job_id}: ошибка расшифровки пароля: {e}")
            return RegisterResult(
                ok=False,
                error=f"Password decryption failed: {e}"
            )
        
        # 5. Вызов локального API регистрации
        # request_id = job_id для идемпотентности
        try:
            result = await self._api.call_register(
                login=login,
                password=password,
                gender=gender,
                telegram_id=telegram_id,
                username=username,
                request_id=job_id  # ← Идемпотентность!
            )
            
            duration = time.time() - start_time
            
            if result["ok"]:
                logger.info(
                    f"✅ Регистрация успешна: {login} (user_id={result['user_id']}, "
                    f"duration={duration:.2f}s)"
                )
                return RegisterResult(
                    ok=True,
                    user_id=result["user_id"]
                )
            else:
                logger.warning(
                    f"❌ Регистрация не удалась: {login} (error={result['error']}, "
                    f"duration={duration:.2f}s)"
                )
                return RegisterResult(
                    ok=False,
                    error=result["error"]
                )
        
        except (TimeoutError, ConnectionError) as e:
            duration = time.time() - start_time
            logger.error(
                f"Задача {job_id}: локальный API недоступен ({e}, duration={duration:.2f}s)"
            )
            return RegisterResult(
                ok=False,
                error=f"Local API error: {e}"
            )

