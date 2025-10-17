from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Battle:
    id: int
    players: List[str]
    battle_type: Optional[str] = None



