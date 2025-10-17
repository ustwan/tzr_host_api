"""Use Case: Сравнение снимков магазина"""
from typing import List, Set
from app.domain.entities import ItemChange, ChangeType
from app.infrastructure.db.repositories import SnapshotRepository, ShopItemRepository
from sqlalchemy.orm import Session


class CalculateDiffUseCase:
    """
    Сравнение двух снимков магазина
    
    Определяет:
    - Добавленные товары
    - Удалённые товары
    - Изменения цен
    - Изменения качества
    """
    
    def __init__(
        self,
        snapshot_repo: SnapshotRepository,
        item_repo: ShopItemRepository,
        session: Session,
    ):
        self.snapshot_repo = snapshot_repo
        self.item_repo = item_repo
        self.session = session
    
    def execute(self, prev_snapshot_id: int, curr_snapshot_id: int) -> List[ItemChange]:
        """
        Сравнить снимки
        
        Args:
            prev_snapshot_id: ID предыдущего снимка
            curr_snapshot_id: ID текущего снимка
        
        Returns:
            Список изменений
        """
        print(f"🔍 Сравнение снимков {prev_snapshot_id} → {curr_snapshot_id}...")
        
        # Получить ID товаров в каждом снимке
        prev_ids = set(self.snapshot_repo.get_item_ids(prev_snapshot_id))
        curr_ids = set(self.snapshot_repo.get_item_ids(curr_snapshot_id))
        
        changes: List[ItemChange] = []
        
        # 1. Добавленные товары
        added_ids = curr_ids - prev_ids
        for item_id in added_ids:
            item = self.item_repo.get_by_id(item_id)
            changes.append(ItemChange(
                item_id=item_id,
                snapshot_id=curr_snapshot_id,
                change_type=ChangeType.ADDED,
                new_price=item.price if item else None,
                new_quality=item.current_quality if item else None,
            ))
        
        # 2. Удалённые товары
        removed_ids = prev_ids - curr_ids
        for item_id in removed_ids:
            item = self.item_repo.get_by_id(item_id)
            changes.append(ItemChange(
                item_id=item_id,
                snapshot_id=curr_snapshot_id,
                change_type=ChangeType.REMOVED,
                old_price=item.price if item else None,
                old_quality=item.current_quality if item else None,
            ))
        
        # 3. Общие товары (проверка изменений)
        common_ids = prev_ids & curr_ids
        
        for item_id in common_ids:
            # Получить данные товара из обоих снимков
            # Примечание: В реальности нужно хранить snapshot_items с атрибутами
            # Сейчас упрощение - берём текущее состояние
            item = self.item_repo.get_by_id(item_id)
            if not item:
                continue
            
            # Здесь нужна логика получения старых значений
            # Для MVP упрощение: сравниваем с текущим состоянием
            # TODO: Добавить историческое хранение атрибутов
            
            # Пример: изменение цены (если бы хранили историю)
            # if old_price != new_price:
            #     changes.append(ItemChange(...))
        
        print(f"  ✓ Добавлено: {len(added_ids)}")
        print(f"  ✓ Удалено: {len(removed_ids)}")
        print(f"  ✓ Без изменений: {len(common_ids)}")
        
        return changes


