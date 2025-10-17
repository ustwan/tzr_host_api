"""Unit tests для Use Cases"""
import pytest
from unittest.mock import Mock, MagicMock
from app.usecases.parse_category import ParseCategoryUseCase
from app.usecases.create_snapshot import CreateSnapshotUseCase
from app.usecases.calculate_diff import CalculateDiffUseCase
from app.domain.entities import Shop, ShopItem, Snapshot


class TestParseCategoryUseCase:
    """Тесты для ParseCategoryUseCase"""
    
    @pytest.fixture
    def mock_repositories(self):
        """Моки репозиториев"""
        shop_repo = Mock()
        template_repo = Mock()
        item_repo = Mock()
        client = Mock()
        
        return shop_repo, template_repo, item_repo, client
    
    def test_parse_category_success(self, mock_repositories):
        """Тест: успешный парсинг категории"""
        shop_repo, template_repo, item_repo, client = mock_repositories
        
        # Setup mocks
        shop_repo.get_by_code.return_value = Shop(id=1, code="moscow", name="Moscow")
        
        # Имитация ответа от сервера
        xml_page_0 = '''
        <SH c="k" s="" p="0">
            <O id="100" txt="Knife" name="k1" type="1.1" cost="10" />
            <O id="101" txt="Sword" name="k2" type="1.2" cost="20" />
        </SH>
        '''
        
        # Страница 1 - повтор (последняя)
        xml_page_1 = xml_page_0
        
        client.fetch_shop_category.side_effect = [xml_page_0, xml_page_1]
        
        # Execute
        use_case = ParseCategoryUseCase(shop_repo, template_repo, item_repo, client)
        items_count, groups_count = use_case.execute("moscow", "k")
        
        # Verify
        assert items_count == 2
        assert groups_count == 0
        assert client.fetch_shop_category.call_count == 2
    
    def test_parse_category_with_retry(self, mock_repositories):
        """Тест: retry при ошибке запроса"""
        shop_repo, template_repo, item_repo, client = mock_repositories
        
        shop_repo.get_by_code.return_value = Shop(id=1, code="moscow", name="Moscow")
        
        # Первый запрос - ошибка, второй - успех
        xml = '<SH c="k" s="" p="0"><O id="100" txt="Item" /></SH>'
        client.fetch_shop_category.side_effect = [None, xml, xml]  # Ошибка, успех, повтор
        
        use_case = ParseCategoryUseCase(shop_repo, template_repo, item_repo, client)
        items_count, _ = use_case.execute("moscow", "k")
        
        assert items_count == 1
        # Должно быть 2 успешных запроса + 1 retry
        assert client.fetch_shop_category.call_count >= 2
    
    def test_parse_category_shop_not_found(self, mock_repositories):
        """Тест: магазин не найден"""
        shop_repo, template_repo, item_repo, client = mock_repositories
        
        shop_repo.get_by_code.return_value = None
        
        use_case = ParseCategoryUseCase(shop_repo, template_repo, item_repo, client)
        
        with pytest.raises(ValueError, match="Shop .* not found"):
            use_case.execute("invalid_shop", "k")


