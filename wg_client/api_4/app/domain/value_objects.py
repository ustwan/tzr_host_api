from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlayerLogin:
    value: str

    def __post_init__(self):
        if not (1 <= len(self.value) <= 32):
            raise ValueError("invalid player login length")


@dataclass(frozen=True)
class ClanName:
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("empty clan name")



