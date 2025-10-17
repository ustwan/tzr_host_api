"""Pytest configuration and fixtures"""
import pytest
import sys
from pathlib import Path

# Добавить app в путь для импортов
app_path = Path(__file__).parent.parent
sys.path.insert(0, str(app_path))


@pytest.fixture
def sample_shop_xml():
    """Пример XML магазина"""
    return '''
    <SH c="k" s="" p="0" m="2">
        <O damage="S2-6" id="79469641" massa="30" maxquality="125" 
           name="b2-k6" nskill="0" OD="1" piercing="500" quality="125" 
           section="0" shot="1-2" st="G,H" txt="Butterfly knife" 
           type="1.13" infinty="1" cost="4" put_day="1749579438" />
        <O damage="S3-8" id="79469642" massa="50" maxquality="150" 
           name="b2-k7" nskill="0" OD="1" piercing="600" quality="150" 
           section="0" shot="1-2" st="GH" txt="Combat knife" 
           type="1.14" infinty="1" cost="8" put_day="1749579438" />
    </SH>
    '''


@pytest.fixture
def moscow_shop():
    """Магазин Moscow"""
    from app.domain.entities import Shop
    return Shop(id=1, code="moscow", name="Moscow", bot_login="Sova")


@pytest.fixture
def oasis_shop():
    """Магазин Oasis"""
    from app.domain.entities import Shop
    return Shop(id=2, code="oasis", name="Oasis", bot_login="Sova")


@pytest.fixture
def neva_shop():
    """Магазин Neva"""
    from app.domain.entities import Shop
    return Shop(id=3, code="neva", name="Neva", bot_login="Sova")


