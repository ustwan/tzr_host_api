from typing import Mapping, Any
from ..ports.father_client import FatherClient


class RegisterProxyUseCase:
    def __init__(self, father: FatherClient):
        self._father = father

    async def execute(self, payload: Mapping[str, Any]) -> tuple[int, bytes, str]:
        res = await self._father.register(payload)
        return res["status"], res["content"], res["headers"].get("content-type", "application/json")



