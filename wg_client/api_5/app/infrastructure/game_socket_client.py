"""Клиент для работы с игровым сервером через сокеты (с поддержкой сессий)"""
import socket
import xml.etree.ElementTree as ET
from typing import Optional, Tuple
from datetime import datetime
import hashlib


class GameSocketClient:
    """
    Клиент для работы с игровым сервером
    
    Поддерживает:
    - Аутентификацию ботов (как в XML Workers)
    - Управление сессиями
    - Отправку запросов магазина <SH />
    - Парсинг ответов
    
    Использует тот же метод авторизации что и XML Workers
    """
    
    def __init__(self, host: str = "185.92.72.18", port: int = 5190, timeout: int = 10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self.authenticated: bool = False
        self._sock: Optional[socket.socket] = None  # Сохраняем сокет после авторизации
    
    def connect(self) -> socket.socket:
        """Создать и подключить сокет"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        return sock
    
    def send_and_receive(self, request: str, end_tag: str) -> Optional[str]:
        """
        Отправить запрос и получить ответ
        
        Args:
            request: XML запрос
            end_tag: Тег окончания (например, "</LOGIN>" или "</SH>")
        
        Returns:
            XML ответ или None при ошибке
        """
        try:
            sock = self.connect()
            
            # Отправка запроса
            sock.sendall(request.encode('utf-8'))
            
            # Получение ответа
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                
                # Проверка окончания XML
                if end_tag.encode('utf-8') in response:
                    break
            
            sock.close()
            return response.decode('utf-8', errors='ignore')
            
        except socket.timeout:
            print(f"⏱ Timeout при запросе к {self.host}:{self.port}")
            return None
        except ConnectionRefusedError:
            print(f"❌ Не удалось подключиться к {self.host}:{self.port}")
            return None
        except Exception as e:
            print(f"❌ Ошибка при запросе: {e}")
            return None
    
    def authenticate(self, login: str, login_key: str) -> Tuple[bool, Optional[str]]:
        """
        Аутентификация бота в игре (как в XML Workers)
        
        Args:
            login: Логин бота (LOGIN_NAME)
            login_key: Ключ бота (LOGIN_KEY)
        
        Returns:
            (success, session_info or error_message)
        """
        try:
            # Создаём новое подключение
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            
            # Формат авторизации из XML Workers
            login_template = '<LOGIN v3="10.20.30.40" lang="ru" v2="4875537" v="108" p="{key}" l="{login_name}" />\x00'
            login_xml = login_template.format(key=login_key, login_name=login)
            
            # Отправляем логин
            sock.sendall(login_xml.encode('utf-8'))
            
            # Получаем ответ (может быть OK или ошибка)
            response = sock.recv(8192)
            
            # Отправляем GETME
            sock.sendall("<GETME />\x00".encode('utf-8'))
            
            # Ждём MYPARAM
            import time
            time.sleep(1.5)
            
            # Сохраняем сокет для дальнейшего использования
            self._sock = sock
            self.authenticated = True
            self.session_id = login  # Используем логин как идентификатор
            
            print(f"✓ Аутентификация {login}: успешно")
            return True, login
            
        except socket.timeout:
            print(f"⏱ Timeout при авторизации {login}")
            return False, "Timeout"
        except Exception as e:
            print(f"❌ Ошибка авторизации {login}: {e}")
            return False, str(e)
    
    def ping(self) -> bool:
        """
        Отправить keep-alive пинг (как в XML Workers)
        
        Returns:
            True если сессия жива
        """
        # DEBUG
        if not login or not login_key:
            print(f"⚠️  DEBUG: login={login}, login_key=SET" if login_key else f"⚠️  DEBUG: login={login}, login_key=NONE")
        
        if not self.authenticated or not self._sock:
            return False
        
        try:
            # Отправляем N (keep-alive)
            self._sock.sendall("<N />\x00".encode('utf-8'))
            return True
        except:
            self.authenticated = False
            return False
    
    def _is_socket_alive(self) -> bool:
        """Проверить что сокет еще живой"""
        if not self._sock:
            return False
        
        try:
            # Попытка получить данные без блокировки
            self._sock.setblocking(0)
            data = self._sock.recv(1, socket.MSG_PEEK)
            self._sock.setblocking(1)
            return len(data) > 0 or True
        except BlockingIOError:
            # Нет данных, но соединение живое
            self._sock.setblocking(1)
            return True
        except:
            # Соединение мертвое
            return False
    
    def _ensure_connected(self, login: str, login_key: str) -> bool:
        """Убедиться что соединение живое, иначе переподключиться"""
        if self.authenticated and self._is_socket_alive():
            return True
        
        # Переподключение
        print("  🔄 Переподключение к игровому серверу...")
        self.disconnect()
        success, _ = self.authenticate(login, login_key)
        if success:
            print("  ✓ Переподключение успешно")
        return success
    
    def fetch_shop_category(
        self, 
        category: str, 
        page: int = 0, 
        filter_str: str = "",
        login: str = None,
        login_key: str = None
    ) -> Optional[str]:
        """
        Запрос категории магазина (с auto-reconnect)
        
        Args:
            category: код категории (k, p, v, h, ...)
            page: номер страницы (с 0)
            filter_str: фильтр для групп (name:...,type:...)
            login: логин бота (для auto-reconnect)
            login_key: ключ бота (для auto-reconnect)
        
        Returns:
            XML строка ответа или None при ошибке
        """
        # DEBUG
        if not login or not login_key:
            print(f"⚠️  DEBUG: login={login}, login_key=SET" if login_key else f"⚠️  DEBUG: login={login}, login_key=NONE")
        
        if not self.authenticated or not self._sock:
            print("❌ Not authenticated. Call authenticate() first.")
            return None
        
        # Auto-reconnect при Broken pipe
        max_retries = 3  # 3 попытки: 0, 1, 2
        for attempt in range(max_retries):
            try:
                # Запрос магазина (аналог команды //blook в XML Workers)
                request = f'<SH c="{category}" s="{filter_str}" p="{page}" />\x00'
                self._sock.sendall(request.encode('utf-8'))
                
                # Получаем ответ до </SH>
                response = b""
                self._sock.settimeout(self.timeout)  # Используем timeout из конфига (20 сек)
                
                while True:
                    chunk = self._sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    
                    if b"</SH>" in response:
                        break
                
                # Декодирование и очистка
                xml_str = response.decode('utf-8', errors='replace')
                xml_str = xml_str.replace('\x00', '').replace('\x1f', '')
                
                # Извлечь только валидный XML (от <SH до </SH>)
                if '<SH' in xml_str and '</SH>' in xml_str:
                    start = xml_str.find('<SH')
                    end = xml_str.find('</SH>') + 5
                    xml_str = xml_str[start:end]
                
                return xml_str
                
            except socket.timeout:
                print(f"⏱ Timeout при запросе магазина")
                return None
            except Exception as e:
                # Проверка на Broken pipe
                error_msg = str(e)
                is_broken_pipe = (
                    isinstance(e, (BrokenPipeError, ConnectionResetError, OSError)) or
                    'Broken pipe' in error_msg or
                    'Connection reset' in error_msg
                )
                
                print(f"    🐛 DEBUG except: type={type(e).__name__}, is_broken={is_broken_pipe}, attempt={attempt}, has_creds={bool(login and login_key)}")
                
                if is_broken_pipe and attempt < max_retries - 1 and login and login_key:  # attempt < 2
                    print(f"    ⚠️  Broken pipe, переподключение...")
                    if self._ensure_connected(login, login_key):
                        continue  # Retry
                
                print(f"❌ Ошибка при запросе магазина: {e}")
                return None
        
        return None
    
    def disconnect(self):
        """Отключиться от игры (закрыть сессию)"""
        if self._sock:
            try:
                self._sock.close()
            except:
                pass
            self._sock = None
            
        self.session_id = None
        self.authenticated = False
        print("✓ Disconnected from game server")
    
    def __enter__(self):
        """Context manager: вход"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: выход (автоматическое отключение)"""
        self.disconnect()


class BotSessionManager:
    """
    Менеджер сессий ботов
    
    Управляет сессиями 3 ботов (moscow, oasis, neva):
    - Создание и хранение клиентов
    - Keep-alive пинги
    - Автоматическое переподключение
    """
    
    def __init__(self, host: str, port: int, timeout: int = 10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.clients: dict[str, GameSocketClient] = {}
        self.last_ping: dict[str, datetime] = {}
    
    def authenticate_bot(self, shop_code: str, login: str, password: str) -> Tuple[bool, str]:
        """
        Аутентифицировать бота
        
        Args:
            shop_code: moscow/oasis/neva
            login: логин бота
            password: пароль бота
        
        Returns:
            (success, session_id or error)
        """
        client = GameSocketClient(self.host, self.port, self.timeout)
        success, result = client.authenticate(login, password)
        
        if success:
            self.clients[shop_code] = client
            self.last_ping[shop_code] = datetime.utcnow()
            return True, result
        else:
            return False, result
    
    def get_client(self, shop_code: str) -> Optional[GameSocketClient]:
        """Получить клиент для магазина"""
        return self.clients.get(shop_code)
    
    def ping_all(self) -> dict[str, bool]:
        """
        Отправить пинги всем ботам
        
        Returns:
            {shop_code: alive}
        """
        results = {}
        for shop_code, client in self.clients.items():
            alive = client.ping()
            results[shop_code] = alive
            
            if alive:
                self.last_ping[shop_code] = datetime.utcnow()
            else:
                print(f"⚠ Session expired for {shop_code}")
        
        return results
    
    def disconnect_all(self):
        """Отключить всех ботов"""
        for shop_code, client in self.clients.items():
            client.disconnect()
        
        self.clients.clear()
        self.last_ping.clear()
    
    def get_status(self) -> dict[str, dict]:
        """Получить статус всех ботов"""
        status = {}
        for shop_code, client in self.clients.items():
            last_ping = self.last_ping.get(shop_code)
            status[shop_code] = {
                "authenticated": client.authenticated,
                "session_id": client.session_id[:8] + "..." if client.session_id else None,
                "last_ping": last_ping.isoformat() if last_ping else None,
            }
        return status


