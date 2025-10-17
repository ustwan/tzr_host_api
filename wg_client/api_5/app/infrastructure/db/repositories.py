"""Репозитории для работы с БД"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from app.infrastructure.db.models import (
    ShopModel, ItemTemplateModel, ShopItemModel,
    SnapshotModel, SnapshotItemModel, ItemChangeModel,
    BotSessionModel
)
from app.domain.entities import Shop, ItemTemplate, ShopItem, Snapshot, BotSession


class ShopRepository:
    """Репозиторий для магазинов"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_code(self, code: str) -> Optional[Shop]:
        """Получить магазин по коду"""
        model = self.session.query(ShopModel).filter_by(code=code).first()
        if model:
            return Shop(id=model.id, code=model.code, name=model.name, bot_login=model.bot_login)
        return None
    
    def get_all(self) -> List[Shop]:
        """Получить все магазины"""
        models = self.session.query(ShopModel).all()
        return [Shop(id=m.id, code=m.code, name=m.name, bot_login=m.bot_login) for m in models]


class ItemTemplateRepository:
    """Репозиторий для шаблонов товаров"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_or_create(self, type: str, name: str, category: str) -> ItemTemplate:
        """Получить или создать шаблон"""
        model = self.session.query(ItemTemplateModel).filter_by(
            type=type, name=name, category=category
        ).first()
        
        if model:
            return ItemTemplate(id=model.id, type=model.type, name=model.name, category=model.category)
        
        # Создать новый
        model = ItemTemplateModel(type=type, name=name, category=category)
        self.session.add(model)
        self.session.flush()
        
        return ItemTemplate(id=model.id, type=model.type, name=model.name, category=model.category)


class ShopItemRepository:
    """Репозиторий для товаров"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def upsert(self, item: ShopItem) -> ShopItem:
        """Вставить или обновить товар"""
        model = self.session.query(ShopItemModel).filter_by(id=item.id).first()
        
        # Подготовка данных
        data = {
            "template_id": item.template_id,
            "shop_id": item.shop_id,
            "txt": item.txt,
            "price": item.price,
            "current_quality": item.current_quality,
            "max_quality": item.max_quality,
            "weight": item.weight,
            "damage": [{"type": d.damage_type, "min": d.min_value, "max": d.max_value} for d in item.damage],
            "protection": [{"type": p.protection_type, "min": p.min_value, "max": p.max_value} for p in item.protection],
            "caliber": item.caliber,
            "range": item.range,
            "grouping": item.grouping,
            "piercing": item.piercing,
            "max_count": item.max_count,
            "reload_od": item.reload_od,
            "attack_modes": [{"type": a.mode_type, "od": a.od_cost} for a in item.attack_modes],
            "skill": item.skill,
            "slots": item.slots,
            "equip_od": item.equip_od,
            "requirements": item.requirements.__dict__ if item.requirements else None,
            "bonuses": item.bonuses,
            "build_in": item.build_in,
            "infinty": item.infinty,
            "owner": item.owner,
            "section": item.section,
            "added_at": item.added_at,
            "raw_attributes": item.raw_attributes,
        }
        
        if model:
            # Обновить
            for key, value in data.items():
                setattr(model, key, value)
        else:
            # Создать
            model = ShopItemModel(id=item.id, **data)
            self.session.add(model)
        
        self.session.flush()
        item.updated_at = model.updated_at
        return item
    
    def get_by_id(self, item_id: int) -> Optional[ShopItem]:
        """Получить товар по ID"""
        model = self.session.query(ShopItemModel).filter_by(id=item_id).first()
        if model:
            return self._model_to_entity(model)
        return None
    
    def get_list(self, shop_id: Optional[int] = None, limit: int = 100, offset: int = 0) -> List[ShopItem]:
        """Получить список товаров"""
        query = self.session.query(ShopItemModel)
        if shop_id:
            query = query.filter_by(shop_id=shop_id)
        
        models = query.order_by(ShopItemModel.updated_at.desc()).limit(limit).offset(offset).all()
        return [self._model_to_entity(m) for m in models]
    
    def _model_to_entity(self, model: ShopItemModel) -> ShopItem:
        """Конвертация модели в сущность"""
        from app.domain.entities import DamageComponent, ProtectionComponent, AttackMode, Requirements
        
        item = ShopItem(
            id=model.id,
            template_id=model.template_id,
            shop_id=model.shop_id,
            txt=model.txt,
            price=float(model.price) if model.price else None,
            current_quality=model.current_quality,
            max_quality=model.max_quality,
            weight=model.weight,
            caliber=model.caliber,
            range=model.range,
            grouping=model.grouping,
            piercing=float(model.piercing) if model.piercing else None,
            max_count=model.max_count,
            reload_od=model.reload_od,
            skill=model.skill,
            slots=model.slots,
            equip_od=model.equip_od,
            bonuses=model.bonuses,
            build_in=model.build_in,
            infinty=model.infinty,
            owner=model.owner,
            section=model.section,
            added_at=model.added_at,
            updated_at=model.updated_at,
            raw_attributes=model.raw_attributes,
        )
        
        # Damage (преобразуем min/max -> min_value/max_value, type -> damage_type)
        if model.damage:
            item.damage = [
                DamageComponent(
                    damage_type=d.get('damage_type', d.get('type', '')),
                    min_value=d.get('min_value', d.get('min', 0)),
                    max_value=d.get('max_value', d.get('max', 0))
                )
                for d in model.damage
            ]
        
        # Protection (преобразуем min/max -> min_value/max_value)
        if model.protection:
            item.protection = [
                ProtectionComponent(
                    protection_type=p.get('protection_type', p.get('type')),
                    min_value=p.get('min_value', p.get('min', 0)),
                    max_value=p.get('max_value', p.get('max', 0))
                )
                for p in model.protection
            ]
        
        # Attack modes (преобразуем mode/od -> mode_type/od_cost)
        if model.attack_modes:
            item.attack_modes = [
                AttackMode(
                    mode_type=a.get('mode_type', a.get('mode', 0)),
                    od_cost=a.get('od_cost', a.get('od', 0))
                )
                for a in model.attack_modes
            ]
        
        # Requirements
        if model.requirements:
            item.requirements = Requirements(**model.requirements)
        
        return item


