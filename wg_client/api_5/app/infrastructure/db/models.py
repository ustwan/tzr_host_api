"""SQLAlchemy модели для API 5"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Numeric, Boolean, 
    TIMESTAMP, Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ShopModel(Base):
    """Магазин (город)"""
    __tablename__ = "shops"
    
    id = Column(Integer, primary_key=True)
    code = Column(Text, unique=True, nullable=False)  # moscow, oasis, neva
    name = Column(Text, nullable=False)  # Moscow, Oasis, Neva
    bot_login = Column(Text)  # Sova
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    # Relationships
    items = relationship("ShopItemModel", back_populates="shop")
    snapshots = relationship("SnapshotModel", back_populates="shop")


class ItemTemplateModel(Base):
    """Шаблон товара"""
    __tablename__ = "item_templates"
    
    id = Column(Integer, primary_key=True)
    type = Column(Text, nullable=False)  # 1.13, 2.32, etc
    name = Column(Text, nullable=False)  # b2-k6, b2-p1, etc
    category = Column(Text, nullable=False)  # k, p, v, h, etc
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('type', 'name', 'category', name='uq_template'),
        Index('idx_item_templates_category', 'category'),
        Index('idx_item_templates_name', 'name'),
    )
    
    # Relationships
    items = relationship("ShopItemModel", back_populates="template")


class ShopItemModel(Base):
    """Экземпляр товара в магазине"""
    __tablename__ = "shop_items"
    
    id = Column(BigInteger, primary_key=True)  # ID из игры
    template_id = Column(Integer, ForeignKey("item_templates.id"))
    shop_id = Column(Integer, ForeignKey("shops.id"))
    
    # Базовые поля
    txt = Column(Text)
    price = Column(Numeric(12, 2))
    current_quality = Column(Integer)
    max_quality = Column(Integer)
    weight = Column(Integer)  # massa
    
    # Урон и защита (JSONB)
    damage = Column(JSONB)  # [{type: "S", min: 2, max: 6}, ...]
    protection = Column(JSONB)  # [{type: "S", min: 7, max: 16}, ...]
    
    # Оружие
    caliber = Column(Text)
    range = Column(Integer)
    grouping = Column(Integer)
    piercing = Column(Numeric(5, 2))  # В процентах
    max_count = Column(Integer)  # Ёмкость магазина
    reload_od = Column(Integer)  # rOD
    attack_modes = Column(JSONB)  # [{type: 2, od: 3}, ...]
    skill = Column(Integer)  # nskill
    
    # Экипировка
    slots = Column(Text)  # st
    equip_od = Column(Integer)  # OD
    requirements = Column(JSONB)  # {level: 6, strength: 14, ...}
    bonuses = Column(JSONB)  # {int: 4, str: 2}
    build_in = Column(ARRAY(Text))  # Встройки
    
    # Мета
    infinty = Column(Boolean, default=False)
    owner = Column(Text)
    section = Column(Integer)
    added_at = Column(TIMESTAMP)  # put_day
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    # Сырые атрибуты
    raw_attributes = Column(JSONB)
    
    __table_args__ = (
        Index('idx_shop_items_template', 'template_id'),
        Index('idx_shop_items_shop', 'shop_id'),
        Index('idx_shop_items_price', 'price'),
        Index('idx_shop_items_added_at', 'added_at'),
        Index('idx_shop_items_owner', 'owner'),
    )
    
    # Relationships
    template = relationship("ItemTemplateModel", back_populates="items")
    shop = relationship("ShopModel", back_populates="items")
    snapshot_links = relationship("SnapshotItemModel", back_populates="item")
    changes = relationship("ItemChangeModel", back_populates="item")


class SnapshotModel(Base):
    """Снимок магазина"""
    __tablename__ = "snapshots"
    
    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    items_count = Column(Integer, default=0)
    worker_name = Column(Text)  # moscow_worker, oasis_worker, neva_worker
    
    __table_args__ = (
        Index('idx_snapshots_shop', 'shop_id', 'created_at'),
    )
    
    # Relationships
    shop = relationship("ShopModel", back_populates="snapshots")
    item_links = relationship("SnapshotItemModel", back_populates="snapshot")
    changes = relationship("ItemChangeModel", back_populates="snapshot")


class SnapshotItemModel(Base):
    """Привязка товара к снимку"""
    __tablename__ = "snapshot_items"
    
    snapshot_id = Column(Integer, ForeignKey("snapshots.id", ondelete="CASCADE"), primary_key=True)
    item_id = Column(BigInteger, ForeignKey("shop_items.id"), primary_key=True)
    
    __table_args__ = (
        Index('idx_snapshot_items_snapshot', 'snapshot_id'),
        Index('idx_snapshot_items_item', 'item_id'),
    )
    
    # Relationships
    snapshot = relationship("SnapshotModel", back_populates="item_links")
    item = relationship("ShopItemModel", back_populates="snapshot_links")


class ItemChangeModel(Base):
    """Изменение товара"""
    __tablename__ = "item_changes"
    
    id = Column(Integer, primary_key=True)
    item_id = Column(BigInteger, ForeignKey("shop_items.id"), nullable=False)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    change_type = Column(Text, nullable=False)  # added, removed, price_changed, etc
    old_price = Column(Numeric(12, 2))
    new_price = Column(Numeric(12, 2))
    old_quality = Column(Integer)
    new_quality = Column(Integer)
    detected_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_item_changes_item', 'item_id', 'detected_at'),
        Index('idx_item_changes_snapshot', 'snapshot_id'),
        Index('idx_item_changes_type', 'change_type'),
    )
    
    # Relationships
    item = relationship("ShopItemModel", back_populates="changes")
    snapshot = relationship("SnapshotModel", back_populates="changes")


class BotSessionModel(Base):
    """Сессия бота"""
    __tablename__ = "bot_sessions"
    
    id = Column(Integer, primary_key=True)
    bot_login = Column(Text, nullable=False)
    shop_code = Column(Text, nullable=False)  # moscow, oasis, neva
    session_id = Column(Text)
    authenticated = Column(Boolean, default=False)
    last_activity = Column(TIMESTAMP)
    location = Column(Text)  # Текущая локация
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('bot_login', 'shop_code', name='uq_bot_session'),
        Index('idx_bot_sessions_shop', 'shop_code'),
        Index('idx_bot_sessions_auth', 'authenticated', 'last_activity'),
    )


