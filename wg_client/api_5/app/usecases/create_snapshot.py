"""Use Case: Создание снимка магазина"""
from typing import List
from datetime import datetime

from app.domain.entities import Snapshot
from app.infrastructure.db.repositories import ShopRepository, SnapshotRepository, ShopItemRepository
from app.usecases.parse_category import ParseCategoryUseCase
from app.config import config


class CreateSnapshotUseCase:
    """
    Создание полного снимка магазина
    
    Включает:
    - Парсинг всех категорий
    - Создание snapshot записи
    - Привязку товаров к снимку
    """
    
    def __init__(
        self,
        shop_repo: ShopRepository,
        snapshot_repo: SnapshotRepository,
        item_repo: ShopItemRepository,
        parse_category_uc: ParseCategoryUseCase,
    ):
        self.shop_repo = shop_repo
        self.snapshot_repo = snapshot_repo
        self.item_repo = item_repo
        self.parse_category_uc = parse_category_uc
    
    def execute(self, shop_code: str, worker_name: str = None) -> Snapshot:
        """
        Создать снимок магазина
        
        Args:
            shop_code: Код магазина (moscow/oasis/neva)
            worker_name: Имя воркера (опционально)
        
        Returns:
            Snapshot
        """
        # Получить магазин
        shop = self.shop_repo.get_by_code(shop_code)
        if not shop:
            raise ValueError(f"Shop {shop_code} not found")
        
        print(f"📸 Создание снимка магазина {shop.name}...")
        
        # Парсинг всех категорий
        total_items = 0
        total_groups = 0
        item_ids: List[int] = []
        
        for category in config.SHOP_CATEGORIES:
            try:
                items_count, groups_count = self.parse_category_uc.execute(shop_code, category)
                total_items += items_count
                total_groups += groups_count
            except Exception as e:
                print(f"  ❌ Ошибка при парсинге категории {category}: {e}")
        
        # Получить все ID товаров этого магазина (текущее состояние)
        all_shop_items = self.item_repo.get_list(shop_id=shop.id, limit=100000)
        item_ids = [item.id for item in all_shop_items]
        
        # Создать снимок
        snapshot = Snapshot(
            shop_id=shop.id,
            items_count=len(item_ids),
            worker_name=worker_name or f"{shop_code}_worker",
        )
        snapshot = self.snapshot_repo.create(snapshot)
        
        # Привязать товары
        self.snapshot_repo.link_items(snapshot.id, item_ids)
        
        print(f"✓ Снимок создан: ID={snapshot.id}, товаров={len(item_ids)}, групп={total_groups}")
        return snapshot


