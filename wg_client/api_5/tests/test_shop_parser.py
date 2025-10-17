"""Unit tests для ShopParser"""
import pytest
from app.parsers.shop_parser import ShopParser
from app.domain.entities import DamageComponent, ProtectionComponent, AttackMode, Requirements


class TestShopParser:
    """Тесты для парсера магазина"""
    
    def test_parse_simple_item(self):
        """Тест: парсинг простого товара (холодное оружие)"""
        xml = '''
        <SH c="k" s="" p="0" m="1">
            <O damage="S2-6" id="79469641" massa="30" maxquality="125" name="b2-k6" 
               nskill="0" OD="1" piercing="500" quality="125" section="0" 
               shot="1-2" st="G,H" txt="Butterfly knife" type="1.13" 
               infinty="1" cost="4" p2="0" put_day="1749579438" />
        </SH>
        '''
        
        result = ShopParser.parse_response(xml, "moscow")
        
        assert result is not None
        assert result.shop_code == "moscow"
        assert result.category == "k"
        assert result.page == 0
        assert len(result.items) == 1
        
        item = result.items[0]
        assert item.id == 79469641
        assert item.txt == "Butterfly knife"
        assert item.price == 4.0
        assert item.current_quality == 125
        assert item.max_quality == 125
        assert item.weight == 30
        assert item.piercing == 5.0  # 500 -> 5.0%
        assert item.infinty is True
        assert item.slots == "G,H"
    
    def test_parse_damage(self):
        """Тест: парсинг урона"""
        # Одиночный урон
        damage = ShopParser.parse_damage("S2-6")
        assert len(damage) == 1
        assert damage[0].damage_type == "S"
        assert damage[0].min_value == 2
        assert damage[0].max_value == 6
        
        # Множественный урон
        damage = ShopParser.parse_damage("E3-7,B4-8")
        assert len(damage) == 2
        assert damage[0].damage_type == "E"
        assert damage[0].min_value == 3
        assert damage[0].max_value == 7
        assert damage[1].damage_type == "B"
        assert damage[1].min_value == 4
        assert damage[1].max_value == 8
    
    def test_parse_protection(self):
        """Тест: парсинг защиты"""
        protection = ShopParser.parse_protection("S7-16,O1-5,B2-5")
        assert len(protection) == 3
        assert protection[0].protection_type == "S"
        assert protection[0].min_value == 7
        assert protection[0].max_value == 16
        assert protection[1].protection_type == "O"
        assert protection[2].protection_type == "B"
    
    def test_parse_attack_modes(self):
        """Тест: парсинг режимов атаки"""
        modes = ShopParser.parse_attack_modes("2-3,3-5,4-7")
        assert len(modes) == 3
        assert modes[0].mode_type == 2
        assert modes[0].od_cost == 3
        assert modes[1].mode_type == 3
        assert modes[1].od_cost == 5
        assert modes[2].mode_type == 4
        assert modes[2].od_cost == 7
    
    def test_parse_requirements(self):
        """Тест: парсинг требований"""
        req = ShopParser.parse_requirements("level=6,str=14,intel=2,acc=4,man!1")
        assert req.level == 6
        assert req.strength == 14
        assert req.intelligence == 2
        assert req.accuracy == 4
        assert req.gender == "M"
        
        # Женский пол
        req = ShopParser.parse_requirements("man!0")
        assert req.gender == "F"
    
    def test_parse_bonuses(self):
        """Тест: парсинг бонусов"""
        bonuses = ShopParser.parse_bonuses("int=4,str=2")
        assert bonuses["int"] == 4
        assert bonuses["str"] == 2
    
    def test_parse_pistol(self):
        """Тест: парсинг пистолета"""
        xml = '''
        <SH c="p" s="" p="0">
            <O calibre="9" damage="S5-8" grouping="36" id="79470735" massa="170" 
               max_count="15" maxquality="95" min="level=3,str=6,int=5" 
               name="b2-p1" nskill="1" OD="4" piercing="2400" quality="95" 
               range="4" rOD="3" section="0" shot="2-3,3-5" st="G,H" 
               txt="Beretta 92/93" type="2.32" infinty="1" cost="22" />
        </SH>
        '''
        
        result = ShopParser.parse_response(xml, "moscow")
        item = result.items[0]
        
        assert item.caliber == "9"
        assert item.max_count == 15
        assert item.range == 4
        assert item.grouping == 36
        assert item.reload_od == 3
        assert len(item.attack_modes) == 2
        assert item.requirements.level == 3
        assert item.requirements.strength == 6
        assert item.requirements.intuition == 5
    
    def test_parse_armor(self):
        """Тест: парсинг брони"""
        xml = '''
        <SH c="h" s="" p="0">
            <O build_in="300.1" id="79510254" massa="250" maxquality="450" 
               min="level=6,str=14,intel=2,acc=4,man!1" name="ba6-h1" OD="4" 
               protect="S7-16,O1-5,B2-5,D1-3,Z1-2" quality="450" section="0" 
               st="F" txt="Stalker helm" type="0.31" up="int=4" 
               infinty="1" cost="146" />
        </SH>
        '''
        
        result = ShopParser.parse_response(xml, "moscow")
        item = result.items[0]
        
        assert len(item.protection) == 5
        assert item.protection[0].protection_type == "S"
        assert item.bonuses["int"] == 4
        assert item.build_in == ["300.1"]
        assert item.slots == "F"
    
    def test_parse_group(self):
        """Тест: определение группы товаров"""
        xml = '''
        <SH c="q" s="" p="0">
            <O txt="Fearless box" name="ba12-zp1" type="808.21" 
               lvl="0" auc="0" count="6" />
        </SH>
        '''
        
        result = ShopParser.parse_response(xml, "moscow")
        
        # Группы не попадают в items (парсятся отдельно)
        assert len(result.items) == 0
        assert result.has_groups is True
    
    def test_parse_empty_page(self):
        """Тест: пустая страница"""
        xml = '<SH c="k" s="" p="5"></SH>'
        
        result = ShopParser.parse_response(xml, "moscow")
        
        assert result is not None
        assert len(result.items) == 0
    
    def test_parse_invalid_xml(self):
        """Тест: невалидный XML"""
        xml = '<SH c="k" invalid xml'
        
        result = ShopParser.parse_response(xml, "moscow")
        
        assert result is None


