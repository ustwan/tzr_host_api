"""
Domain Transfer Objects для WebSocket сообщений
"""
from dataclasses import dataclass
from typing import Any, Literal, Optional
from datetime import datetime


@dataclass
class JobMessage:
    """Задача от сайта"""
    type: Literal["job"]
    id: str  # UUID задачи
    job_type: Literal["register", "get_server_status"]
    payload: dict[str, Any]
    ts: int  # Unix timestamp
    nonce: str  # UUID для защиты от replay
    sig: str  # Hex HMAC подпись


@dataclass
class ResultMessage:
    """Ответ агента на задачу"""
    type: Literal["result"]
    id: str  # UUID задачи (тот же что в JobMessage)
    ok: bool
    result: Optional[dict[str, Any]]
    error: Optional[str]
    ts: int  # Unix timestamp
    nonce: str  # UUID
    sig: str  # Hex HMAC подпись


@dataclass
class RegisterPayload:
    """Payload для задачи register"""
    login: str
    password_encrypted: str  # Зашифрованный AES-GCM пароль (base64)
    gender: int  # 0 или 1
    telegram_id: int
    username: Optional[str] = None


@dataclass
class RegisterResult:
    """Результат регистрации"""
    ok: bool
    user_id: Optional[int] = None
    error: Optional[str] = None


@dataclass
class ServerStatusResult:
    """Результат get_server_status"""
    server_status: int  # 1 = онлайн, 0 = офлайн
    rates: dict[str, float]  # exp, pvp, pve, color_mob, skill
    generated_at: str  # ISO 8601 timestamp
    revision: int  # Монотонно растущий счетчик


@dataclass
class AgentConfig:
    """Конфигурация агента из ENV"""
    site_ws_url: str
    auth_jwt: str
    hmac_secret: str
    aes_gcm_key: str  # Base64 encoded AES-GCM ключ
    local_register_url: str
    local_status_url: str
    request_timeout: float  # секунды
    ws_ping_interval: float  # секунды
    reconnect_backoff_min: float  # минимальный backoff (секунды)
    reconnect_backoff_max: float  # максимальный backoff (секунды)
    job_ttl: int = 45  # TTL задачи в секундах

