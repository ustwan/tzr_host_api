from dataclasses import dataclass
from typing import Optional


@dataclass
class RegisterRequestDTO:
    login: str
    password: str
    gender: int
    telegram_id: int
    username: Optional[str] = None
    request_id: Optional[str] = None