class TestShopParserMoscow:
    """Тесты специфичные для магазина Moscow"""
    
    @pytest.fixture
    def moscow_cold_weapons_xml(self):
        """Пример XML холодного оружия из Moscow"""
        return '''
        <SH c="k" s="" p="0" m="3">
            <O damage="S2-6" id="79469641" massa="30" maxquality="125" 
               name="b2-k6" nskill="0" OD="1" piercing="500" quality="125" 
               section="0" shot="1-2" st="G,H" txt="Butterfly knife" 
               type="1.13" infinty="1" cost="4" put_day="1749579438" />
            <O damage="S3-8" id="79469642" massa="50" maxquality="150" 
               name="b2-k7" nskill="0" OD="1" piercing="600" quality="150" 
               section="0" shot="1-2" st="GH" txt="Combat knife" 
               type="1.14" infinty="1" cost="8" put_day="1749579438" />
            <O damage="S4-10" id="79469643" massa="80" maxquality="200" 
               name="b2-k8" nskill="0" OD="2" piercing="800" quality="200" 
               section="0" shot="1-3" st="GH" txt="Katana" 
               type="1.15" infinty="1" cost="15" put_day="1749579438" />
        </SH>
        '''
    
    def test_parse_moscow_cold_weapons(self, moscow_cold_weapons_xml):
        """Тест: парсинг холодного оружия Moscow"""
        result = ShopParser.parse_response(moscow_cold_weapons_xml, "moscow")
        
        assert result.shop_code == "moscow"
        assert result.category == "k"
        assert len(result.items) == 3
        
        # Butterfly knife
        knife = result.items[0]
        assert knife.txt == "Butterfly knife"
        assert knife.slots == "G,H"  # Одноручный
        
        # Combat knife
        combat = result.items[1]
        assert combat.txt == "Combat knife"
        assert combat.slots == "GH"  # Двуручный
        
        # Katana
        katana = result.items[2]
        assert katana.txt == "Katana"
        assert katana.price == 15.0
        assert katana.piercing == 8.0  # 800 -> 8.0%
    
    def test_moscow_price_range(self, moscow_cold_weapons_xml):
        """Тест: проверка диапазона цен Moscow"""
        result = ShopParser.parse_response(moscow_cold_weapons_xml, "moscow")
        
        prices = [item.price for item in result.items]
        assert min(prices) == 4.0
        assert max(prices) == 15.0
        assert sum(prices) == 27.0
    
    def test_moscow_quality_check(self, moscow_cold_weapons_xml):
        """Тест: проверка качества товаров Moscow"""
        result = ShopParser.parse_response(moscow_cold_weapons_xml, "moscow")
        
        for item in result.items:
            assert item.current_quality == item.max_quality  # infinty=1
            assert item.infinty is True


class TestPagination:
    """Тесты для логики пагинации"""
    
    def test_detect_last_page_by_repeat(self):
        """Тест: определение последней страницы по повтору"""
        # Страница 0
        xml_p0 = '''
        <SH c="k" s="" p="0">
            <O id="100" txt="Item 1" />
            <O id="101" txt="Item 2" />
        </SH>
        '''
        
        # Страница 1 (новые товары)
        xml_p1 = '''
        <SH c="k" s="" p="1">
            <O id="102" txt="Item 3" />
            <O id="103" txt="Item 4" />
        </SH>
        '''
        
        # Страница 2 (повтор страницы 1)
        xml_p2 = '''
        <SH c="k" s="" p="2">
            <O id="102" txt="Item 3" />
            <O id="103" txt="Item 4" />
        </SH>
        '''
        
        result_p0 = ShopParser.parse_response(xml_p0, "moscow")
        result_p1 = ShopParser.parse_response(xml_p1, "moscow")
        result_p2 = ShopParser.parse_response(xml_p2, "moscow")
        
        ids_p0 = {item.id for item in result_p0.items}
        ids_p1 = {item.id for item in result_p1.items}
        ids_p2 = {item.id for item in result_p2.items}
        
        # Страница 2 повторяет страницу 1
        assert ids_p2 == ids_p1
        assert ids_p2 != ids_p0


