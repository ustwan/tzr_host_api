from typing import Mapping, Any


class FatherClient:
    async def get_constants(self) -> Mapping[str, Any]:
        raise NotImplementedError



