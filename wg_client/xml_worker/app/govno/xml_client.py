"""
XML Client - простой клиент для получения логов через XML протокол
Основан на рабочем примере из register.py
"""
import socket
import time
import logging

logger = logging.getLogger(__name__)


class XmlSyncClient:
    """Простой XML клиент для получения логов боев"""
    
    def __init__(self, login_name: str, key: str):
        self.host = "185.92.72.18"
        self.port = 5190
        self.login_name = login_name
        self.key = key
        
        self.sock = None
        self.is_authenticated = False
    
    def connect(self) -> bool:
        """Подключиться и авторизоваться"""
        try:
            logger.info(f"Подключение к {self.host}:{self.port} (аккаунт: {self.login_name})")
            
            # Создаём сокет
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(30.0)  # Увеличено до 30 секунд (сервер медленный)
            self.sock.connect((self.host, self.port))
            
            # Задержка после подключения (сервер нужно время)
            time.sleep(0.3)
            
            # Авторизация
            login_xml = f'<LOGIN v3="10.20.30.40" lang="ru" v2="4875537" v="108" p="{self.key}" l="{self.login_name}" />\x00'
            self.sock.sendall(login_xml.encode('utf-8'))
            
            # Читаем ответ
            response = self.sock.recv(8192).decode(errors='ignore')
            logger.info(f"Ответ авторизации: {response[:100]}")
            
            if '<ERROR' in response:
                logger.error(f"Ошибка авторизации: {response}")
                self.disconnect()
                return False
            
            self.is_authenticated = True
            logger.info("✅ Авторизация успешна")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            self.disconnect()
            return False
        
    def disconnect(self):
        """Закрыть соединение"""
        if self.sock:
            try:
                self.sock.close()
                logger.info("Соединение закрыто")
            except Exception as e:
                logger.debug(f"Ошибка при закрытии: {e}")
            finally:
                self.sock = None
                self.is_authenticated = False
    
    def get_battle_xml(self, battle_id: int, force_reconnect: bool = False) -> str:
        """
        Получить XML лога боя
        
        Args:
            battle_id: ID боя
            force_reconnect: Переподключиться перед запросом
            
        Returns:
            XML содержимое или пустая строка
        """
        # Переподключаемся если нужно
        if force_reconnect or not self.is_authenticated:
            self.disconnect()
            if not self.connect():
                logger.error(f"Не удалось подключиться для боя {battle_id}")
                return ""
        
        try:
            # Отправляем команду
            command = f'<POST t="//blook {battle_id}" />\x00'
            logger.info(f"Запрос боя {battle_id}")
            
            self.sock.sendall(command.encode('utf-8'))
            
            # Читаем ответ до </BLOOK>
            response = b''
            self.sock.settimeout(15.0)
            
            max_chunks = 1000
            chunk_count = 0
            
            while chunk_count < max_chunks:
                try:
                    chunk = self.sock.recv(16384)
                    chunk_count += 1
                    
                    if not chunk:
                        # Пустой chunk - продолжаем ждать
                        time.sleep(0.01)
                        continue
                    
                    response += chunk
                    
                    # Проверяем end tags
                    if b'</BLOOK>' in response or b'</BATTLE>' in response or b'</ERROR>' in response:
                        logger.info(f"✅ Получен лог боя {battle_id}: {len(response)} байт")
                        return response.decode(errors='ignore')
                    
                except socket.timeout:
                    # Timeout на chunk - продолжаем
                    if len(response) > 0:
                        # Есть данные - ждём ещё
                        continue
                    else:
                        # Нет данных - выходим
                        break
            
            # Не дождались end tag
            if len(response) > 100:
                logger.warning(f"Получены данные ({len(response)} байт) но нет end tag для боя {battle_id}")
                return response.decode(errors='ignore')
            else:
                logger.warning(f"Empty response for battle {battle_id}")
                return ""
                
        except Exception as e:
            logger.error(f"Ошибка получения боя {battle_id}: {e}")
            return ""
