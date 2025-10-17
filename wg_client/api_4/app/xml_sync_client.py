"""
XML Sync Client - альтернативный способ получения логов боев
Адаптировано из send_qt.py для работы в API 4
"""
import socket
import time
import re
import os
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class XmlSyncClient:
    """Клиент для получения логов боев через XML протокол игрового сервера"""
    
    def __init__(self, login_name: str = None, key: str = None):
        # Production server configuration
        self.host = "185.92.72.18"
        self.port = 5190
        
        # Аккаунт для авторизации (можно передать в конструктор)
        self.login_name = login_name or "КОТ БЕГЕМОТ"  # Fallback на старый аккаунт
        self.key = key or "21C097883FB3C9A3352912DD00D1B2095FF3C09E"  # Fallback на старый ключ
        
        self.login_template = '<LOGIN v3="10.20.30.40" lang="ru" v2="4875537" v="108" p="{key}" l="{login_name}" />\x00'
        
        # Настройки таймаутов
        self.connect_timeout = 5
        self.receive_timeout = 30
        self.max_response_time = 45  # Если дольше 45 сек - скорее всего лога нет
        self.max_empty_chunks = 3
        
    def _connect_and_authenticate(self) -> socket.socket:
        """Подключение к серверу и авторизация"""
        logger.info(f"Подключение к {self.host}:{self.port}")
        
        sock = socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
        
        # Отправляем авторизацию
        login_xml = self.login_template.format(key=self.key, login_name=self.login_name)
        sock.sendall(login_xml.encode('utf-8'))
        
        # Получаем ответ авторизации
        login_resp = sock.recv(8192)
        login_response = login_resp.decode(errors='ignore')
        
        logger.info(f"Ответ авторизации: {login_response[:200]}")
        
        if b'<ERROR' in login_resp:
            sock.close()
            raise Exception(f"Ошибка авторизации: {login_response}")
        
        logger.info("Авторизация успешна")
        return sock
    
    def _send_command(self, sock: socket.socket, xml_command: str) -> bytes:
        """Отправка XML команды и получение ответа"""
        xml_data_full = xml_command.strip() + "\x00"
        
        logger.info(f"Отправляем команду: {xml_command}")
        time.sleep(0.3)  # Небольшая пауза после авторизации
        sock.sendall(xml_data_full.encode('utf-8'))
        
        response = b''
        sock.settimeout(self.receive_timeout)
        start = time.time()
        
        total_chunks = 0
        
        logger.info("Ожидаем ответ от сервера...")
        
        try:
            # Читаем данные пока не получим </BLOOK> или другой закрывающий тег
            while True:
                chunk = sock.recv(8192)
                total_chunks += 1
                
                if chunk:
                    response += chunk
                    logger.debug(f"Получен chunk #{total_chunks}, размер: {len(chunk)} байт")
                    
                    # Для логов боев ждём именно </BLOOK>
                    if b'</BLOOK>' in response:
                        logger.info("Получен полный лог боя (найден </BLOOK>)")
                        # Читаем ещё немного на случай если есть хвост
                        sock.settimeout(2)
                        try:
                            tail = sock.recv(8192)
                            if tail:
                                response += tail
                                logger.debug(f"Получен хвост после </BLOOK>: {len(tail)} байт")
                        except socket.timeout:
                            pass
                        break
                    
                    # Для других команд проверяем стандартные теги
                    if b'</POST>' in response or b'</ERROR>' in response or b'</OK>' in response:
                        logger.info("Получен ответ (найден закрывающий тег)")
                        sock.settimeout(2)
                        try:
                            tail = sock.recv(8192)
                            if tail:
                                response += tail
                        except socket.timeout:
                            pass
                        break
                else:
                    # Пустой chunk - данные закончились
                    logger.debug("Пустой chunk, данные закончились")
                    break
                
                # Проверяем общий таймаут
                if time.time() - start > self.max_response_time:
                    logger.warning(f"Таймаут ответа ({self.max_response_time}s) - скорее всего лога нет")
                    # Помечаем как response_timeout
                    raise TimeoutError(f"Server response timeout after {self.max_response_time}s")
        
        except socket.timeout:
            logger.warning("Таймаут получения данных")
            raise TimeoutError("Socket timeout during data reception")
        except TimeoutError:
            raise  # Пробрасываем дальше
        except Exception as e:
            logger.error(f"Ошибка получения данных: {e}")
        
        logger.info(f"Получен ответ размером: {len(response)} байт, chunks: {total_chunks}")
        return response
    
    def _deduplicate_battles(self, xml_content: str) -> str:
        """
        Дедубликация тегов <BATTLE> и удаление обёртки <BLOOK>
        
        Из: <BLOOK><BATTLE>...</BATTLE><BATTLE>...</BATTLE></BLOOK>
        В:  <BATTLE>...</BATTLE>
        """
        # Убираем открывающий и закрывающий теги BLOOK
        xml_content = xml_content.replace('<BLOOK>', '').replace('</BLOOK>', '')
        # На всякий случай убираем варианты с атрибутами
        xml_content = re.sub(r'<BLOOK[^>]*>', '', xml_content)
        
        # Ищем первое вхождение <BATTLE>
        first_battle_start = xml_content.find('<BATTLE')
        if first_battle_start == -1:
            logger.warning("Не найдено ни одного тега <BATTLE> в ответе")
            return xml_content
        
        # Ищем второе вхождение <BATTLE> (признак дубликата)
        second_battle_start = xml_content.find('<BATTLE', first_battle_start + 1)
        
        if second_battle_start != -1:
            logger.info(f"Найден дубликат <BATTLE> на позиции {second_battle_start}, обрезаем")
            # Удаляем всё начиная со второго <BATTLE>
            xml_content = xml_content[:second_battle_start]
        
        # Убираем лишние пробелы и переносы в начале/конце
        xml_content = xml_content.strip()
        
        # Проверяем что есть закрывающий тег </BATTLE>
        if '</BATTLE>' not in xml_content:
            logger.warning("Отсутствует закрывающий тег </BATTLE>, возможно лог неполный")
        
        return xml_content
    
    def request_battle_log(self, battle_id: int) -> Optional[str]:
        """
        Запрос лога боя по его ID
        
        Args:
            battle_id: ID боя для запроса
            
        Returns:
            XML содержимое боя или None при ошибке
        """
        xml_command = f'<POST t="//blook {battle_id}" />'
        
        sock = None
        try:
            # Подключаемся и авторизуемся
            sock = self._connect_and_authenticate()
            
            # Отправляем команду и получаем ответ
            response = self._send_command(sock, xml_command)
            
            # Декодируем ответ
            xml_content = response.decode(errors='ignore')
            
            # Проверяем на ошибки
            if '<ERROR' in xml_content:
                logger.error(f"Сервер вернул ошибку для battle_id={battle_id}: {xml_content[:500]}")
                return None
            
            # Проверяем что есть данные
            if '<BATTLE' not in xml_content:
                logger.warning(f"Нет данных о бое {battle_id}")
                return None
            
            # Дедубликация и очистка
            battle_xml = self._deduplicate_battles(xml_content)
            
            logger.info(f"Успешно получен лог боя {battle_id}, размер: {len(battle_xml)} байт")
            return battle_xml
            
        except TimeoutError as e:
            logger.warning(f"Таймаут при запросе боя {battle_id}: {e}")
            raise  # Пробрасываем для обработки в request_and_save
        except Exception as e:
            logger.error(f"Ошибка при запросе боя {battle_id}: {e}", exc_info=True)
            return None
        
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
    
    def save_battle_to_tmp(self, battle_id: int, xml_content: str) -> str:
        """
        DEPRECATED: Используйте get_battle_xml вместо сохранения в /tmp/
        
        Сохранение лога боя во временный файл (только для обратной совместимости)
        """
        filename = f"/tmp/{battle_id}.tzb"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        logger.info(f"Лог боя {battle_id} сохранён в {filename}")
        return filename
    
    def get_battle_xml(self, battle_id: int) -> Optional[str]:
        """
        Получить XML содержимое боя (без сохранения в файл)
        
        Args:
            battle_id: ID боя
            
        Returns:
            XML содержимое или None при ошибке
        """
        return self.request_battle_log(battle_id)
    
    def request_and_save(self, battle_id: int) -> Optional[Dict[str, Any]]:
        """
        Запросить лог боя и сохранить во временный файл
        
        Args:
            battle_id: ID боя
            
        Returns:
            Словарь с информацией о результате или None при ошибке
        """
        try:
            # Запрашиваем лог
            xml_content = self.request_battle_log(battle_id)
            
            if not xml_content:
                return {
                    "battle_id": battle_id,
                    "status": "failed",
                    "error": "Не удалось получить лог боя",
                    "file_path": None
                }
            
            # Сохраняем во временный файл
            file_path = self.save_battle_to_tmp(battle_id, xml_content)
            
            return {
                "battle_id": battle_id,
                "status": "success",
                "error": None,
                "file_path": file_path,
                "size_bytes": len(xml_content),
                "requested_at": datetime.now().isoformat()
            }
        
        except TimeoutError as e:
            logger.warning(f"Таймаут для боя {battle_id}: {e}")
            return {
                "battle_id": battle_id,
                "status": "response_timeout",
                "error": f"Server response timeout: {str(e)}",
                "file_path": None
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обработке боя {battle_id}: {e}", exc_info=True)
            return {
                "battle_id": battle_id,
                "status": "failed",
                "error": str(e),
                "file_path": None
            }
    
    def request_range(self, start_id: int, end_id: int, skip_existing: bool = True) -> Dict[str, Any]:
        """
        Запросить диапазон боев
        
        Args:
            start_id: Начальный ID боя
            end_id: Конечный ID боя
            skip_existing: Пропускать существующие файлы
            
        Returns:
            Статистика выполнения
        """
        total = end_id - start_id + 1
        success = 0
        failed = 0
        skipped = 0
        results = []
        
        logger.info(f"Запрос диапазона боев: {start_id} - {end_id} ({total} боев)")
        
        for battle_id in range(start_id, end_id + 1):
            # Проверяем существование файла
            if skip_existing and os.path.exists(f"/tmp/{battle_id}.tzb"):
                logger.debug(f"Бой {battle_id} уже существует, пропускаем")
                skipped += 1
                continue
            
            result = self.request_and_save(battle_id)
            
            if result and result["status"] == "success":
                success += 1
            else:
                failed += 1
            
            results.append(result)
            
            # Небольшая пауза между запросами
            if battle_id < end_id:
                time.sleep(0.5)
        
        summary = {
            "total": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "start_id": start_id,
            "end_id": end_id,
            "results": results
        }
        
        logger.info(f"Завершено: успешно={success}, ошибок={failed}, пропущено={skipped}")
        return summary

