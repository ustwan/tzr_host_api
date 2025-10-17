import httpx
from typing import Dict, Any, Optional

class HttpMotherClient:
    def __init__(self, base_url: str = "http://api_mother:8083"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def sync_logs(self) -> Dict[str, Any]:
        """Запускает синхронизацию логов через api_mother"""
        response = await self.client.post(f"{self.base_url}/sync")
        response.raise_for_status()
        return response.json()
    
    async def get_gz_file(self, path: str) -> bytes:
        """Получает .gz файл по пути через api_mother"""
        response = await self.client.get(f"{self.base_url}/gz/{path}")
        response.raise_for_status()
        return response.content
    
    async def health_check(self) -> bool:
        """Проверяет доступность api_mother"""
        try:
            response = await self.client.get(f"{self.base_url}/healthz")
            return response.status_code == 200
        except:
            return False
    
    async def close(self):
        """Закрывает HTTP-клиент"""
        await self.client.aclose()
    
    async def upload_battle_log(self, battle_id: int, xml_content: bytes) -> Dict[str, Any]:
        """Отправляет лог боя в api_mother для сохранения"""
        response = await self.client.post(
            f"{self.base_url}/upload/{battle_id}",
            content=xml_content,
            headers={"Content-Type": "application/xml"}
        )
        response.raise_for_status()
        return response.json()