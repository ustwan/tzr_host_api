"""
Реализация HMAC подписи
"""
import hmac
import hashlib
import json
from typing import Any

from ..ports.crypto import HmacSigner


class HmacSha256Signer(HmacSigner):
    """HMAC-SHA256 подпись для WebSocket сообщений"""
    
    def __init__(self, secret: str):
        """
        Args:
            secret: Общий секрет для HMAC
        """
        self._secret = secret.encode('utf-8')
    
    def sign(self, data: dict[str, Any]) -> str:
        """
        Создать HMAC-SHA256 подпись
        
        Канонический формат:
        - Сортировка ключей по алфавиту
        - JSON без пробелов (separators=(',', ':'))
        - ensure_ascii=False для поддержки UTF-8
        """
        # Исключаем поле sig если оно есть
        clean_data = {k: v for k, v in data.items() if k != 'sig'}
        
        # Канонический JSON (sorted keys, no spaces)
        canonical = json.dumps(
            clean_data,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False
        )
        
        # HMAC-SHA256
        signature = hmac.new(
            self._secret,
            canonical.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify(self, data: dict[str, Any], signature: str) -> bool:
        """
        Проверить HMAC-SHA256 подпись
        
        Использует constant-time сравнение для защиты от timing attacks
        """
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)

