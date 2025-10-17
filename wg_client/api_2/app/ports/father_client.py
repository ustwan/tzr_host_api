from typing import Mapping, Any


class FatherClient:
    async def register(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        raise NotImplementedError



