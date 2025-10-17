from datetime import datetime, timezone

from wg_client.api_4.app.external_parser import normalize_for_db


def test_normalize_for_db_basic_mapping():
    parser_json = {
        "battle": {
            "id": 123,
            "ts": "2025-10-01T00:00:00Z",
            "size_bytes": 100,
            "sha256": "deadbeef",
            "storage_key": "/tmp/123.tzb",
            "compressed": False,
            "turns": 10,
            "battle_type": "B",
            "loc": {"x": 10, "y": 20},
            "start_ts_unix": 1696118400,
            "players_cnt": 1,
            "monsters_cnt": 2,
            "entities_cnt": 3,
            "map_patch": {"i": "m_ABCD", "cs": "blake2s8:ABCD"},
        },
        "participants": [
            {"login": "player1", "side": 1, "damage_total": {"players": {"HP": 10}}}
        ],
        "monsters": [
            {"kind": "rat", "spec": None, "side": 2, "count": 5, "min_level": 1, "max_level": 3}
        ],
        "loot_total": {
            "resources": [{"name": "Gems", "qty": 2}],
            "monster_parts": [{"name": "Rat Fang", "qty": 1}],
            "other": [{"item_name": "Some Item", "qty": 4}],
        },
    }

    out = normalize_for_db(parser_json)

    assert out["id"] == 123
    assert out["ts"] == "2025-10-01T00:00:00Z"
    assert out["loc_x"] == 10 and out["loc_y"] == 20
    assert out["players_cnt"] == 1 and out["monsters_cnt"] == 2
    # start_ts converted to datetime
    assert isinstance(out["start_ts"], datetime) and out["start_ts"].tzinfo == timezone.utc

    # meta.monsters mapped to dict
    assert "rat" in out["meta"]["monsters"]
    # loot mapping
    loot = out["meta"]["loot"]
    assert loot["resources_total"]["Gems"] == 2
    assert loot["monster_parts_total"]["Rat Fang"] == 1
    assert loot["other_items"]["Some Item"] == 4












