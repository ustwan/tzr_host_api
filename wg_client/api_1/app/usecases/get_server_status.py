from typing import Mapping, Any
from ..ports.father_client import FatherClient


class GetServerStatusUseCase:
    def __init__(self, father: FatherClient):
        self._father = father

    async def execute(self) -> Mapping[str, Any]:
        consts = await self._father.get_constants()
        return {
            "server_status": consts.get("ServerStatus", {}).get("value"),
            "rates": {
                "exp": consts.get("RateExp", {}).get("value"),
                "pvp": consts.get("RatePvp", {}).get("value"),
                "pve": consts.get("RatePve", {}).get("value"),
                "color_mob": consts.get("RateColorMob", {}).get("value"),
                "skill": consts.get("RateSkill", {}).get("value"),
            },
            "client_status": consts.get("CLIENT_STATUS", {}).get("value"),
            "_meta": {k: v.get("description") for k, v in consts.items()},
        }



