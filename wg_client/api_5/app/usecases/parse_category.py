"""Use Case: Парсинг категории магазина с пагинацией и раскрытием групп"""
from typing import List, Set, Tuple
import time

from app.domain.entities import ShopItem, ShopParseResult
from app.infrastructure.game_socket_client import GameSocketClient
from app.parsers.shop_parser import ShopParser
from app.infrastructure.db.repositories import (
    ShopRepository, ItemTemplateRepository, ShopItemRepository
)
from app.config import config


class ParseCategoryUseCase:
    """
    Парсинг одной категории магазина
    
    Включает:
    - Пагинацию (перебор страниц до повтора)
    - Раскрытие групп (count="N")
    - Сохранение в БД
    """
    
    def __init__(
        self,
        shop_repo: ShopRepository,
        template_repo: ItemTemplateRepository,
        item_repo: ShopItemRepository,
        client: GameSocketClient,
    ):
        self.shop_repo = shop_repo
        self.template_repo = template_repo
        self.item_repo = item_repo
        self.client = client
    
    def execute(self, shop_code: str, category: str) -> Tuple[int, int]:
        """
        Парсинг категории
        
        Args:
            shop_code: Код магазина (moscow/oasis/neva)
            category: Код категории (k, p, v, ...)
        
        Returns:
            (items_count, groups_expanded_count)
        """
        # Получить магазин
        shop = self.shop_repo.get_by_code(shop_code)
        if not shop:
            raise ValueError(f"Shop {shop_code} not found")
        
        print(f"🔄 Парсинг категории '{category}' в магазине {shop.name}...")
        
        # Парсинг с пагинацией
        all_items = []
        groups_to_expand = []
        
        page = 0
        seen_ids: Set[int] = set()
        
        while True:
            print(f"  📄 Страница {page}...")
            
            # Запрос страницы
            xml_response = self._fetch_page_with_retry(category, page, "", shop_code)
            if not xml_response:
                print(f"    ❌ Не удалось получить страницу {page}")
                break
            
            # Парсинг
            result = ShopParser.parse_response(xml_response, shop_code)
            if not result:
                print(f"    ❌ Ошибка парсинга страницы {page}")
                break
            
            # Проверка на группы (важно сделать ДО проверки items!)
            if result.has_groups:
                groups_to_expand.extend(self._extract_groups(xml_response))
                print(f"    📦 Обнаружено групп: {len(self._extract_groups(xml_response))}")
            
            # Если нет товаров
            if not result.items:
                if page == 0 and result.has_groups:
                    # Первая страница без товаров, но с группами - нормально
                    print(f"    ⚠ Страница {page} без товаров, но есть {len(self._extract_groups(xml_response))} групп")
                    page += 1
                    time.sleep(config.PAGE_RETRY_DELAY)
                    continue
                else:
                    # Пустая страница без групп или не первая
                    print(f"    ⚠ Пустая страница {page}")
                    break
            
            # Проверка на повтор (это последняя страница?)
            current_ids = {item.id for item in result.items}
            
            if current_ids.issubset(seen_ids):
                # Все товары уже видели → повтор → останавливаемся
                print(f"    ✓ Повтор обнаружен на странице {page} (последняя: {page-1})")
                break
            
            # Новые товары
            new_items = [item for item in result.items if item.id not in seen_ids]
            all_items.extend(new_items)
            seen_ids.update(current_ids)
            
            print(f"    ✓ Найдено {len(new_items)} новых товаров (всего {len(all_items)}) [⏱ {page*2:.0f}s]")
            
            page += 1
            time.sleep(config.PAGE_RETRY_DELAY)  # Пауза между страницами
        
        # Раскрытие групп
        groups_expanded = 0
        if groups_to_expand:
            print(f"  📦 Раскрытие {len(groups_to_expand)} групп...")
            group_items = self._expand_groups(shop_code, category, groups_to_expand)
            all_items.extend(group_items)
            groups_expanded = len(groups_to_expand)
        
        # Сохранение в БД
        print(f"  💾 Сохранение {len(all_items)} товаров в БД...")
        for item in all_items:
            # Определить шаблон (по name, type, category из raw_attributes)
            raw = item.raw_attributes
            if "name" in raw and "type" in raw:
                template = self.template_repo.get_or_create(
                    type=raw["type"],
                    name=raw["name"],
                    category=category
                )
                item.template_id = template.id
            
            item.shop_id = shop.id
            self.item_repo.upsert(item)
        
        print(f"✓ Категория '{category}': {len(all_items)} товаров, {groups_expanded} групп")
        return len(all_items), groups_expanded
    
    def _fetch_page_with_retry(self, category: str, page: int, filter_str: str = "", shop_code: str = "moscow") -> str:
        """Запрос страницы с retry и auto-reconnect"""
        # Получить bot credentials для auto-reconnect
        bots_config = config.get_bots_config()
        bot_config = bots_config.get(shop_code)
        login = bot_config.login if bot_config else None
        login_key = bot_config.login_key if bot_config else None
        
        for attempt in range(config.PAGE_RETRY_ATTEMPTS):
            xml = self.client.fetch_shop_category(category, page, filter_str, login, login_key)
            if xml:
                return xml
            
            if attempt < config.PAGE_RETRY_ATTEMPTS - 1:
                print(f"    ⚠ Retry {attempt+1}/{config.PAGE_RETRY_ATTEMPTS}...")
                time.sleep(config.PAGE_RETRY_DELAY)
        
        return None
    
    def _extract_groups(self, xml_str: str) -> List[dict]:
        """Извлечь группы из XML (исключая товары-стаки с id)"""
        import xml.etree.ElementTree as ET
        
        groups = []
        try:
            root = ET.fromstring(xml_str)
            for item_el in root.findall("O"):
                # Группа = count есть, но id нет
                # Товар-стак (патроны, энергомодули) = count есть И id есть (парсится как обычный товар)
                if "count" in item_el.attrib and "id" not in item_el.attrib:
                    # Это группа для раскрытия
                    groups.append({
                        "name": item_el.get("name"),
                        "type": item_el.get("type"),
                        "count": int(item_el.get("count", 0)),
                    })
        except:
            pass
        
        return groups
    
    def _expand_groups(self, shop_code: str, category: str, groups: List[dict]) -> List[ShopItem]:
        """Раскрыть группы товаров"""
        all_group_items = []
        
        for group in groups:
            filter_str = f"name:{group['name']},type:{group['type']}"
            print(f"    🔓 Группа: {group['name']} (count={group['count']})")
            
            # Парсинг группы с пагинацией (по умолчанию 8 товаров на странице)
            page = 0
            seen_ids: Set[int] = set()
            
            while True:
                # Запрос с фильтром группы
                xml = self._fetch_page_with_retry(category, page, filter_str, shop_code)
                if not xml:
                    break
                
                result = ShopParser.parse_response(xml, shop_code)
                if not result or not result.items:
                    break
                
                # Проверка на повтор
                current_ids = {item.id for item in result.items}
                if current_ids.issubset(seen_ids):
                    break
                
                new_items = [item for item in result.items if item.id not in seen_ids]
                all_group_items.extend(new_items)
                seen_ids.update(current_ids)
                
                page += 1
                time.sleep(config.PAGE_RETRY_DELAY)
            
            print(f"      ✓ Получено {len(seen_ids)} товаров из группы")
        
        return all_group_items


