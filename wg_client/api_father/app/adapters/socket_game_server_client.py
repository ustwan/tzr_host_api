import socket
import hashlib
import asyncio
import time


class SocketGameServerClient:
    def __init__(self):
        pass  # Не нужен executor
    
    def _encrypt(self, psw: str, key: str) -> str:
        s = (psw[0] + key[:10] + psw[1:] + key[10:]).replace(" ", "")
        h = hashlib.sha1(s.encode("ascii")).hexdigest().upper()
        indices = [30,26,24,39,2,15,1,4,5,18,27,38,10,19,33,17,7,36,34,31,8,14,23,21,29,3,32,25,37,20,28,11,22,16,35,0,6,9,13,12]
        return "".join(h[i] for i in indices)

    def _sync_register(self, host: str, port: int, xml: str, max_retries: int = 3) -> None:
        """Синхронная отправка XML к game_server с retry механизмом"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Увеличенный timeout: 10 секунд
                with socket.create_connection((host, port), timeout=10.0) as sock:
                    sock.sendall(xml.encode("utf-8"))
                    sock.settimeout(10.0)
                    
                    # Простое чтение ответа
                    data = sock.recv(4096)
                    
                    if not data:
                        raise RuntimeError("game_server_no_response")
                    
                    # Парсим ответ
                    if b"\x00" in data:
                        msg, _ = data.split(b"\x00", 1)
                        txt = msg.decode("utf-8", "replace")
                        if txt.startswith("<OK"):
                            return  # ✅ Успех!
                        elif txt.startswith("<ERR"):
                            raise RuntimeError(f"game_server_error: {txt}")
                    
                    # Если получили данные без \x00, считаем успехом
                    return
                    
            except socket.timeout as e:
                last_error = RuntimeError(f"game_server_timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff: 0.5s, 1s, 1.5s
                    continue
                    
            except ConnectionRefusedError as e:
                last_error = RuntimeError(f"game_server_unreachable (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                    
            except Exception as e:
                last_error = RuntimeError(f"game_server_error: {e} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
        
        # Если все попытки провалились
        raise last_error if last_error else RuntimeError("game_server_unknown_error")

    async def register_user(self, *, host: str, port: int, login: str, password: str, gender: int) -> None:
        """Асинхронная регистрация через asyncio.to_thread с retry"""
        xml = f'<ADDUSER l="{login}" p="{self._encrypt(password, "0123456789ABCDEF0123456789ABCDEF")}" g="{gender}" m="test@test.ru"/>\x00'
        # Используем asyncio.to_thread вместо executor
        await asyncio.to_thread(self._sync_register, host, port, xml)



