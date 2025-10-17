"""
Port для проверки членства в Telegram группе
"""
from abc import ABC, abstractmethod


class TelegramChecker(ABC):
    @abstractmethod
    async def is_user_in_group(self, telegram_id: int) -> bool:
        """Проверяет, состоит ли пользователь в требуемой группе"""
        pass











