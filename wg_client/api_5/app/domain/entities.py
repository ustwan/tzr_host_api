"""Доменные сущности API 5"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


class ChangeType(str, Enum):
    """Типы изменений товаров"""
    ADDED = "added"
    REMOVED = "removed"
    PRICE_CHANGED = "price_changed"
    QUALITY_CHANGED = "quality_changed"
    OWNER_CHANGED = "owner_changed"


@dataclass
class Shop:
    """Магазин (город)"""
    id: Optional[int] = None
    code: str = ""  # moscow, oasis, neva
    name: str = ""  # Moscow, Oasis, Neva
    bot_login: Optional[str] = None  # Sova


@dataclass
class ItemTemplate:
    """Шаблон товара (тип + имя + категория)"""
    id: Optional[int] = None
    type: str = ""       # 1.13, 2.32, etc
    name: str = ""       # b2-k6, b2-p1, etc
    category: str = ""   # k, p, v, h, etc


@dataclass
class DamageComponent:
    """Компонент урона"""
    damage_type: str  # S, E, B, D, P, N, H, C, Z, V, O
    min_value: int
    max_value: int


@dataclass
class ProtectionComponent:
    """Компонент защиты"""
    protection_type: str  # S, E, B, D, P, N, H, C, Z, V, O
    min_value: int
    max_value: int


@dataclass
class AttackMode:
    """Режим атаки"""
    mode_type: int  # 0-30 (см. справочник в main_shop.md)
    od_cost: int    # Стоимость ОД


@dataclass
class Requirements:
    """Требования для экипировки"""
    level: Optional[int] = None
    strength: Optional[int] = None
    dexterity: Optional[int] = None
    accuracy: Optional[int] = None
    intuition: Optional[int] = None
    intelligence: Optional[int] = None
    endurance: Optional[int] = None
    gender: Optional[str] = None  # 'M', 'F', None


@dataclass
class ShopItem:
    """Экземпляр товара в магазине"""
    id: int  # ID товара из игры
    template_id: Optional[int] = None
    shop_id: Optional[int] = None
    
    # Базовые поля
    txt: str = ""  # Название
    price: Optional[float] = None
    current_quality: Optional[int] = None
    max_quality: Optional[int] = None
    weight: Optional[int] = None  # massa
    
    # Урон и защита
    damage: List[DamageComponent] = field(default_factory=list)
    protection: List[ProtectionComponent] = field(default_factory=list)
    
    # Оружие
    caliber: Optional[str] = None
    range: Optional[int] = None
    grouping: Optional[int] = None  # Кучность
    piercing: Optional[float] = None  # Бронебойность в %
    max_count: Optional[int] = None  # Ёмкость магазина
    reload_od: Optional[int] = None  # rOD
    attack_modes: List[AttackMode] = field(default_factory=list)
    skill: Optional[int] = None  # nskill
    
    # Экипировка
    slots: Optional[str] = None  # st (G,H / GH / F / C / etc)
    equip_od: Optional[int] = None  # OD
    requirements: Optional[Requirements] = None
    bonuses: Optional[Dict[str, int]] = None  # up="int=4"
    build_in: Optional[List[str]] = None  # Встройки
    
    # Мета
    infinty: bool = False
    owner: Optional[str] = None
    section: Optional[int] = None
    added_at: Optional[datetime] = None  # put_day
    updated_at: Optional[datetime] = None
    
    # Сырые данные (для трассировки)
    raw_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Snapshot:
    """Снимок магазина"""
    id: Optional[int] = None
    shop_id: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    items_count: int = 0
    worker_name: Optional[str] = None  # moscow_worker, oasis_worker, neva_worker
    item_ids: List[int] = field(default_factory=list)


@dataclass
class ItemChange:
    """Изменение товара между снимками"""
    id: Optional[int] = None
    item_id: int = 0
    snapshot_id: int = 0
    change_type: ChangeType = ChangeType.ADDED
    old_price: Optional[float] = None
    new_price: Optional[float] = None
    old_quality: Optional[int] = None
    new_quality: Optional[int] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BotSession:
    """Сессия бота в игре"""
    id: Optional[int] = None
    bot_login: str = ""
    shop_code: str = ""  # moscow, oasis, neva
    session_id: Optional[str] = None
    authenticated: bool = False
    last_activity: Optional[datetime] = None
    location: Optional[str] = None  # Текущая локация бота
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_alive(self, timeout: int = 60) -> bool:
        """Проверка активности сессии"""
        if not self.authenticated or not self.last_activity:
            return False
        delta = (datetime.utcnow() - self.last_activity).total_seconds()
        return delta < timeout


@dataclass
class ShopParseResult:
    """Результат парсинга категории магазина"""
    shop_code: str
    category: str
    page: int
    items: List[ShopItem]
    has_groups: bool = False  # Есть ли группы для раскрытия
    is_last_page: bool = False  # Последняя страница (повтор)
    raw_xml: str = ""