class SnapshotRepository:
    """Репозиторий для снимков"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, snapshot: Snapshot) -> Snapshot:
        """Создать снимок"""
        model = SnapshotModel(
            shop_id=snapshot.shop_id,
            items_count=snapshot.items_count,
            worker_name=snapshot.worker_name,
        )
        self.session.add(model)
        self.session.flush()
        
        snapshot.id = model.id
        snapshot.created_at = model.created_at
        return snapshot
    
    def link_items(self, snapshot_id: int, item_ids: List[int]):
        """Привязать товары к снимку"""
        for item_id in item_ids:
            link = SnapshotItemModel(snapshot_id=snapshot_id, item_id=item_id)
            self.session.add(link)
        self.session.flush()
    
    def get_latest(self, shop_id: int) -> Optional[Snapshot]:
        """Получить последний снимок магазина"""
        model = self.session.query(SnapshotModel).filter_by(
            shop_id=shop_id
        ).order_by(SnapshotModel.created_at.desc()).first()
        
        if model:
            return Snapshot(
                id=model.id,
                shop_id=model.shop_id,
                created_at=model.created_at,
                items_count=model.items_count,
                worker_name=model.worker_name,
            )
        return None
    
    def get_item_ids(self, snapshot_id: int) -> List[int]:
        """Получить ID товаров в снимке"""
        links = self.session.query(SnapshotItemModel).filter_by(snapshot_id=snapshot_id).all()
        return [link.item_id for link in links]


class BotSessionRepository:
    """Репозиторий для сессий ботов"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def upsert(self, bot_session: BotSession) -> BotSession:
        """Вставить или обновить сессию"""
        model = self.session.query(BotSessionModel).filter_by(
            bot_login=bot_session.bot_login,
            shop_code=bot_session.shop_code
        ).first()
        
        if model:
            model.session_id = bot_session.session_id
            model.authenticated = bot_session.authenticated
            model.last_activity = bot_session.last_activity
            model.location = bot_session.location
        else:
            model = BotSessionModel(
                bot_login=bot_session.bot_login,
                shop_code=bot_session.shop_code,
                session_id=bot_session.session_id,
                authenticated=bot_session.authenticated,
                last_activity=bot_session.last_activity,
                location=bot_session.location,
            )
            self.session.add(model)
        
        self.session.flush()
        bot_session.id = model.id
        return bot_session
    
    def get_by_shop(self, shop_code: str) -> Optional[BotSession]:
        """Получить сессию по магазину"""
        model = self.session.query(BotSessionModel).filter_by(shop_code=shop_code).first()
        if model:
            return BotSession(
                id=model.id,
                bot_login=model.bot_login,
                shop_code=model.shop_code,
                session_id=model.session_id,
                authenticated=model.authenticated,
                last_activity=model.last_activity,
                location=model.location,
                created_at=model.created_at,
            )
        return None


