"""
Реализация HTTP клиента для локальных API
"""
import aiohttp
import asyncio
from typing import Any, Optional

from ..ports.local_api_client import LocalApiClient


class HttpLocalApiClient(LocalApiClient):
    """
    HTTP клиент для вызова локальных API (API_2, API_1, API_Father)
    """
    
    def __init__(
        self,
        register_url: str,
        status_url: str,
        timeout: float = 8.0
    ):
        """
        Args:
            register_url: URL локального API регистрации
            status_url: URL локального API статуса
            timeout: Таймаут запроса в секундах
        """
        self._register_url = register_url
        self._status_url = status_url
        self._timeout = aiohttp.ClientTimeout(total=timeout)
    
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
        Вызвать POST /internal/register (или /register)
        
        Идемпотентность через X-Request-Id заголовок
        """
        payload = {
            "login": login,
            "password": password,
            "gender": gender,
            "telegram_id": telegram_id,
            "username": username,
            "request_id": request_id
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Request-Id": request_id
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(
                    self._register_url,
                    json=payload,
                    headers=headers
                ) as resp:
                    data = await resp.json()
                    
                    # Нормализация ответа
                    if resp.status == 200:
                        # Успешная регистрация
                        # Может быть {"ok": true, "user_id": 123} или просто {"ok": true}
                        return {
                            "ok": True,
                            "user_id": data.get("user_id"),
                            "error": None
                        }
                    else:
                        # Ошибка регистрации
                        error_msg = data.get("message") or data.get("error") or f"HTTP {resp.status}"
                        
                        # Детальные ошибки валидации
                        if "fields" in data:
                            field_errors = ", ".join(f"{k}: {v}" for k, v in data["fields"].items())
                            error_msg = f"{error_msg} ({field_errors})"
                        
                        return {
                            "ok": False,
                            "user_id": None,
                            "error": error_msg
                        }
        
        except asyncio.TimeoutError:
            return {
                "ok": False,
                "user_id": None,
                "error": f"Timeout after {self._timeout.total}s"
            }
        
        except aiohttp.ClientError as e:
            return {
                "ok": False,
                "user_id": None,
                "error": f"Connection error: {e}"
            }
        
        except Exception as e:
            return {
                "ok": False,
                "user_id": None,
                "error": f"Unexpected error: {e}"
            }
    
    async def call_server_status(self) -> dict[str, Any]:
        """
        Вызвать GET /internal/bonuses или /internal/constants
        
        Возвращает статус сервера и константы (рейты)
        """
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(self._status_url) as resp:
                    if resp.status != 200:
                        raise ConnectionError(f"Status API returned {resp.status}")
                    
                    data = await resp.json()
                    
                    # Нормализация ответа
                    # Если это /internal/constants - преобразуем в нужный формат
                    if isinstance(data, dict) and "ServerStatus" in data:
                        # Формат constants API
                        return {
                            "server_status": int(data.get("ServerStatus", {}).get("value", 1)),
                            "rates": {
                                "exp": float(data.get("RateExp", {}).get("value", 1.0)),
                                "pvp": float(data.get("RatePvp", {}).get("value", 1.0)),
                                "pve": float(data.get("RatePve", {}).get("value", 1.0)),
                                "color_mob": float(data.get("RateColorMob", {}).get("value", 1.0)),
                                "skill": float(data.get("RateSkill", {}).get("value", 1.0)),
                            },
                            "constants": data  # Полные данные
                        }
                    else:
                        # Прямой формат
                        return data
        
        except asyncio.TimeoutError:
            raise TimeoutError(f"Timeout after {self._timeout.total}s")
        
        except aiohttp.ClientError as e:
            raise ConnectionError(f"Connection error: {e}")

