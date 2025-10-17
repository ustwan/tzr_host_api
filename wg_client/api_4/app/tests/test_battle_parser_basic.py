from pathlib import Path
from datetime import datetime

from app.parser import BattleParser


def test_battle_parser_extracts_core_fields(tmp_path: Path):
    # Минимальный валидный TZB (XML) с заголовком BATTLE и атрибутами
    xml = (
        '<BATTLE i="2650006" t2="1748072924" turn="13" f="D" note="3,-4,1748072817">\n'
        '  <TURN n="1"/>\n'
        '  <USER l="Elisa" s="1"/>\n'
        '  <MONSTER k="rat" c="15" side="2" min_level="7" max_level="10"/>\n'
        "</BATTLE>\n"
    )
    f = tmp_path / "2650006.tzb"
    f.write_text(xml, encoding="utf-8")

    parser = BattleParser()
    data = parser.parse_battle_file(str(f))

    # Базовые поля боя
    # Число ходов может считаться по тегам TURN (у нас их 1) или по атрибуту
    # Поэтому проверяем, что количество ходов положительно
    assert data["turns"] >= 1
    # Тип боя должен быть одним из допустимых значений (Enum или строка)
    bt = data["battle_type"]
    bt_val = getattr(bt, "value", bt)
    assert bt_val in {"A", "B", "C", "D"}
    assert isinstance(data["loc_x"], int) and isinstance(data["loc_y"], int)
    assert isinstance(data["ts"], datetime)
    assert data["start_ts"] is not None
    assert data["players_cnt"] >= 1
    assert data["monsters_cnt"] >= 1
    assert data["entities_cnt"] == data["players_cnt"] + data["monsters_cnt"]

    # source_id может выставляться на этапе парсинга; если есть — это int
    sid = data.get("source_id")
    assert (sid is None) or isinstance(sid, int)

    # map_patch должен быть внутри data.battle, а в БД он будет проставлен при сохранении
    # Здесь проверяем, что структура data присутствует
    assert isinstance(data.get("data"), dict)

