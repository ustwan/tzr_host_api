import os
import httpx
from typing import Mapping, Any

from ..ports.father_client import FatherClient


class HttpFatherClient(FatherClient):
    def __init__(self, base_url: str | None = None):
        self._base = base_url or os.getenv("API_FATHER_URL", "http://api_father:9000")

    async def register(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f"{self._base}/internal/register", json=payload)
            return {"status": r.status_code, "content": r.content, "headers": dict(r.headers)}



