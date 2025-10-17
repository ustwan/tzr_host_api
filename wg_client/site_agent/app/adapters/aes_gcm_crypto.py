"""
Реализация AES-GCM шифрования/расшифровки
"""
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

from ..ports.crypto import AesGcmCrypto


class AesGcmCryptoImpl(AesGcmCrypto):
    """
    AES-GCM шифрование/расшифровка
    
    Формат зашифрованных данных (base64):
        nonce (12 байт) || tag (16 байт) || ciphertext
    """
    
    def __init__(self, key_base64: str):
        """
        Args:
            key_base64: AES ключ в base64 (256 бит = 32 байта)
        """
        key_bytes = base64.b64decode(key_base64)
        if len(key_bytes) != 32:
            raise ValueError("AES-GCM ключ должен быть 256 бит (32 байта)")
        
        self._aesgcm = AESGCM(key_bytes)
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Расшифровать AES-GCM данные
        
        Args:
            encrypted_data: Base64 строка формата: nonce || tag || ciphertext
            
        Returns:
            Расшифрованная строка (UTF-8)
            
        Raises:
            ValueError: Если расшифровка не удалась (неверный ключ/поврежденные данные)
        """
        try:
            # Декодируем base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Извлекаем компоненты
            nonce = encrypted_bytes[:12]  # 12 байт
            tag = encrypted_bytes[12:28]  # 16 байт
            ciphertext = encrypted_bytes[28:]
            
            # AES-GCM расшифровка (tag проверяется автоматически)
            # Формат для AESGCM.decrypt: nonce, ciphertext+tag
            combined = ciphertext + tag
            plaintext_bytes = self._aesgcm.decrypt(nonce, combined, None)
            
            return plaintext_bytes.decode('utf-8')
        
        except Exception as e:
            raise ValueError(f"AES-GCM расшифровка не удалась: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Зашифровать данные с помощью AES-GCM
        
        Args:
            plaintext: Исходная строка
            
        Returns:
            Base64 строка формата: nonce || tag || ciphertext
        """
        import os
        
        # Генерируем случайный nonce (96 бит = 12 байт)
        nonce = os.urandom(12)
        
        # Шифруем (возвращает ciphertext + tag)
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext_with_tag = self._aesgcm.encrypt(nonce, plaintext_bytes, None)
        
        # ciphertext_with_tag содержит: ciphertext || tag (16 байт в конце)
        # Разделяем
        tag = ciphertext_with_tag[-16:]
        ciphertext = ciphertext_with_tag[:-16]
        
        # Формируем: nonce || tag || ciphertext
        encrypted_bytes = nonce + tag + ciphertext
        
        return base64.b64encode(encrypted_bytes).decode('ascii')