class TestCreateSnapshotUseCase:
    """Тесты для CreateSnapshotUseCase"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Моки зависимостей"""
        shop_repo = Mock()
        snapshot_repo = Mock()
        item_repo = Mock()
        parse_category_uc = Mock()
        
        return shop_repo, snapshot_repo, item_repo, parse_category_uc
    
    def test_create_snapshot_success(self, mock_dependencies):
        """Тест: успешное создание снимка"""
        shop_repo, snapshot_repo, item_repo, parse_category_uc = mock_dependencies
        
        # Setup
        shop = Shop(id=1, code="moscow", name="Moscow")
        shop_repo.get_by_code.return_value = shop
        
        # Парсинг категорий
        parse_category_uc.execute.return_value = (10, 2)  # 10 товаров, 2 группы
        
        # Товары в магазине
        items = [ShopItem(id=i, shop_id=1) for i in range(100, 110)]
        item_repo.get_list.return_value = items
        
        # Создание снимка
        snapshot = Snapshot(id=1, shop_id=1, items_count=10)
        snapshot_repo.create.return_value = snapshot
        
        # Execute
        use_case = CreateSnapshotUseCase(
            shop_repo, snapshot_repo, item_repo, parse_category_uc
        )
        result = use_case.execute("moscow", "moscow_worker")
        
        # Verify
        assert result.id == 1
        assert result.shop_id == 1
        snapshot_repo.create.assert_called_once()
        snapshot_repo.link_items.assert_called_once()
    
    def test_create_snapshot_partial_failure(self, mock_dependencies):
        """Тест: частичная ошибка при парсинге категорий"""
        shop_repo, snapshot_repo, item_repo, parse_category_uc = mock_dependencies
        
        shop = Shop(id=1, code="moscow", name="Moscow")
        shop_repo.get_by_code.return_value = shop
        
        # Некоторые категории падают с ошибкой
        def parse_side_effect(shop_code, category):
            if category in ["k", "p"]:
                return (5, 0)
            raise Exception("Parse error")
        
        parse_category_uc.execute.side_effect = parse_side_effect
        
        item_repo.get_list.return_value = []
        snapshot_repo.create.return_value = Snapshot(id=1, shop_id=1, items_count=0)
        
        # Execute (не должно упасть)
        use_case = CreateSnapshotUseCase(
            shop_repo, snapshot_repo, item_repo, parse_category_uc
        )
        result = use_case.execute("moscow")
        
        # Verify
        assert result.id == 1


class TestCalculateDiffUseCase:
    """Тесты для CalculateDiffUseCase"""
    
    @pytest.fixture
    def mock_repos(self):
        """Моки репозиториев"""
        snapshot_repo = Mock()
        item_repo = Mock()
        session = Mock()
        
        return snapshot_repo, item_repo, session
    
    def test_calculate_diff_added_items(self, mock_repos):
        """Тест: добавленные товары"""
        snapshot_repo, item_repo, session = mock_repos
        
        # Предыдущий снимок: товары 100, 101
        snapshot_repo.get_item_ids.side_effect = [
            [100, 101],  # prev
            [100, 101, 102, 103]  # curr
        ]
        
        # Новые товары
        item_repo.get_by_id.side_effect = [
            ShopItem(id=102, price=10.0, current_quality=50),
            ShopItem(id=103, price=20.0, current_quality=100),
        ]
        
        # Execute
        use_case = CalculateDiffUseCase(snapshot_repo, item_repo, session)
        changes = use_case.execute(prev_snapshot_id=1, curr_snapshot_id=2)
        
        # Verify
        added = [c for c in changes if c.change_type.value == "added"]
        assert len(added) == 2
        assert added[0].item_id == 102
        assert added[1].item_id == 103
    
    def test_calculate_diff_removed_items(self, mock_repos):
        """Тест: удалённые товары"""
        snapshot_repo, item_repo, session = mock_repos
        
        # Товары удалены из curr
        snapshot_repo.get_item_ids.side_effect = [
            [100, 101, 102],  # prev
            [100]  # curr (101, 102 удалены)
        ]
        
        item_repo.get_by_id.side_effect = [
            ShopItem(id=101, price=10.0),
            ShopItem(id=102, price=20.0),
        ]
        
        # Execute
        use_case = CalculateDiffUseCase(snapshot_repo, item_repo, session)
        changes = use_case.execute(prev_snapshot_id=1, curr_snapshot_id=2)
        
        # Verify
        removed = [c for c in changes if c.change_type.value == "removed"]
        assert len(removed) == 2
    
    def test_calculate_diff_no_changes(self, mock_repos):
        """Тест: нет изменений"""
        snapshot_repo, item_repo, session = mock_repos
        
        # Одинаковые товары
        snapshot_repo.get_item_ids.side_effect = [
            [100, 101],
            [100, 101]
        ]
        
        # Execute
        use_case = CalculateDiffUseCase(snapshot_repo, item_repo, session)
        changes = use_case.execute(prev_snapshot_id=1, curr_snapshot_id=2)
        
        # Verify
        added = [c for c in changes if c.change_type.value == "added"]
        removed = [c for c in changes if c.change_type.value == "removed"]
        assert len(added) == 0
        assert len(removed) == 0


