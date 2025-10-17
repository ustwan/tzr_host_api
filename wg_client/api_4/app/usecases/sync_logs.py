from typing import Dict, Any


class SyncLogsUseCase:
    """Use case: синхронизировать/переобработать логи через существующий загрузчик."""

    def __init__(self, loader):
        self._loader = loader

    async def sync(self, base_dir: str) -> Dict[str, Any]:
        return await self._loader.sync_new_files(base_dir)

    async def reprocess(self) -> Dict[str, Any]:
        return await self._loader.reprocess_failed_files()



