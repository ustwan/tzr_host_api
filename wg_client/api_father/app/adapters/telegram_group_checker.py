"""
Проверка членства пользователя в Telegram группе через Bot API
"""
import os
import aiohttp
from typing import Optional


class TelegramGroupChecker:
    def __init__(self, bot_token: Optional[str] = None, required_group_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.required_group_id = required_group_id or os.getenv("TELEGRAM_REQUIRED_GROUP_ID")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def is_user_in_group(self, telegram_id: int) -> bool:
        """
        Проверяет, состоит ли пользователь в требуемой группе
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            True если пользователь в группе, False otherwise
        """
        if not self.bot_token or not self.required_group_id:
            # Если токен или группа не указаны, пропускаем проверку (для локальных тестов)
            return True
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/getChatMember",
                    params={
                        "chat_id": self.required_group_id,
                        "user_id": telegram_id
                    },
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            status = data.get("result", {}).get("status")
                            # Разрешенные статусы: member, administrator, creator
                            return status in ['member', 'administrator', 'creator']
                    
                    return False
        except Exception as e:
            # При ошибке API (сеть, таймаут) - НЕ блокируем регистрацию
            # Логируем ошибку для мониторинга
            print(f"Warning: Telegram group check failed: {e}")
            return True  # пропускаем в случае ошибки

