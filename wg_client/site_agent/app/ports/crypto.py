"""
Порты для криптографии (HMAC, AES-GCM)
"""
from abc import ABC, abstractmethod
from typing import Any


class HmacSigner(ABC):
    """Интерфейс для HMAC подписи и верификации"""
    
    @abstractmethod
    def sign(self, data: dict[str, Any]) -> str:
        """
        Создать HMAC подпись для данных
        
        Args:
            data: Словарь с данными (без поля 'sig')
            
        Returns:
            Hex строка HMAC подписи
        """
        pass
    
    @abstractmethod
    def verify(self, data: dict[str, Any], signature: str) -> bool:
        """
        Проверить HMAC подпись
        
        Args:
            data: Словарь с данными (без поля 'sig')
            signature: Hex строка HMAC подписи
            
        Returns:
            True если подпись валидна, иначе False
        """
        pass


class AesGcmCrypto(ABC):
    """Интерфейс для AES-GCM шифрования/расшифровки"""
    
    @abstractmethod
    def decrypt(self, encrypted_data: str) -> str:
        """
        Расшифровать AES-GCM зашифрованные данные
        
        Args:
            encrypted_data: Base64 строка с зашифрованными данными
                           Формат: base64(nonce || tag || ciphertext)
                           
        Returns:
            Расшифрованная строка (plaintext)
            
        Raises:
            ValueError: Если расшифровка не удалась
        """
        pass
    
    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """
        Зашифровать данные с помощью AES-GCM
        
        Args:
            plaintext: Исходная строка
            
        Returns:
            Base64 строка с зашифрованными данными
        """
        pass

