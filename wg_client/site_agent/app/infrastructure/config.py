"""
Загрузка конфигурации из переменных окружения
"""
import os
from ..domain.dto import AgentConfig


def load_config() -> AgentConfig:
    """
    Загрузить конфигурацию агента из ENV переменных
    
    Returns:
        AgentConfig с настройками
        
    Raises:
        ValueError: Если обязательные переменные не заданы
    """
    # Обязательные переменные
    site_ws_url = os.getenv("SITE_WS_URL")
    if not site_ws_url:
        raise ValueError("SITE_WS_URL не задан")
    
    auth_jwt = os.getenv("AUTH_JWT")
    if not auth_jwt:
        raise ValueError("AUTH_JWT не задан")
    
    hmac_secret = os.getenv("HMAC_SECRET")
    if not hmac_secret:
        raise ValueError("HMAC_SECRET не задан")
    
    aes_gcm_key = os.getenv("AES_GCM_KEY")
    if not aes_gcm_key:
        raise ValueError("AES_GCM_KEY не задан (base64 encoded 256-bit key)")
    
    # Опциональные с дефолтами
    local_register_url = os.getenv(
        "LOCAL_REGISTER_URL",
        "http://127.0.0.1:8082/register"
    )
    
    local_status_url = os.getenv(
        "LOCAL_STATUS_URL",
        "http://127.0.0.1:9000/internal/constants"
    )
    
    # Таймауты и интервалы
    request_timeout = float(os.getenv("REQUEST_TIMEOUT", "8.0"))
    ws_ping_interval = float(os.getenv("WS_PING_INTERVAL", "20.0"))
    
    # Backoff для реконнекта (в секундах)
    reconnect_backoff_min = float(os.getenv("RECONNECT_BACKOFF_MIN", "3.0"))
    reconnect_backoff_max = float(os.getenv("RECONNECT_BACKOFF_MAX", "30.0"))
    
    # TTL задачи
    job_ttl = int(os.getenv("JOB_TTL", "45"))
    
    return AgentConfig(
        site_ws_url=site_ws_url,
        auth_jwt=auth_jwt,
        hmac_secret=hmac_secret,
        aes_gcm_key=aes_gcm_key,
        local_register_url=local_register_url,
        local_status_url=local_status_url,
        request_timeout=request_timeout,
        ws_ping_interval=ws_ping_interval,
        reconnect_backoff_min=reconnect_backoff_min,
        reconnect_backoff_max=reconnect_backoff_max,
        job_ttl=job_ttl
    )

