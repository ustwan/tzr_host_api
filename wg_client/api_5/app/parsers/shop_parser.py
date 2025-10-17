"""Парсер XML ответов магазина"""
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
import re
from datetime import datetime

from app.domain.entities import (
    ShopItem,
    DamageComponent,
    ProtectionComponent,
    AttackMode,
    Requirements,
    ShopParseResult,
)


class ShopParser:
    """
    Парсер XML ответов магазина
    
    Обрабатывает:
    - Страницы категорий (<SH>)
    - Элементы товаров (<O />)
    - Нормализацию полей
    """
    
    @staticmethod
    def parse_response(xml_str: str, shop_code: str) -> Optional[ShopParseResult]:
        """
        Парсинг XML ответа магазина
        
        Args:
            xml_str: XML строка
            shop_code: Код магазина (moscow/oasis/neva)
        
        Returns:
            ShopParseResult или None при ошибке
        """
        try:
            root = ET.fromstring(xml_str)
            
            if root.tag != "SH":
                print(f"❌ Unexpected root tag: {root.tag}")
                return None
            
            # Метаданные страницы
            category = root.get("c", "")
            page = int(root.get("p", "0"))
            count = int(root.get("m", "0"))
            
            # Парсинг товаров
            items = []
            has_groups = False
            
            for item_el in root.findall("O"):
                # Проверка на группу vs товар-стак (патроны, энергомодули)
                # Если count есть НО id нет → это группа для раскрытия
                # Если count есть И id есть → это товар-стак (парсим как обычный товар)
                if "count" in item_el.attrib and "id" not in item_el.attrib:
                    has_groups = True
                    continue  # Группы парсим отдельно
                
                item = ShopParser.parse_item(item_el)
                if item:
                    items.append(item)
            
            result = ShopParseResult(
                shop_code=shop_code,
                category=category,
                page=page,
                items=items,
                has_groups=has_groups,
                is_last_page=False,  # Проверяется снаружи
                raw_xml=xml_str,
            )
            
            return result
            
        except ET.ParseError as e:
            print(f"❌ XML parse error: {e}")
            return None
        except Exception as e:
            print(f"❌ Parse error: {e}")
            return None
    
    @staticmethod
    def parse_item(item_el: ET.Element) -> Optional[ShopItem]:
        """Парсинг одного элемента <O />"""
        try:
            attrs = dict(item_el.attrib)
            
            # ID обязателен
            if "id" not in attrs:
                return None
            
            item_id = int(attrs["id"])
            
            # Создаём базовый item
            item = ShopItem(
                id=item_id,
                txt=attrs.get("txt", ""),
                raw_attributes=attrs,
            )
            
            # Цена
            if "cost" in attrs:
                item.price = float(attrs["cost"])
            
            # Качество
            if "quality" in attrs:
                item.current_quality = int(attrs["quality"])
            if "maxquality" in attrs:
                item.max_quality = int(attrs["maxquality"])
            
            # Вес
            if "massa" in attrs:
                item.weight = float(attrs["massa"])
            
            # Урон
            if "damage" in attrs:
                item.damage = ShopParser.parse_damage(attrs["damage"])
            
            # Защита
            if "protect" in attrs:
                item.protection = ShopParser.parse_protection(attrs["protect"])
            
            # Оружие
            if "calibre" in attrs:
                item.caliber = attrs["calibre"]
            if "range" in attrs:
                item.range = int(attrs["range"])
            if "grouping" in attrs:
                item.grouping = int(attrs["grouping"])
            if "piercing" in attrs:
                item.piercing = int(attrs["piercing"]) / 100.0  # 500 -> 5.0%
            if "max_count" in attrs:
                item.max_count = int(attrs["max_count"])
            elif "count" in attrs and "id" in attrs:
                # Товар-стак (патроны, энергомодули) - count это количество единиц
                item.max_count = int(attrs["count"])
            if "rOD" in attrs:
                item.reload_od = int(attrs["rOD"])
            if "nskill" in attrs:
                item.skill = int(attrs["nskill"])
            
            # Режимы атаки
            if "shot" in attrs:
                item.attack_modes = ShopParser.parse_attack_modes(attrs["shot"])
            
            # Слоты
            if "st" in attrs:
                item.slots = attrs["st"]
            if "OD" in attrs:
                item.equip_od = int(attrs["OD"])
            
            # Требования
            if "min" in attrs:
                item.requirements = ShopParser.parse_requirements(attrs["min"])
            
            # Бонусы
            if "up" in attrs:
                item.bonuses = ShopParser.parse_bonuses(attrs["up"])
            
            # Встройки
            if "build_in" in attrs:
                item.build_in = attrs["build_in"].split(",")
            
            # Мета
            if "infinty" in attrs:
                item.infinty = attrs["infinty"] == "1"
            
            # Owner (для infinity товаров ставим 'admin')
            if "owner" in attrs:
                item.owner = attrs["owner"]
            elif "infinty" in attrs and attrs["infinty"] == "1":
                item.owner = "admin"  # Бесконечные товары = админские
            
            if "section" in attrs:
                item.section = int(attrs["section"])
            if "put_day" in attrs:
                item.added_at = datetime.utcfromtimestamp(int(attrs["put_day"]))
            
            return item
            
        except Exception as e:
            print(f"❌ Error parsing item: {e}")
            return None
    
    @staticmethod
    def parse_damage(damage_str: str) -> List[DamageComponent]:
        """
        Парсинг урона: damage="S2-6,E3-7,B4-8"
        
        Returns:
            [DamageComponent(type="S", min=2, max=6), ...]
        """
        components = []
        for part in damage_str.split(","):
            match = re.match(r"([A-Z])(\d+)-(\d+)", part.strip())
            if match:
                dmg_type, min_val, max_val = match.groups()
                components.append(
                    DamageComponent(
                        damage_type=dmg_type,
                        min_value=int(min_val),
                        max_value=int(max_val),
                    )
                )
        return components
    
    @staticmethod
    def parse_protection(protect_str: str) -> List[ProtectionComponent]:
        """
        Парсинг защиты: protect="S7-16,O1-5,B2-5"
        
        Returns:
            [ProtectionComponent(type="S", min=7, max=16), ...]
        """
        components = []
        for part in protect_str.split(","):
            match = re.match(r"([A-Z])(\d+)-(\d+)", part.strip())
            if match:
                prot_type, min_val, max_val = match.groups()
                components.append(
                    ProtectionComponent(
                        protection_type=prot_type,
                        min_value=int(min_val),
                        max_value=int(max_val),
                    )
                )
        return components
    
    @staticmethod
    def parse_attack_modes(shot_str: str) -> List[AttackMode]:
        """
        Парсинг режимов атаки: shot="2-3,3-5,4-7"
        
        Returns:
            [AttackMode(type=2, od=3), AttackMode(type=3, od=5), ...]
        """
        modes = []
        for part in shot_str.split(","):
            match = re.match(r"(\d+)-(\d+)", part.strip())
            if match:
                mode_type, od_cost = match.groups()
                modes.append(
                    AttackMode(
                        mode_type=int(mode_type),
                        od_cost=int(od_cost),
                    )
                )
        return modes
    
    @staticmethod
    def parse_requirements(min_str: str) -> Requirements:
        """
        Парсинг требований: min="level=6,str=14,intel=2,acc=4,man!1"
        
        Returns:
            Requirements(level=6, strength=14, ...)
        """
        req = Requirements()
        
        for part in min_str.split(","):
            part = part.strip()
            
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip()
                
                if key == "level":
                    req.level = int(value)
                elif key == "str":
                    req.strength = int(value)
                elif key == "dex":
                    req.dexterity = int(value)
                elif key == "acc":
                    req.accuracy = int(value)
                elif key == "int":
                    req.intuition = int(value)
                elif key == "intel":
                    req.intelligence = int(value)
                elif key == "pow":
                    req.endurance = int(value)
            
            elif "!" in part:
                # Пол: man!1 (1=муж, 0=жен)
                key, value = part.split("!", 1)
                if key.strip() == "man":
                    req.gender = "M" if value.strip() == "1" else "F"
        
        return req
    
    @staticmethod
    def parse_bonuses(up_str: str) -> Dict[str, int]:
        """
        Парсинг бонусов: up="int=4,str=2"
        
        Returns:
            {"int": 4, "str": 2}
        """
        bonuses = {}
        for part in up_str.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                bonuses[key.strip()] = int(value.strip())
        return bonuses


