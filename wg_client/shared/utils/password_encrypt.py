"""
Шифрование пароля для отправки на игровой сервер
Алгоритм взят из example/register.py
"""
import hashlib


def encrypt_password(password: str, key: str = "0123456789ABCDEF0123456789ABCDEF") -> str:
    """
    Шифрование пароля для игрового сервера
    
    Args:
        password: пароль пользователя
        key: ключ шифрования (32 символа)
    
    Returns:
        Зашифрованный пароль (40 символов)
    """
    # Формируем строку для хеширования
    concatenated_string = (
        password[0] + key[:10] + password[1:] + key[10:]
    ).replace(" ", "")
    
    # Генерируем SHA1-хеш строки
    sha1_hash = hashlib.sha1(concatenated_string.encode("ascii")).hexdigest().upper()
    
    # Индексы символов для извлечения из хеша
    indices = [
        30, 26, 24, 39, 2, 15, 1, 4, 5, 18,
        27, 38, 10, 19, 33, 17, 7, 36, 34, 31,
        8, 14, 23, 21, 29, 3, 32, 25, 37, 20,
        28, 11, 22, 16, 35, 0, 6, 9, 13, 12
    ]
    
    # Формируем результат из символов хеша по заданным индексам
    result = "".join(sha1_hash[index] for index in indices)
    
    return result











