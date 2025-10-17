"""
XML парсер для .tzb файлов
Извлекает метаданные из файлов логов боёв
"""

try:
    from lxml import etree as ET  # более устойчивый парсер
except Exception:  # fallback
    import xml.etree.ElementTree as ET
import gzip
import hashlib
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from app.models import BattleMeta, BattleInfo, Participant, Monster, Loot
import json as _json

# Попытка подключить example/parser/battle_parser
_EXAMPLE_BP = None
try:
    import sys as _sys
    _sys.path.append('/app/example/parser')
    import battle_parser as _example_bp
    _EXAMPLE_BP = _example_bp
except Exception:
    try:
        _sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'example' / 'parser'))
        import battle_parser as _example_bp
        _EXAMPLE_BP = _example_bp
    except Exception:
        _EXAMPLE_BP = None

# Опционально подключаем дедупликатор из example/parser
try:
    from example.parser.dedupe_tzb import dedupe_tzb_content
except Exception:
    try:
        from wg_client.example.parser.dedupe_tzb import dedupe_tzb_content
    except Exception:
        dedupe_tzb_content = None


class BattleParser:
    """Парсер XML файлов логов боёв"""
    
    def __init__(self):
        self.parser_version = "1.1.0"

    # ====== Утилиты поиска с учётом/без учёта регистра (при наличии lxml) ======
    def _findall_case(self, root: ET.Element, tag_lower: str):
        """Найти элементы по тегу, поддерживая верхний регистр (если логи в формате <TAG .../>)."""
        try:
            # Если это lxml, можно воспользоваться XPath с translate для case-insensitive
            if hasattr(root, 'xpath'):
                tag_upper = tag_lower.upper()
                return root.xpath(f"//*[translate(local-name(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='{tag_upper}']")
        except Exception:
            pass
        # Стандартный путь: ищем как есть в нижнем регистре
        return root.findall(f".//{tag_lower}")

    def _find_case(self, root: ET.Element, tag_lower: str):
        """Найти первый элемент по тегу с поддержкой верхнего регистра."""
        try:
            if hasattr(root, 'xpath'):
                tag_upper = tag_lower.upper()
                res = root.xpath(f"//*[translate(local-name(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='{tag_upper}'][1]")
                return res[0] if res else None
        except Exception:
            pass
        return root.find(f".//{tag_lower}")

    def _get_battle_elem(self, root: ET.Element) -> Optional[ET.Element]:
        """Надёжно получить элемент BATTLE (без учёта регистра)."""
        be = self._find_case(root, "battle")
        if be is not None:
            return be
        # Fallback: полный обход
        try:
            for el in root.iter():
                try:
                    if getattr(el, 'tag', '').upper() == 'BATTLE':
                        return el
                except Exception:
                    continue
        except Exception:
            pass
        return None
    
    def parse_battle_file(self, file_path: str) -> Dict[str, Any]:
        """Парсинг файла боя"""
        # Если доступен example/parser — используем как первичный источник
        if _EXAMPLE_BP is not None:
            try:
                bp = _EXAMPLE_BP.BattleParser()
                res = bp.parse_file(str(file_path))
                # Маппинг в текущую схему
                b = res.get('battle') or {}
                parts = res.get('participants') or []
                mons = res.get('monsters') or []
                loot_total = res.get('loot_total') or {}

                # Время
                ts_val = b.get('ts')
                ts_dt = None
                if isinstance(ts_val, str) and ts_val:
                    tss = ts_val.replace('Z', '+00:00')
                    try:
                        ts_dt = datetime.fromisoformat(tss)
                    except Exception:
                        ts_dt = datetime.now()

                start_ts_unix = b.get('start_ts_unix')
                start_ts_dt = datetime.fromtimestamp(start_ts_unix) if isinstance(start_ts_unix, int) else None

                loc = b.get('loc') or {}
                loc_x = loc.get('x') if isinstance(loc, dict) else None
                loc_y = loc.get('y') if isinstance(loc, dict) else None

                # Участники → Participant list
                norm_parts: List[Participant] = []
                for p in parts:
                    try:
                        norm_parts.append(Participant(
                            login=p.get('login',''),
                            clan=p.get('clan'),
                            profession=int(p.get('profession')) if p.get('profession') is not None else None,
                            side=int(p.get('side') or 0),
                            rank_points=float(p.get('rank_points') or 0.0),
                            pve_points=int(p.get('pve_points') or 0),
                            level=int(p.get('level') or 0),
                            gender=int(p.get('gender') or 0),
                            survived=bool(p.get('survived') or False),
                            kills_monsters=int(((p.get('kills') or {}).get('monsters') or 0)),
                            kills_players=int(((p.get('kills') or {}).get('players') or 0)),
                        ))
                    except Exception:
                        continue

                # Монстры → Dict[name->Monster]
                norm_mons: Dict[str, Monster] = {}
                for m in mons:
                    try:
                        kind = m.get('kind') or 'unknown'
                        spec = m.get('spec')
                        name = f"{kind}|{spec}" if spec else kind
                        norm_mons[name] = Monster(
                            count=int(m.get('count') or 0),
                            min_level=int(m.get('min_level') or 0),
                            max_level=int(m.get('max_level') or 0),
                            side=int(m.get('side') or 0),
                            spec=spec,
                        )
                    except Exception:
                        continue

                # Loot персональный мы положим в participants в дальнейшем на этапе сохранения
                # Loot total оставим в data

                meta = BattleMeta(
                    battle_info=BattleInfo(
                        turns=int(b.get('turns') or 0),
                        participants_count=int(b.get('players_cnt') or 0),
                        battle_type=str(b.get('battle_type') or 'B'),
                        location=[int(loc_x or 0), int(loc_y or 0)],
                        start_timestamp=int(start_ts_unix or 0) if start_ts_unix else int(ts_dt.timestamp()) if ts_dt else int(datetime.now().timestamp()),
                    ),
                    participants=norm_parts,
                    monsters=norm_mons,
                    loot=self._extract_loot(ET.Element('root'))  # заполним пустым, персональный лут уже в parts
                )

                battle_id_from_parser = int(b.get('id') or 0)
                if battle_id_from_parser == 0:
                    # Пытаемся извлечь из имени файла
                    battle_id_from_parser = self._get_battle_id_from_filename(Path(file_path))
                
                return {
                    "id": battle_id_from_parser,
                    "ts": ts_dt or datetime.now(),
                    "players": [p.login for p in norm_parts],
                    "map": None,
                    "map_height": 0,
                    "map_width": 0,
                    "turns": int(b.get('turns') or 0),
                    "battle_type": str(b.get('battle_type') or 'B'),
                    "loc_x": int(loc_x or 0) if loc_x is not None else None,
                    "loc_y": int(loc_y or 0) if loc_y is not None else None,
                    "start_ts": start_ts_dt,
                    "players_cnt": int(b.get('players_cnt') or (len(norm_parts))),
                    "monsters_cnt": int(b.get('monsters_cnt') or sum(m.count for m in norm_mons.values())),
                    "entities_cnt": int(b.get('entities_cnt') or (len(norm_parts) + sum(m.count for m in norm_mons.values()))),
                    "meta": meta.dict(),
                    "data": {
                        "battle": b,
                        "loot_total": loot_total,
                        "participants": parts,
                        "monsters": mons,
                    },
                    "size_bytes": int(b.get('size_bytes') or 0),
                    "sha256": b.get('sha256') or '',
                    "storage_key": b.get('storage_key') or str(file_path),
                    "compressed": bool(b.get('compressed') or False),
                    "parser_version": self.parser_version,
                    "source": "example_parser",
                    "source_id": self._get_battle_id(ET.Element('root'), Path(file_path)),
                }
            except Exception:
                pass
        file_path = Path(file_path)
        
        # Проверяем существование файла
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        # Получаем метаданные файла
        file_stats = file_path.stat()
        size_bytes = file_stats.st_size
        
        # Вычисляем SHA256
        sha256_hash = self._calculate_sha256(file_path)
        
        # Определяем, сжат ли файл
        compressed = file_path.suffix.lower() in ['.gz', '.gzip']
        
        # Читаем содержимое файла
        try:
            if compressed:
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    content = f.read()
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
        except Exception as e:
            raise ValueError(f"Ошибка чтения файла {file_path}: {e}")
        # Авто-дедупликация по второму <BATTLE> при наличии утилиты
        if dedupe_tzb_content is not None:
            try:
                content = dedupe_tzb_content(content)
            except Exception:
                pass

        # Жёсткое извлечение атрибутов из первой строки <BATTLE ...>
        try:
            first_line = content.split('\n', 1)[0] if content else ''
            if first_line.strip().upper().startswith('<BATTLE'):
                import re as _re
                def _attr(s: str, name: str) -> str:
                    m = _re.search(fr"\b{name}=['\"]([^'\"]+)['\"]", s)
                    return m.group(1) if m else ''
                t2 = _attr(first_line, 't2')
                if t2 and t2.isdigit():
                    ts_hard = datetime.fromtimestamp(int(t2))
                else:
                    ts_hard = None
                turn = _attr(first_line, 'turn')
                turns_hard = int(turn) if turn.isdigit() else None
                fval = _attr(first_line, 'f')
                bt_hard = fval.strip().upper() if fval else None
                note = _attr(first_line, 'note')
                loc_x_hard = loc_y_hard = st_hard = None
                if note and ',' in note:
                    parts = note.split(',')
                    if len(parts) >= 3:
                        try:
                            loc_x_hard = int(parts[0]); loc_y_hard = int(parts[1]); st_hard = int(parts[2])
                        except Exception:
                            pass
            else:
                ts_hard = turns_hard = bt_hard = loc_x_hard = loc_y_hard = st_hard = None
        except Exception:
            ts_hard = turns_hard = bt_hard = loc_x_hard = loc_y_hard = st_hard = None
        
        # Фрагментный парсинг: выделяем блок <BATTLE>... + соседние <TURN> до следующего <BATTLE>/EOF
        root = None
        try:
            # Быстрый путь: попробовать как есть
            if hasattr(ET, 'XMLParser'):
                parser = ET.XMLParser(recover=True)
                root = ET.fromstring(content.encode('utf-8'), parser)
            else:
                root = ET.fromstring(content)
        except Exception:
            # Выделяем первый боевой блок
            lines = content.splitlines()
            start = None
            for i, line in enumerate(lines):
                if '<BATTLE' in line:
                    start = i
                    break
            if start is None:
                raise ValueError(f"Ошибка парсинга XML {file_path}: не найден тег <BATTLE>")
            # Ищем начало следующего боя
            end = len(lines)
            for j in range(start + 1, len(lines)):
                if '<BATTLE' in lines[j]:
                    end = j
                    break
            fragment = "\n".join(lines[start:end])
            wrapped = f"<root>\n{fragment}\n</root>"
            try:
                if hasattr(ET, 'XMLParser'):
                    parser = ET.XMLParser(recover=True)
                    root = ET.fromstring(wrapped.encode('utf-8'), parser)
                else:
                    root = ET.fromstring(wrapped)
            except Exception as e2:
                raise ValueError(f"Ошибка парсинга XML {file_path}: {e2}")
        
        # Извлекаем метаданные
        battle_data = self._extract_battle_metadata(root, file_path)

        # Жёсткий разбор заголовка <BATTLE ...> по example/parser через regex — как fallback
        try:
            import re
            m = re.search(r"<BATTLE[^>]*>", content, re.IGNORECASE)
            if m:
                header = m.group(0)
                def get_attr(name: str) -> str:
                    mm = re.search(fr"\b{name}=['\"]([^'\"]+)['\"]", header)
                    return mm.group(1) if mm else ""
                # ts/t2/turn/f/note приоритетно с верхнего заголовка
                if ts_hard:
                    battle_data["ts"] = ts_hard
                else:
                    t2 = get_attr('t2')
                    if t2.isdigit():
                        try:
                            battle_data["ts"] = datetime.fromtimestamp(int(t2))
                        except Exception:
                            pass
                if turns_hard is not None:
                    battle_data["turns"] = turns_hard
                else:
                    turn = get_attr('turn')
                    if turn.isdigit():
                        battle_data["turns"] = int(turn)
                if bt_hard:
                    battle_data["battle_type"] = bt_hard
                else:
                    fval = get_attr('f')
                    if fval:
                        battle_data["battle_type"] = fval.strip().upper()
                if loc_x_hard is not None and loc_y_hard is not None:
                    battle_data["loc_x"] = loc_x_hard
                    battle_data["loc_y"] = loc_y_hard
                if st_hard is not None:
                    try:
                        battle_data["start_ts"] = datetime.fromtimestamp(st_hard)
                    except Exception:
                        pass
            else:
                # Доп. fallback: первая строка файла, если начинается с <BATTLE ...>
                first = content.splitlines()[0] if content else ''
                if first.strip().upper().startswith('<BATTLE'):
                    header = first
                    def get_attr2(name: str) -> str:
                        mm = re.search(fr"\b{name}=['\"]([^'\"]+)['\"]", header)
                        return mm.group(1) if mm else ""
                    if ts_hard:
                        battle_data["ts"] = ts_hard
                    else:
                        t2 = get_attr2('t2')
                        if t2.isdigit():
                            try:
                                battle_data["ts"] = datetime.fromtimestamp(int(t2))
                            except Exception:
                                pass
                    if turns_hard is not None:
                        battle_data["turns"] = turns_hard
                    else:
                        turn = get_attr2('turn')
                        if turn.isdigit():
                            battle_data["turns"] = int(turn)
                    if bt_hard:
                        battle_data["battle_type"] = bt_hard
                    else:
                        fval = get_attr2('f')
                        if fval:
                            battle_data["battle_type"] = fval.strip().upper()
                    if loc_x_hard is not None and loc_y_hard is not None:
                        battle_data["loc_x"] = loc_x_hard
                        battle_data["loc_y"] = loc_y_hard
                    if st_hard is not None:
                        try:
                            battle_data["start_ts"] = datetime.fromtimestamp(st_hard)
                        except Exception:
                            pass
        except Exception:
            pass
        
        # Добавляем информацию о файле
        battle_data.update({
            "size_bytes": size_bytes,
            "sha256": sha256_hash,
            "storage_key": str(file_path),
            "compressed": compressed,
            "format": "xml",
            "source": "file",
            "parser_version": self.parser_version
        })

        # Проставляем source_id на этапе парсинга из имени файла
        try:
            stem = file_path.stem
            digits = ''.join([c for c in stem if c.isdigit()])
            if digits:
                battle_data["source_id"] = int(digits)
        except Exception:
            pass
        
        return battle_data
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Вычисление SHA256 хеша файла"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _extract_battle_metadata(self, root: ET.Element, file_path: Path) -> Dict[str, Any]:
        """Извлечение метаданных боя из XML"""
        # Базовые данные боя
        battle_id = self._get_battle_id(root, file_path)
        battle_ts = self._get_battle_timestamp(root)
        
        # Информация о бое
        battle_info = self._extract_battle_info(root)
        
        # Участники
        participants = self._extract_participants(root)
        
        # Монстры
        monsters = self._extract_monsters(root)
        
        # Лут
        loot = self._extract_loot(root)
        
        # Создаем метаданные
        meta = BattleMeta(
            battle_info=battle_info,
            participants=participants,
            monsters=monsters,
            loot=loot
        )
        
        # Собираем список игроков
        players = [p.login for p in participants]
        
        # Извлекаем карту
        map_data, map_height, map_width = self._extract_map(root)
        
        return {
            "id": battle_id,
            "ts": battle_ts,
            "players": players,
            "map": map_data,
            "map_height": map_height,
            "map_width": map_width,
            "turns": battle_info.turns,
            "battle_type": battle_info.battle_type,
            "loc_x": battle_info.location[0] if battle_info.location else None,
            "loc_y": battle_info.location[1] if battle_info.location else None,
            "start_ts": datetime.fromtimestamp(battle_info.start_timestamp) if battle_info.start_timestamp else None,
            "players_cnt": len(participants),
            "monsters_cnt": sum(m.count for m in monsters.values()),
            "entities_cnt": len(participants) + sum(m.count for m in monsters.values()),
            "meta": meta.dict(),
            "data": self._extract_full_data(root)
        }
    
    def _get_battle_id(self, root: ET.Element, file_path: Path) -> int:
        """Получение ID боя"""
        # Вариант 1: явный элемент
        battle_id_elem = root.find(".//battle_id")
        if battle_id_elem is not None and battle_id_elem.text:
            try:
                return int(battle_id_elem.text)
            except ValueError:
                pass

        # Вариант 2: атрибут у тега BATTLE (часто встречается в сыром логе)
        battle_elem = self._get_battle_elem(root)
        if battle_elem is not None and hasattr(battle_elem, 'attrib'):
            # Наиболее вероятные имена атрибутов: i, id, battle_id
            for key in ("i", "id", "battle_id", "BATTLE_ID"):
                val = battle_elem.attrib.get(key)
                if val:
                    try:
                        return int(val)
                    except ValueError:
                        continue

        # Вариант 3: из имени файла (цифры в имени)
        return self._get_battle_id_from_filename(file_path)
    
    def _get_battle_id_from_filename(self, file_path: Path) -> int:
        """Извлечение battle_id из имени файла"""
        stem = file_path.stem
        
        # Убираем возможные префиксы (tmp, battle_, и т.д.)
        stem_clean = stem.replace('tmp', '').replace('battle_', '').replace('_', '')
        
        # Извлекаем все цифры
        digits = ''.join([c for c in stem_clean if c.isdigit()])
        
        if digits:
            try:
                # Берём последние 7-8 цифр (разумная длина для battle_id)
                battle_id = int(digits[-8:]) if len(digits) > 8 else int(digits)
                if battle_id > 0:
                    return battle_id
            except ValueError:
                pass
        
        # Фолбэк: стабильный псевдослучайный на основе пути
        return int(hashlib.sha256(str(file_path).encode('utf-8')).hexdigest()[:8], 16)
    
    def _get_battle_timestamp(self, root: ET.Element) -> datetime:
        """Получение времени боя"""
        # Вариант 0: атрибут t2 у тега BATTLE (основной источник по example/parser)
        battle_elem = self._find_case(root, "battle")
        if battle_elem is not None and hasattr(battle_elem, 'attrib'):
            val = battle_elem.attrib.get("t2")
            if val:
                try:
                    return datetime.fromtimestamp(int(val))
                except (ValueError, OSError):
                    pass
        # Вариант 1: явный элемент timestamp
        timestamp_elem = root.find(".//timestamp")
        if timestamp_elem is not None and timestamp_elem.text:
            try:
                return datetime.fromtimestamp(int(timestamp_elem.text))
            except (ValueError, OSError):
                pass

        # Вариант 2: атрибут у BATTLE (напр. ts, t)
        battle_elem = battle_elem or self._get_battle_elem(root)
        if battle_elem is not None and hasattr(battle_elem, 'attrib'):
            for key in ("ts", "t", "start_ts", "TIME"):
                val = battle_elem.attrib.get(key)
                if val:
                    try:
                        return datetime.fromtimestamp(int(val))
                    except (ValueError, OSError):
                        continue

        # Фолбэк
        return datetime.now()
    
    def _extract_battle_info(self, root: ET.Element) -> BattleInfo:
        """Извлечение информации о бое"""
        # Количество ходов
        turns = 0
        # Пробуем из атрибута BATTLE@turn
        battle_elem = self._find_case(root, "battle")
        if battle_elem is not None and hasattr(battle_elem, 'attrib'):
            bt_turn = battle_elem.attrib.get("turn")
            if bt_turn:
                try:
                    turns = int(bt_turn)
                except ValueError:
                    turns = 0
        turns_elem = root.find(".//turns")
        if turns_elem is not None and turns_elem.text:
            try:
                turns = int(turns_elem.text)
            except ValueError:
                pass

        # Подсчёт ходов как количество тегов TURN
        if turns == 0:
            try:
                turns = len([e for e in self._findall_case(root, "turn") if e.tag.upper() == "TURN"]) or 0
            except Exception:
                pass

        # Количество участников
        participants_count = len(root.findall(".//participant"))
        if participants_count == 0:
            # Fallback: считаем USER
            try:
                participants_count = len([e for e in self._findall_case(root, "user") if e.tag.upper() == "USER"]) or 0
            except Exception:
                participants_count = 0

        # Тип боя
        battle_type = "B"  # По умолчанию PvE
        battle_type_elem = root.find(".//battle_type")
        if battle_type_elem is not None and battle_type_elem.text:
            battle_type = battle_type_elem.text
        else:
            # Попробуем взять из атрибута у BATTLE (пример: f для типа, затем type/t)
            battle_elem = battle_elem or self._get_battle_elem(root)
            if battle_elem is not None and hasattr(battle_elem, 'attrib'):
                battle_type = battle_elem.attrib.get("f") or battle_elem.attrib.get("type") or battle_elem.attrib.get("t") or battle_type

        # Нормализуем тип боя к ожидаемым значениям ('A','B','C','D')
        if isinstance(battle_type, str):
            bt = battle_type.strip().upper()
            # Иногда встречаются числовые коды, например '40' — приводим к дефолту
            if bt not in {"A", "B", "C", "D"}:
                battle_type = "B"
            else:
                battle_type = bt
        else:
            battle_type = "B"

        # Координаты
        location = [0, 0]
        loc_x_elem = root.find(".//location/x")
        loc_y_elem = root.find(".//location/y")
        if loc_x_elem is not None and loc_y_elem is not None:
            try:
                location = [int(loc_x_elem.text), int(loc_y_elem.text)]
            except (ValueError, TypeError):
                pass
        else:
            # Попробуем из BATTLE@note="x,y,ts" или атрибутов X/Y у BATTLE
            battle_elem = battle_elem or self._get_battle_elem(root)
            if battle_elem is not None and hasattr(battle_elem, 'attrib'):
                note = battle_elem.attrib.get("note")
                if note and "," in note:
                    parts = note.split(',')
                    if len(parts) >= 2:
                        try:
                            x = int(parts[0])
                            y = int(parts[1])
                            location = [x, y]
                        except ValueError:
                            pass
                if location == [0, 0]:
                    try:
                        x = int(battle_elem.attrib.get("x", "0"))
                        y = int(battle_elem.attrib.get("y", "0"))
                        location = [x, y]
                    except ValueError:
                        pass

        # Время начала
        start_timestamp = int(datetime.now().timestamp())
        start_ts_elem = root.find(".//start_timestamp")
        if start_ts_elem is not None and start_ts_elem.text:
            try:
                start_timestamp = int(start_ts_elem.text)
            except ValueError:
                pass
        else:
            battle_elem = battle_elem or self._find_case(root, "battle")
            if battle_elem is not None and hasattr(battle_elem, 'attrib'):
                # Приоритет: note третий компонент, затем start_ts/t/ts
                note = battle_elem.attrib.get("note")
                if note and "," in note:
                    parts = note.split(',')
                    if len(parts) >= 3:
                        try:
                            start_timestamp = int(parts[2])
                        except ValueError:
                            pass
                for key in ("start_ts", "t", "ts"):
                    val = battle_elem.attrib.get(key)
                    if val:
                        try:
                            start_timestamp = int(val)
                            break
                        except ValueError:
                            continue

        return BattleInfo(
            turns=turns,
            participants_count=participants_count,
            battle_type=battle_type,
            location=location,
            start_timestamp=start_timestamp
        )
    
    def _extract_participants(self, root: ET.Element) -> List[Participant]:
        """Извлечение участников боя"""
        participants: List[Participant] = []

        # 1) Нормализованный формат
        for participant_elem in root.findall(".//participant"):
            try:
                participant = Participant(
                    login=self._get_text(participant_elem, "login", ""),
                    clan=self._get_text(participant_elem, "clan"),
                    profession=self._get_int(participant_elem, "profession", 0),
                    side=self._get_int(participant_elem, "side", 0),
                    rank_points=self._get_float(participant_elem, "rank_points", 0.0),
                    pve_points=self._get_int(participant_elem, "pve_points", 0),
                    level=self._get_int(participant_elem, "level", 1),
                    gender=self._get_int(participant_elem, "gender", 0),
                    survived=self._get_bool(participant_elem, "survived", False),
                    kills_monsters=self._get_int(participant_elem, "kills_monsters", 0),
                    kills_players=self._get_int(participant_elem, "kills_players", 0)
                )
                if participant.login:
                    participants.append(participant)
            except Exception:
                continue

        if participants:
            return participants

        # 2) Fallback: формат USER с атрибутами (например, l=login, g=clan)
        try:
            user_elems = [e for e in self._findall_case(root, "user") if e.tag.upper() == "USER"]
            for ue in user_elems:
                try:
                    login = ue.attrib.get("l") or ue.attrib.get("login") or ""
                    clan = ue.attrib.get("g") or ue.attrib.get("clan")
                    level = int(ue.attrib.get("lv", ue.attrib.get("level", 1))) if ue.attrib.get("lv") or ue.attrib.get("level") else 1
                    participant = Participant(
                        login=login,
                        clan=clan,
                        profession=int(ue.attrib.get("pro")) if ue.attrib.get("pro") is not None else None,
                        side=int(ue.attrib.get("s", 0)) if ue.attrib.get("s") else 0,
                        rank_points=0.0,
                        pve_points=0,
                        level=level,
                        gender=int(ue.attrib.get("sex", 0)) if ue.attrib.get("sex") else 0,
                        survived=False,
                        kills_monsters=0,
                        kills_players=0
                    )
                    if participant.login:
                        participants.append(participant)
                except Exception:
                    continue
        except Exception:
            pass

        return participants
    
    def _extract_monsters(self, root: ET.Element) -> Dict[str, Monster]:
        """Извлечение монстров боя"""
        monsters: Dict[str, Monster] = {}

        # 1) Нормализованный формат
        for monster_elem in root.findall(".//monster"):
            try:
                kind = self._get_text(monster_elem, "kind", "unknown")
                spec = self._get_text(monster_elem, "spec")
                monster_name = f"{kind}|{spec}" if spec else kind
                monster = Monster(
                    count=self._get_int(monster_elem, "count", 1),
                    min_level=self._get_int(monster_elem, "min_level", 1),
                    max_level=self._get_int(monster_elem, "max_level", 1),
                    side=self._get_int(monster_elem, "side", 0),
                    spec=spec
                )
                monsters[monster_name] = monster
            except Exception:
                continue

        if monsters:
            return monsters

        # 2) Fallback: верхний регистр MONSTER с атрибутами
        try:
            mons_elems = [e for e in self._findall_case(root, "monster") if e.tag.upper() == "MONSTER"]
            for me in mons_elems:
                try:
                    kind = me.attrib.get("k") or me.attrib.get("kind") or "unknown"
                    spec = me.attrib.get("s") or me.attrib.get("spec")
                    count = int(me.attrib.get("c", me.attrib.get("count", 1))) if me.attrib.get("c") or me.attrib.get("count") else 1
                    side = int(me.attrib.get("side", 0)) if me.attrib.get("side") else 0
                    min_level = int(me.attrib.get("min_level", 1))
                    max_level = int(me.attrib.get("max_level", 1))
                    monster_name = f"{kind}|{spec}" if spec else kind
                    monsters[monster_name] = Monster(
                        count=count,
                        min_level=min_level,
                        max_level=max_level,
                        side=side,
                        spec=spec
                    )
                except Exception:
                    continue
        except Exception:
            pass

        return monsters
    
    def _extract_loot(self, root: ET.Element) -> Loot:
        """Извлечение лута боя"""
        resources_total: Dict[str, int] = {}
        monster_parts_total: Dict[str, int] = {}
        other_items: Dict[str, int] = {}

        # Нормализованный формат
        for resource_elem in root.findall(".//loot/resource"):
            name = self._get_text(resource_elem, "name", "")
            quantity = self._get_int(resource_elem, "quantity", 0)
            if name and quantity > 0:
                resources_total[name] = resources_total.get(name, 0) + quantity

        for part_elem in root.findall(".//loot/monster_part"):
            name = self._get_text(part_elem, "name", "")
            quantity = self._get_int(part_elem, "quantity", 0)
            if name and quantity > 0:
                monster_parts_total[name] = monster_parts_total.get(name, 0) + quantity

        for item_elem in root.findall(".//loot/item"):
            name = self._get_text(item_elem, "name", "")
            quantity = self._get_int(item_elem, "quantity", 0)
            if name and quantity > 0:
                other_items[name] = other_items.get(name, 0) + quantity

        # Fallback: плоские теги RESOURCE/PART/ITEM с атрибутами
        try:
            res_elems = [e for e in self._findall_case(root, "resource") if e.tag.upper() == "RESOURCE"]
            for re in res_elems:
                name = re.attrib.get("n") or re.attrib.get("name") or ""
                qty = int(re.attrib.get("q", re.attrib.get("quantity", 0))) if re.attrib.get("q") or re.attrib.get("quantity") else 0
                if name and qty > 0:
                    resources_total[name] = resources_total.get(name, 0) + qty

            part_elems = [e for e in self._findall_case(root, "monster_part") if e.tag.upper() in ("MONSTER_PART", "PART")]
            for pe in part_elems:
                name = pe.attrib.get("n") or pe.attrib.get("name") or ""
                qty = int(pe.attrib.get("q", pe.attrib.get("quantity", 0))) if pe.attrib.get("q") or pe.attrib.get("quantity") else 0
                if name and qty > 0:
                    monster_parts_total[name] = monster_parts_total.get(name, 0) + qty

            item_elems = [e for e in self._findall_case(root, "item") if e.tag.upper() == "ITEM"]
            for ie in item_elems:
                name = ie.attrib.get("n") or ie.attrib.get("name") or ""
                qty = int(ie.attrib.get("q", ie.attrib.get("quantity", 0))) if ie.attrib.get("q") or ie.attrib.get("quantity") else 0
                if name and qty > 0:
                    other_items[name] = other_items.get(name, 0) + qty
        except Exception:
            pass

        # Дополнительно: извлечь предметы/подборы из событий (<a t="8" ...>) и объектов карты (<O ... bx/by .../>)
        try:
            # Карточные объекты на карте с координатами (валидируем наличие bx/by через наличие атрибутов в data JSON)
            # Здесь в XML: <O id="..." txt="NAME" count="N" bx="X" by="Y" />
            for o in self._findall_case(root, 'o'):
                try:
                    # Только объекты с координатами на карте
                    if not hasattr(o, 'attrib') or ('bx' not in o.attrib or 'by' not in o.attrib):
                        continue
                    name = o.attrib.get('txt') or o.attrib.get('name')
                    cnt = int(o.attrib.get('count', '0')) if o.attrib.get('count') else 0
                    if name and cnt > 0:
                        # Без словаря маппинга кладём в other_items
                        other_items[name] = other_items.get(name, 0) + cnt
                except Exception:
                    continue
            # Подборы t="8" по уникальным id — считаем фактический лут
            seen_ids = set()
            for a in self._findall_case(root, 'a'):
                try:
                    if not hasattr(a, 'attrib'):
                        continue
                    if a.attrib.get('t') != '8':
                        continue
                    iid = a.attrib.get('id')
                    name = a.attrib.get('txt') or a.attrib.get('name')
                    cnt = int(a.attrib.get('count', '0')) if a.attrib.get('count') else 0
                    if not name or cnt <= 0:
                        continue
                    if iid and iid in seen_ids:
                        continue
                    if iid:
                        seen_ids.add(iid)
                    # Без классификации — кладём в other_items как факт подбора
                    other_items[name] = other_items.get(name, 0) + cnt
                except Exception:
                    continue
        except Exception:
            pass

        return Loot(
            resources_total=resources_total,
            monster_parts_total=monster_parts_total,
            other_items=other_items
        )
    
    def _extract_map(self, root: ET.Element) -> Tuple[Optional[str], int, int]:
        """Извлечение карты боя"""
        map_elem = root.find(".//map")
        if map_elem is None:
            return None, 0, 0
        
        # Получаем размеры карты
        height = self._get_int(map_elem, "height", 0)
        width = self._get_int(map_elem, "width", 0)
        
        # Получаем данные карты
        map_data = self._get_text(map_elem, "data")
        if not map_data:
            # Пытаемся получить из дочерних элементов
            map_rows = []
            for row_elem in map_elem.findall(".//row"):
                row_data = self._get_text(row_elem, "data", "")
                if row_data:
                    map_rows.append(row_data)
            map_data = "\n".join(map_rows) if map_rows else None
        
        return map_data, height, width
    
    def _extract_full_data(self, root: ET.Element) -> Dict[str, Any]:
        """Извлечение полных данных боя для хранения в JSONB"""
        # Конвертируем XML в словарь
        def xml_to_dict(element):
            result = {}
            
            # Добавляем атрибуты
            if element.attrib:
                result.update(element.attrib)
            
            # Добавляем текст, если есть
            if element.text and element.text.strip():
                if len(element) == 0:  # Листовой элемент
                    return element.text.strip()
                else:
                    result['_text'] = element.text.strip()
            
            # Обрабатываем дочерние элементы
            for child in element:
                child_data = xml_to_dict(child)
                if child.tag in result:
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = child_data
            
            return result
        
        return xml_to_dict(root)
    
    def _get_text(self, element: ET.Element, tag: str, default: Optional[str] = None) -> Optional[str]:
        """Получение текста из элемента"""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return default
    
    def _get_int(self, element: ET.Element, tag: str, default: int = 0) -> int:
        """Получение целого числа из элемента"""
        text = self._get_text(element, tag)
        if text:
            try:
                return int(text)
            except ValueError:
                pass
        return default
    
    def _get_float(self, element: ET.Element, tag: str, default: float = 0.0) -> float:
        """Получение числа с плавающей точкой из элемента"""
        text = self._get_text(element, tag)
        if text:
            try:
                return float(text)
            except ValueError:
                pass
        return default
    
    def _get_bool(self, element: ET.Element, tag: str, default: bool = False) -> bool:
        """Получение булева значения из элемента"""
        text = self._get_text(element, tag)
        if text:
            return text.lower() in ['true', '1', 'yes', 'on']
        return default
