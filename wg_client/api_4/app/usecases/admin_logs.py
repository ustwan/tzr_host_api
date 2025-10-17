from typing import Dict, Any


class AdminLogsUseCase:
    """Use case: административные операции над загрузкой логов."""

    def __init__(self, loader):
        self._loader = loader

    async def loading_stats(self) -> Dict[str, Any]:
        return await self._loader.get_loading_stats()

    async def cleanup(self, *, days_old: int) -> int:
        return await self._loader.cleanup_old_logs(days_old)



