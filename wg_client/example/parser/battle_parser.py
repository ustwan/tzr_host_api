#!/usr/bin/env python3
import re
import os
import json
import base64
import gzip
import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict, namedtuple


@dataclass
class FileMeta:
    size_bytes: int
    sha256: str
    storage_key: str
    compressed: bool


Kill = namedtuple("Kill", "battle_id turn sf killer victim damage shots")

HP_NUM_RE = re.compile(r"(-?\d+)$")  # забираем последнее число с учетом знака (например, из "0:60" → 60, "0:-52" → -52)
HP_EXTENDED_RE = re.compile(r"^(\d+):(\d+):([A-Z]+\d*)(-?\d+)$")  # расширенный формат "бронебойный:обычный:код_урон"


class BattleParser:
    def __init__(self) -> None:
        self.resource_types = {
            "Gems",
            "Metals",
            "Organic",
            "Polymers",
            "Precious metals",
            "Radioactive materials",
            "Venom",
            "Silicon",
        }
        self.monster_parts = {
            "Rat Brain",
            "Rat Eyes",
            "Rat Fang",
            "Rat Skin",
            "Stich Blood",
            "Stich Bone Marrow",
            "Stich Claw",
            "Stich Meat",
            "Stich Skin",
            "Vzzik Egg Fragments",
            "Vzzik Shell Powder",
            "Vzzik Wings",
            "Cursed Brain",
            "Cursed Paw",
            "Cursed Skin",
            "Water crystal",
            "WitchJelly Acid",
            "WitchJelly Bille",
            "WitchJelly Enzyme",
        }

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        file_meta = self._file_meta(file_path, content)
        battle_info = self._parse_battle_info(content)
        participants = self._parse_participants(content)
        self._update_interventions(content, participants)
        self._augment_kills_by_turn(content, participants)
        self._update_personal_loot(content, participants)
        monsters_agg = self._parse_monsters(content)
        loot = self._parse_loot(content)

        # Map patch (diff against base map rows)
        map_patch = self._build_map_patch(content)

        players_cnt = len(participants)
        monsters_cnt = sum(m["count"] for m in monsters_agg.values())

        result: Dict[str, Any] = {
            "battle": {
                "id": battle_info.get("battle_id", 0),
                "ts": battle_info.get("end_ts_iso", None),
                "size_bytes": file_meta.size_bytes,
                "sha256": file_meta.sha256,
                "storage_key": file_meta.storage_key,
                "compressed": file_meta.compressed,
                "turns": battle_info.get("turns", 0),
                "battle_type": battle_info.get("field_type", None),
                "loc": {"x": battle_info.get("loc_x", 0), "y": battle_info.get("loc_y", 0)},
                "start_ts_unix": battle_info.get("start_ts_unix", None),
                "players_cnt": players_cnt,
                "monsters_cnt": monsters_cnt,
                "entities_cnt": players_cnt + monsters_cnt,
                "data": None,
                "map_patch": map_patch,
            },
            "participants": participants,
            "monsters": self._format_monsters(monsters_agg),
            "loot_total": loot,
        }

        return result

    def _extract_map_rows(self, content: str) -> List[str]:
        """Extract MAP rows (v strings) from the first BATTLE section."""
        # Limit to first BATTLE to avoid duplicates
        end_pos = content.find('</BATTLE>')
        scope = content if end_pos == -1 else content[:end_pos]
        rows = re.findall(r'<MAP\s+v="([^"]+)"\s*/>', scope)
        return rows

    def _build_map_patch(self, content: str) -> Dict[str, Any]:
        """Build minimal map patch object: base id, diff (h+s), checksum.
        For now, we assume final rows equal to base rows (diff empty), which is
        sufficient to carry map identity and integrity.
        """
        base_rows = self._extract_map_rows(content)
        if not base_rows:
            return {}

        # Identify map by short hash of base rows
        data = "\n".join(base_rows).encode('utf-8')
        map_id = hashlib.blake2s(data, digest_size=8).hexdigest().upper()

        # For MVP, final_rows = base_rows → empty diff
        final_rows = list(base_rows)

        # Build diff (h + s) between base_rows and final_rows
        d: Dict[str, List[List[Any]]] = {}
        h_ops: List[List[Any]] = []
        s_ops: List[List[Any]] = []
        if base_rows and final_rows and len(base_rows) == len(final_rows):
            H = len(base_rows)
            W = len(base_rows[0]) if H > 0 else 0
            for y in range(H):
                a = base_rows[y]
                b = final_rows[y]
                if len(a) != len(b):
                    # If widths mismatch, skip diff generation
                    h_ops.clear(); s_ops.clear()
                    break
                x = 0
                while x < W:
                    if a[x] == b[x]:
                        x += 1
                        continue
                    ch = b[x]
                    x0 = x
                    while x < W and b[x] == ch and a[x] != b[x]:
                        x += 1
                    x1 = x - 1
                    # Threshold T=3 for horizontal runs
                    if x1 - x0 + 1 >= 3:
                        h_ops.append([y, x0, x1, ch])
                    else:
                        for xx in range(x0, x1 + 1):
                            s_ops.append([y, xx, ch])
            if h_ops:
                d["h"] = h_ops
            if s_ops:
                d["s"] = s_ops

        # Checksum of final map
        content = '\n'.join(final_rows).encode('utf-8')
        cs = f"blake2s8:{hashlib.blake2s(content, digest_size=8).hexdigest().upper()}"

        out: Dict[str, Any] = {"i": f"m_{map_id}"}
        if d:
            out["d"] = d
        out["cs"] = cs
        return out

    def _file_meta(self, file_path: str, content: str) -> FileMeta:
        size_bytes = os.path.getsize(file_path)
        sha256 = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return FileMeta(
            size_bytes=size_bytes,
            sha256=sha256,
            storage_key=file_path,
            compressed=False,
        )

    def _parse_battle_info(self, content: str) -> Dict[str, Any]:
        # Extract the first BATTLE tag, then read attributes individually (order-agnostic)
        m = re.search(r'<BATTLE[^>]*>', content)
        field_type: Optional[str] = None
        turns: int = 0
        loc_x, loc_y = 0, 0
        start_ts: Optional[int] = None
        end_ts_iso: Optional[str] = None
        if m:
            battle_open = m.group(0)
            f_m = re.search(r'\bf="([^"]*)"', battle_open)
            t2_m = re.search(r'\bt2="([^"]*)"', battle_open)
            turn_m = re.search(r'\bturn="([^"]*)"', battle_open)
            note_m = re.search(r'\bnote="([^"]*)"', battle_open)
            if f_m:
                field_type = f_m.group(1)
            if turn_m:
                try:
                    turns = int(turn_m.group(1))
                except Exception:
                    turns = 0
            if note_m:
                note = note_m.group(1)
                parts = note.split(',')
                if len(parts) >= 2:
                    try:
                        loc_x, loc_y = int(parts[0]), int(parts[1])
                    except Exception:
                        loc_x, loc_y = 0, 0
                if len(parts) >= 3:
                    try:
                        start_ts = int(parts[2])
                    except Exception:
                        start_ts = None
            if t2_m:
                try:
                    end_ts_iso = datetime.fromtimestamp(int(t2_m.group(1)), tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                except Exception:
                    end_ts_iso = None

        battle_id = self._extract_battle_id(content)
        return {
            "battle_id": battle_id,
            "field_type": field_type,
            "turns": turns,
            "loc_x": loc_x,
            "loc_y": loc_y,
            "start_ts_unix": start_ts,
            "end_ts_iso": end_ts_iso,
        }

    def _extract_battle_id(self, content: str) -> int:
        # battleid appears on USER; use the first occurrence
        m = re.search(r'battleid="(\d+)"', content)
        return int(m.group(1)) if m else 0

    def _parse_participants(self, content: str) -> List[Dict[str, Any]]:
        # Find only USER tags INSIDE <BATTLE> tag (not in <TURN>)
        # Extract <BATTLE>...</BATTLE> section first
        battle_section_match = re.search(r'<BATTLE[^>]*>(.*?)</BATTLE>', content, re.DOTALL)
        if not battle_section_match:
            return []
        
        battle_content = battle_section_match.group(1)
        # Remove all <TURN>...</TURN> sections to exclude USER tags from turns
        battle_content_no_turns = re.sub(r'<TURN.*?</TURN>', '', battle_content, flags=re.DOTALL)
        
        # Now find USER tags only from battle_content_no_turns
        tags = re.findall(r'<USER[^>]*/>|<USER[^>]*>', battle_content_no_turns)
        participants: List[Dict[str, Any]] = []
        seen_logins: set[str] = set()
        for tag in tags:
            login_m = re.search(r'\blogin="([^"]+)"', tag)
            if not login_m:
                continue
            login = login_m.group(1)
            if login.startswith('$'):
                continue
            if login in seen_logins:
                continue
            seen_logins.add(login)
            # Extract optional attributes individually (order-agnostic)
            def _int(attr: str) -> int:
                m = re.search(fr'\b{attr}="([^"]*)"', tag)
                try:
                    return int(m.group(1)) if m and m.group(1) != '' else 0
                except Exception:
                    return 0
            def _float(attr: str) -> float:
                m = re.search(fr'\b{attr}="([^"]*)"', tag)
                try:
                    return float(m.group(1)) if m and m.group(1) != '' else 0.0
                except Exception:
                    return 0.0
            def _str(attr: str) -> Optional[str]:
                m = re.search(fr'\b{attr}="([^"]*)"', tag)
                return m.group(1) if m else None

            level = _int('level')
            profession = _int('pro')
            clan = _str('clan')
            side = _int('side')
            rank_points = _float('rank_points')
            pve_points = _int('pve_points')
            gender = _int('man')

            survived = 1
            # if there exists a USER snapshot with HP="0" for this login, mark not survived
            if re.search(fr'<USER[^>]*login="{re.escape(login)}"[^>]*HP="0\b', content):
                survived = 0

            participants.append({
                "login": login,
                "clan": clan or None,
                "profession": profession,
                "side": side,
                "rank_points": rank_points,
                "pve_points": pve_points,
                "level": level,
                "gender": gender,
                "survived": survived,
                "intervened": {"state": 0},  # Will be updated later
                "kills": {"monsters": 0, "players": 0},
                "damage_total": {
                    "monsters": {"HP": 0},
                    "players": {"HP": 0}
                },
                "loot": {
                    "resources": [],
                    "monster_parts": [],
                    "other": []
                },
            })

        return participants

    def _update_interventions(self, content: str, participants: List[Dict[str, Any]]) -> None:
        """Update intervention status for each participant."""
        # Get intervention data using existing function
        intervention_data = self.analyze_battle_interventions(content)
        
        # Create a mapping of login to intervention info
        intervention_map = {}
        for intervention in intervention_data.get('interventions', []):
            login = intervention['login']
            turn = intervention['turn']
            intervention_map[login] = turn
        
        # Update participants with intervention data
        for participant in participants:
            login = participant['login']
            if login in intervention_map:
                participant['intervened'] = {
                    "state": 1,
                    "turn": intervention_map[login]
                }
            else:
                participant['intervened'] = {"state": 0}

    def _update_personal_loot(self, content: str, participants: List[Dict[str, Any]]) -> None:
        """Update personal loot for each participant."""
        for participant in participants:
            login = participant['login']
            personal_loot = self._parse_personal_loot(content, login)
            participant['loot'] = personal_loot

    def _augment_kills_by_turn(self, content: str, participants: List[Dict[str, Any]]) -> None:
        """Assign kills and damage per participant using the new kill parser algorithm."""
        if not participants:
            return
        
        # Get battle_id for the kill parser
        battle_info = self._parse_battle_info(content)
        battle_id = battle_info.get("battle_id", 0)
        
        # Use the new kill parser to get all kills with damage
        kills = self.parse_kills_from_xml(content, battle_id, "frame_only")
        
        # Create login to index mapping
        login_to_idx: Dict[str, int] = {p["login"]: i for i, p in enumerate(participants)}
        
        # Process each kill for kill count and detailed damage tracking
        for kill in kills:
            killer = kill.killer
            victim = kill.victim
            
            if killer not in login_to_idx:
                continue
                
            idx = login_to_idx[killer]
            
            if victim.startswith('$'):
                # Monster kill
                participants[idx]["kills"]["monsters"] += 1
            else:
                # Player kill (but not self-kill)
                if victim != killer:
                    participants[idx]["kills"]["players"] += 1
        
        # Now process all damage (not just kills) for detailed damage tracking
        self._track_detailed_damage(content, participants, login_to_idx)

    def _track_detailed_damage(self, content: str, participants: List[Dict[str, Any]], login_to_idx: Dict[str, int]) -> None:
        """Track detailed damage by type for each participant."""
        # Parse all damage events using existing function
        all_attacks = self.analyze_damage_by_turns(content)
        
        # Map status codes to our damage categories (только специальные эффекты)
        status_code_map = {
            'O': 'Poison',        # Отравление входящие  
            'P': 'Paralysis',     # Парализация
            'N': 'Panic',         # Паника
            'H': 'Hallucinations', # Галлюцинации
            'Z': 'Zombification', # Зомбирование
            # A, B, D, C, V, S, E не считаются как спец урон в JSON
        }
        
        # Process each attack
        for attack in all_attacks:
            attacker = attack['attacker']
            victim = attack['victim']
            
            if attacker not in login_to_idx:
                continue
            
            idx = login_to_idx[attacker]
            
            # Determine target type (monster or player)
            target_type = "monsters" if victim.startswith('$') else "players"
            
            # Add damage by type
            armor_piercing = attack.get('armor_piercing', 0)
            normal_damage = attack.get('normal_damage', 0)
            critical_damage = attack.get('critical_damage', 0)
            
            # Add piercing damage separately if present
            if armor_piercing > 0:
                if "piercing" not in participants[idx]["damage_total"][target_type]:
                    participants[idx]["damage_total"][target_type]["piercing"] = 0
                participants[idx]["damage_total"][target_type]["piercing"] += armor_piercing
            
            # Add critical damage separately if present
            if critical_damage > 0:
                if "critical" not in participants[idx]["damage_total"][target_type]:
                    participants[idx]["damage_total"][target_type]["critical"] = 0
                participants[idx]["damage_total"][target_type]["critical"] += critical_damage
            
            # Add total HP damage (all types combined)
            total_hp_damage = armor_piercing + normal_damage + critical_damage
            if total_hp_damage > 0:
                participants[idx]["damage_total"][target_type]["HP"] += total_hp_damage
            
            # Add special status damage
            status_code = attack.get('status_code')
            status_damage = attack.get('status_damage', 0)
            if status_code and status_damage != 0:
                status_damage = abs(status_damage)  # Always positive for damage tracking
                
                if status_code in status_code_map:
                    damage_category = status_code_map[status_code]
                    # Initialize the field if it doesn't exist
                    if damage_category not in participants[idx]["damage_total"][target_type]:
                        participants[idx]["damage_total"][target_type][damage_category] = 0
                    participants[idx]["damage_total"][target_type][damage_category] += status_damage

    def _parse_monsters(self, content: str) -> Dict[str, Dict[str, Any]]:
        # Monsters at battle start: only those that also appear in TURNs (to avoid inactive placeholders)
        battle_start_block = content.split('</BATTLE>', 1)[0]
        turn_block = content.split('</BATTLE>', 1)[1] if '</BATTLE>' in content else ''
        # All monster logins in initial BATTLE
        initial = re.findall(r'<USER[^>]*login="(\$[^\"]+)"[^>]*level="([^"]*)"[^>]*side="([^"]*)"[^>]*>', battle_start_block)
        # Monster logins that appear in any TURN (state or actions)
        active_logins = set(re.findall(r'<USER[^>]*login="(\$[^\"]+)"', turn_block))
        seen_logins: set[str] = set()
        agg: Dict[str, Dict[str, Any]] = {}
        for login, level, side in initial:
            if login in seen_logins:
                continue
            # Keep only monsters that have any presence in TURNs; if none, skip
            if active_logins and login not in active_logins:
                continue
            seen_logins.add(login)
            # Find the full USER tag for this login to extract def/color
            user_tag_match = re.search(fr'<USER[^>]*login="{re.escape(login)}"[^>]*>', battle_start_block)
            user_tag = user_tag_match.group(0) if user_tag_match else ""
            def_attr_m = re.search(r'\bdef="([^"]*)"', user_tag)
            color_attr_m = re.search(r'\bcolor="([^"]*)"', user_tag)
            def_attr = def_attr_m.group(1) if def_attr_m else None
            color_attr = color_attr_m.group(1) if color_attr_m else None
            kind = self._monster_kind(login)
            # Primary signal for special monsters: underscore in login (e.g., $stich14_1337)
            # Secondary signals: explicit def/color attributes
            has_underscore = ('_' in login)
            is_spec = has_underscore or bool(def_attr) or bool(color_attr)

            # Determine spec value preference: def first, then color
            spec_value = def_attr or color_attr if is_spec else None

            # Aggregate key: split special monsters by unique spec value if present
            if is_spec and spec_value is not None:
                agg_key = f"{kind}_spec::{spec_value}"
            elif is_spec:
                # special without explicit def/color → keep as one bucket
                agg_key = f"{kind}_spec"
            else:
                agg_key = kind

            if agg_key not in agg:
                agg[agg_key] = {
                    "kind": f"{kind}_spec" if is_spec else kind,
                    "spec": spec_value if is_spec else None,
                    "side": int(side) if side else 0,
                    "count": 0,
                    "min_level": 10**9,
                    "max_level": 0,
                }
            lvl = int(level) if level else 0
            agg[agg_key]["count"] += 1
            agg[agg_key]["min_level"] = min(agg[agg_key]["min_level"], lvl)
            agg[agg_key]["max_level"] = max(agg[agg_key]["max_level"], lvl)
        return agg

    def _monster_kind(self, login: str) -> str:
        """Определяет тип монстра по префиксу login. Поддерживает 38 типов монстров."""
        if not login.startswith('$'):
            return 'unknown'
        
        # Извлекаем префикс после $ до первой цифры
        import re
        match = re.match(r'\$([a-zA-Z]+)', login)
        if not match:
            return 'unknown'
        
        prefix = match.group(1).lower()
        
        # Маппинг всех известных типов монстров
        monster_types = {
            'bmi': 'bmi',      # Мина
            'rat': 'rat',      # Крыса-мутант
            'sti': 'sti',      # Стич
            'stich': 'sti',    # Альтернативное написание Стич
            'pco': 'pco',      # робокоп
            'pcb': 'pcb',      # кибер-страж
            'std': 'std',      # Ведьмин студень
            'vzz': 'vzz',      # Вжик
            'tur': 'tur',      # Туррель
            'dev': 'dev',      # Манок
            'bll': 'bll',      # Мяч
            'dog': 'dog',      # Динго
            'srg': 'srg',      # Сержант Мак Грегори
            'enm': 'enm',      # условный противник
            'gek': 'gek',      # Геккон
            'rbt': 'rbt',      # r2-d2(mf)
            'robot': 'robot',  # Механоид
            'scr': 'scr',      # Скорпион
            'scrp': 'scr',     # Альтернативное написание Скорпион
            'wrm': 'wrm',      # Червь
            'spd': 'spd',      # Арахнид
            'zmb': 'zmb',      # Одержимый
            'rdr': 'rdr',      # радар
            'alg': 'alg',      # Диверсант
            'als': 'als',      # Штурмовик
            'alb': 'alb',      # Каратель
            'erg': 'erg',      # Эрго
            'mts': 'mts',      # Богомол
            'crs': 'crs',      # Крашер
            'crm': 'crm',      # Крушителенок
            'cdv': 'cdv',      # клетка
            'hst': 'hst',      # заложник
            'col': 'col',      # Лаборант
            'fgh': 'fgh',      # воин
            'sha': 'sha',      # шаман
            'pjm': 'pjm',      # пси-джаммер
            'rjm': 'rjm',      # джаммер
            'rng': 'rng',      # Рейнджер
        }
        
        return monster_types.get(prefix, 'unknown')

    def _format_monsters(self, agg: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for key in sorted(agg.keys()):
            m = agg[key]
            out.append({
                "kind": m["kind"] if "kind" in m else key,
                "spec": m.get("spec", None),
                "side": m.get("side", 0),
                "count": m.get("count", 0),
                "min_level": 0 if m.get("min_level", 0) == 10**9 else m.get("min_level", 0),
                "max_level": m.get("max_level", 0),
            })
        return out

    def _parse_loot(self, content: str) -> Dict[str, Any]:
        # Aggregate pickups t="8" but only inside participants' USER blocks within TURNs; dedupe by item ID globally
        # Validate against items that actually exist on the map (<O ... bx/by .../>)
        by_name: Dict[str, int] = {}
        seen_ids_global: set[str] = set()
        map_ids: set[str] = set(re.findall(r'<O[^>]*\bid="([^"]+)"[^>]*\bbx="[^"]+"[^>]*\bby="[^"]+"[^>]*/>', content))
        # Collect participant logins
        participant_logins = set(re.findall(r'<USER[^>]*login="([^$][^"]*)"', content))
        # Iterate TURNs and then USER blocks for participants
        for turn_m in re.finditer(r'<TURN[^>]*>([\s\S]*?)</TURN>', content):
            turn_body = turn_m.group(1)
            for user_m in re.finditer(r'<USER[^>]*login="([^"]+)"[^>]*>([\s\S]*?)</USER>', turn_body):
                actor = user_m.group(1)
                if actor not in participant_logins:
                    continue
                body = user_m.group(2)
                for tag_m in re.finditer(r'<a[^>]*\bt="8"[^>]*/>', body):
                    tag = tag_m.group(0)
                    id_m = re.search(r'\bid="([^"]+)"', tag)
                    name_m = re.search(r'\btxt="([^"]+)"', tag)
                    count_m = re.search(r'\bcount="(\d+)"', tag)
                    if not id_m or not name_m or not count_m:
                        continue
                    item_id = id_m.group(1)
                    if map_ids and item_id not in map_ids:
                        continue
                    if item_id in seen_ids_global:
                        continue
                    seen_ids_global.add(item_id)
                    name = name_m.group(1)
                    qty = int(count_m.group(1))
                    by_name[name] = by_name.get(name, 0) + qty

        resources: List[Dict[str, Any]] = []
        monster_parts: List[Dict[str, Any]] = []
        other: List[Dict[str, Any]] = []

        for name, qty in sorted(by_name.items()):
            if name in self.resource_types:
                resources.append({"name": name, "qty": qty})
            elif name in self.monster_parts:
                monster_parts.append({"name": name, "qty": qty})
            else:
                other.append({"item_id": None, "item_name": name, "qty": qty})

        return {"resources": resources, "monster_parts": monster_parts, "other": other}

    def _parse_personal_loot(self, content: str, player_login: str) -> Dict[str, Any]:
        # Parse loot for a specific player
        by_name: Dict[str, int] = {}
        seen_ids: set[str] = set()
        map_ids: set[str] = set(re.findall(r'<O[^>]*\bid="([^"]+)"[^>]*\bbx="[^"]+"[^>]*\bby="[^"]+"[^>]*/>', content))
        
        # Iterate TURNs and find USER blocks for this specific player
        for turn_m in re.finditer(r'<TURN[^>]*>([\s\S]*?)</TURN>', content):
            turn_body = turn_m.group(1)
            for user_m in re.finditer(r'<USER[^>]*login="([^"]+)"[^>]*>([\s\S]*?)</USER>', turn_body):
                actor = user_m.group(1)
                if actor != player_login:
                    continue
                body = user_m.group(2)
                for tag_m in re.finditer(r'<a[^>]*\bt="8"[^>]*/>', body):
                    tag = tag_m.group(0)
                    id_m = re.search(r'\bid="([^"]+)"', tag)
                    name_m = re.search(r'\btxt="([^"]+)"', tag)
                    count_m = re.search(r'\bcount="(\d+)"', tag)
                    if not id_m or not name_m or not count_m:
                        continue
                    item_id = id_m.group(1)
                    if map_ids and item_id not in map_ids:
                        continue
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                    name = name_m.group(1)
                    qty = int(count_m.group(1))
                    by_name[name] = by_name.get(name, 0) + qty

        resources: List[Dict[str, Any]] = []
        monster_parts: List[Dict[str, Any]] = []
        other: List[Dict[str, Any]] = []

        for name, qty in sorted(by_name.items()):
            if name in self.resource_types:
                resources.append({"name": name, "qty": qty})
            elif name in self.monster_parts:
                monster_parts.append({"name": name, "qty": qty})
            else:
                other.append({"item_id": None, "item_name": name, "qty": qty})

        return {"resources": resources, "monster_parts": monster_parts, "other": other}

    def parse_damage(self, hp_str: str) -> int:
        """Достаём число урона/лечения из атрибута HP.
        
        Поддерживаемые форматы:
        - Простой: '60', '0:60', '0:-52'
        - DoT: '0:A7', '0:A-15' (урон от статусных эффектов)
        - Расширенный: '0:18:N4' (бронебойный:обычный:код_урон)
        
        Возвращает суммарный урон (обычный + статусный).
        Положительные значения — прямой урон.
        Отрицательные с кодом — DoT урон от статусных эффектов.
        Отрицательные без кода — лечение.
        """
        if not hp_str:
            return 0
        
        # Простой формат без двоеточий: "60"
        if ':' not in hp_str:
            try:
                return abs(int(hp_str))
            except ValueError:
                return 0
        
        # Проверяем расширенный формат "бронебойный:обычный:код_урон"
        if hp_str.count(':') == 2:
            parts = hp_str.split(':')
            if len(parts) == 3:
                try:
                    armor_piercing = int(parts[0])
                    normal_damage = int(parts[1])
                    # Третья часть содержит код и урон, например "N4", "H5"
                    status_part = parts[2]
                    # Извлекаем код (буквы) и урон (число в конце)
                    status_match = re.match(r'^([A-Z]+)(-?\d+)$', status_part)
                    if status_match:
                        status_code = status_match.group(1)
                        status_damage = int(status_match.group(2))
                        # Возвращаем суммарный урон (обычный + статусный)
                        return normal_damage + abs(status_damage)
                except ValueError:
                    pass  # Продолжаем к простому формату
        
        # DoT формат "0:A7" или простой "0:60"
        if hp_str.count(':') == 1:
            parts = hp_str.split(':')
            if len(parts) == 2:
                try:
                    first_part = parts[0]
                    second_part = parts[1]
                    
                    # Проверяем DoT формат "0:A7" или "0:A-15"
                    dot_match = re.match(r'^([A-Z]+)(-?\d+)$', second_part)
                    if dot_match:
                        status_code = dot_match.group(1)
                        status_damage = int(dot_match.group(2))
                        return abs(status_damage)
                    
                    # Простой формат "0:60" или "0:-52"
                    try:
                        damage = int(second_part)
                        return abs(damage)
                    except ValueError:
                        pass
                        
                except ValueError:
                    pass
        
        # Fallback: ищем последнее число
        simple_match = HP_NUM_RE.search(hp_str.strip())
        return abs(int(simple_match.group(1))) if simple_match else 0

    def parse_damage_detailed(self, hp_str: str) -> Dict[str, Any]:
        """Детальный парсинг урона с разбивкой по компонентам.
        
        Возвращает словарь с полной информацией об уроне:
        {
            'total_damage': int,
            'armor_piercing': int,
            'normal_damage': int,
            'status_code': str | None,
            'status_damage': int,
            'status_name': str | None,
            'format_type': str  # 'simple', 'dot', 'extended'
        }
        """
        if not hp_str:
            return {
                'total_damage': 0,
                'armor_piercing': 0,
                'normal_damage': 0,
                'status_code': None,
                'status_damage': 0,
                'status_name': None,
                'format_type': 'simple'
            }
        
        status_names = {
            'A': 'отравление',
            'O': 'отравление входящее',
            'B': 'ожог',
            'D': 'ослепление',
            'P': 'паралич',
            'N': 'паника',
            'H': 'галлюцинации',
            'C': 'контузия',
            'Z': 'зомбирование',
            'V': 'биологическое заражение',
            'S': 'ударное',
            'E': 'энергетическое'
        }
        
        # Простой формат без двоеточий: "60"
        if ':' not in hp_str:
            try:
                damage = abs(int(hp_str))
                return {
                    'total_damage': damage,
                    'armor_piercing': 0,
                    'normal_damage': damage,
                    'status_code': None,
                    'status_damage': 0,
                    'status_name': None,
                    'format_type': 'simple'
                }
            except ValueError:
                pass
        
        # Расширенный формат "бронебойный:обычный:код_урон"
        if hp_str.count(':') == 2:
            parts = hp_str.split(':')
            if len(parts) == 3:
                try:
                    armor_piercing = int(parts[0])
                    normal_damage = int(parts[1])
                    status_part = parts[2]
                    
                    status_match = re.match(r'^([A-Z]+)(-?\d+)$', status_part)
                    if status_match:
                        status_code = status_match.group(1)
                        status_damage = abs(int(status_match.group(2)))
                        return {
                            'total_damage': normal_damage + status_damage,
                            'armor_piercing': armor_piercing,
                            'normal_damage': normal_damage,
                            'status_code': status_code,
                            'status_damage': status_damage,
                            'status_name': status_names.get(status_code, f'неизвестный({status_code})'),
                            'format_type': 'extended'
                        }
                except ValueError:
                    pass
        
        # DoT формат "0:A7", простой "0:60" или бронебойный "5:25"
        if hp_str.count(':') == 1:
            parts = hp_str.split(':')
            if len(parts) == 2:
                try:
                    first_part = parts[0]
                    second_part = parts[1]
                    
                    # Проверяем DoT формат "0:A7" или "0:A-15"
                    dot_match = re.match(r'^([A-Z]+)(-?\d+)$', second_part)
                    if dot_match:
                        status_code = dot_match.group(1)
                        status_damage = abs(int(dot_match.group(2)))
                        return {
                            'total_damage': status_damage,
                            'armor_piercing': 0,
                            'normal_damage': 0,
                            'status_code': status_code,
                            'status_damage': status_damage,
                            'status_name': status_names.get(status_code, f'неизвестный({status_code})'),
                            'format_type': 'dot'
                        }
                    
                    # Формат с типом урона "тип:урон" где тип: 0=обычный, 1=крит, 2=бронебой
                    try:
                        damage_type = int(first_part)
                        damage_value = int(second_part)
                        
                        # Определяем тип урона
                        if damage_type == 1:
                            # Критический урон
                            return {
                                'total_damage': damage_value,
                                'armor_piercing': 0,
                                'normal_damage': 0,
                                'critical_damage': damage_value,
                                'status_code': None,
                                'status_damage': 0,
                                'status_name': None,
                                'format_type': 'critical'
                            }
                        elif damage_type == 2:
                            # Бронебойный урон
                            return {
                                'total_damage': damage_value,
                                'armor_piercing': damage_value,
                                'normal_damage': 0,
                                'critical_damage': 0,
                                'status_code': None,
                                'status_damage': 0,
                                'status_name': None,
                                'format_type': 'piercing'
                            }
                        else:
                            # Обычный урон (тип 0 или любой другой)
                            return {
                                'total_damage': damage_value,
                                'armor_piercing': 0,
                                'normal_damage': damage_value,
                                'critical_damage': 0,
                                'status_code': None,
                                'status_damage': 0,
                                'status_name': None,
                                'format_type': 'simple'
                            }
                    except ValueError:
                        pass
                        
                except ValueError:
                    pass
        
        # Fallback
        return {
            'total_damage': 0,
            'armor_piercing': 0,
            'normal_damage': 0,
            'status_code': None,
            'status_damage': 0,
            'status_name': None,
            'format_type': 'simple'
        }

    def analyze_damage_by_turns(self, content: str) -> List[Dict[str, Any]]:
        """Анализирует урон по ходам с детальной разбивкой.
        
        Возвращает список атак с полной информацией об уроне.
        """
        # Дедупликация
        second_battle_pos = content.find('<BATTLE', content.find('<BATTLE') + 1)
        if second_battle_pos != -1:
            content = content[:second_battle_pos]
        
        # Найдем все ходы
        turn_pattern = r'<TURN turn="(\d+)"[^>]*>(.*?)</TURN>'
        turns = re.findall(turn_pattern, content, re.DOTALL)
        
        all_attacks = []
        
        for turn_num, turn_content in turns:
            # Найдем все USER блоки с содержимым (не самозакрывающиеся)
            users = []
            
            # Найдем все USER теги
            all_user_pattern = r'<USER login="([^"]+)"[^>]*>'
            for match in re.finditer(all_user_pattern, turn_content):
                login = match.group(1)
                full_tag = match.group(0)
                is_self_closing = full_tag.endswith('/>')
                
                if not is_self_closing:
                    # Это открывающий тег, найдем содержимое до </USER>
                    start_pos = match.end()
                    end_pattern = r'</USER>'
                    end_match = re.search(end_pattern, turn_content[start_pos:])
                    if end_match:
                        end_pos = start_pos + end_match.start()
                        user_content = turn_content[start_pos:end_pos]
                        if user_content.strip():
                            users.append((login, user_content))
            
            for attacker_login, user_content in users:
                # Найдем все атаки t="5" с HP
                attack_pattern = r'<a sf="(\d+)" t="5"[^>]*HP="([^"]+)"[^>]*>'
                attacks = re.findall(attack_pattern, user_content)
                
                for sf, hp_str in attacks:
                    damage_info = self.parse_damage_detailed(hp_str)
                    if damage_info['total_damage'] > 0:
                        # Найдем жертву из login атрибута
                        full_attack_pattern = rf'<a sf="{sf}" t="5"[^>]*HP="{re.escape(hp_str)}"[^>]*>'
                        full_match = re.search(full_attack_pattern, user_content)
                        victim_login = None
                        if full_match:
                            login_match = re.search(r'login="([^"]+)"', full_match.group(0))
                            victim_login = login_match.group(1) if login_match else None
                        
                        # Найдем тип атаки
                        attack_type = None
                        type_match = re.search(r'type="([^"]+)"', full_match.group(0))
                        if type_match:
                            attack_type = type_match.group(1)
                        
                        attack_data = {
                            'turn': int(turn_num),
                            'frame': int(sf),
                            'attacker': attacker_login,
                            'victim': victim_login if victim_login else 'координаты',
                            'attack_type': attack_type,
                            'attack_type_name': self._get_attack_type_name(attack_type),
                            'hp_string': hp_str,
                            **damage_info
                        }
                        all_attacks.append(attack_data)
        
        return sorted(all_attacks, key=lambda x: (x['turn'], x['frame']))

    def analyze_stance_changes(self, content: str) -> List[Dict[str, Any]]:
        """Анализирует смены стоек по ходам.
        
        Возвращает список изменений стоек с детальной информацией.
        """
        # Дедупликация
        second_battle_pos = content.find('<BATTLE', content.find('<BATTLE') + 1)
        if second_battle_pos != -1:
            content = content[:second_battle_pos]
        
        # Найдем все ходы
        turn_pattern = r'<TURN turn="(\d+)"[^>]*>(.*?)</TURN>'
        turns = re.findall(turn_pattern, content, re.DOTALL)
        
        all_stance_changes = []
        
        for turn_num, turn_content in turns:
            # Найдем все USER блоки (только с содержимым)
            user_pattern = r'<USER login="([^"]+)"[^>]*>(.*?)</USER>'
            users = re.findall(user_pattern, turn_content, re.DOTALL)
            users = [(login, user_content) for login, user_content in users if user_content.strip()]
            
            for player_login, user_content in users:
                # Найдем смены стоек t="6"
                stance_pattern = r'<a sf="(\d+)" t="6"[^>]*/?>'
                stance_matches = re.finditer(stance_pattern, user_content)
                
                for match in stance_matches:
                    sf = match.group(1)
                    full_tag = match.group(0)
                    
                    # Ищем атрибут run в полном теге
                    run_match = re.search(r'run="([^"]+)"', full_tag)
                    run_value = run_match.group(1) if run_match else None
                    
                    stance_data = {
                        'turn': int(turn_num),
                        'frame': int(sf),
                        'player': player_login,
                        'run_value': run_value,
                        'stance_name': self._get_stance_name(run_value)
                    }
                    all_stance_changes.append(stance_data)
                
                # Найдем побеги из боя t="9"
                escape_pattern = r'<a sf="(\d+)" t="9"[^>]*/?>'
                escapes = re.findall(escape_pattern, user_content)
                
                for sf in escapes:
                    escape_data = {
                        'turn': int(turn_num),
                        'frame': int(sf),
                        'player': player_login,
                        'run_value': 'escape',
                        'stance_name': 'Убежал из боя'
                    }
                    all_stance_changes.append(escape_data)
        
        return sorted(all_stance_changes, key=lambda x: (x['turn'], x['frame']))

    def analyze_battle_interventions(self, content: str) -> Dict[str, Any]:
        """Анализирует вмешательства в бой - игроков, которые присоединились после начала.
        
        Возвращает информацию о первоначальных участниках и вмешательствах по ходам.
        """
        # Дедупликация
        second_battle_pos = content.find('<BATTLE', content.find('<BATTLE') + 1)
        if second_battle_pos != -1:
            content = content[:second_battle_pos]
        
        # Извлекаем изначальных участников из блока BATTLE
        battle_match = re.search(r'<BATTLE[^>]*>(.*?)</BATTLE>', content, re.DOTALL)
        if not battle_match:
            return {'error': 'BATTLE блок не найден'}
        
        battle_content = battle_match.group(1)
        
        # Находим всех изначальных участников (как самозакрывающиеся, так и обычные теги)
        initial_users = set()
        
        # Самозакрывающиеся теги <USER ... />
        self_closing_pattern = r'<USER login="([^"]+)"[^>]*/?>'
        for match in re.finditer(self_closing_pattern, battle_content):
            login = match.group(1)
            initial_users.add(login)
        
        # Обычные теги <USER ...>...</USER>
        regular_pattern = r'<USER login="([^"]+)"[^>]*>(.*?)</USER>'
        for match in re.finditer(regular_pattern, battle_content, re.DOTALL):
            login = match.group(1)
            initial_users.add(login)
        
        # Анализируем ходы
        turn_pattern = r'<TURN turn="(\d+)"[^>]*>(.*?)</TURN>'
        turns = re.findall(turn_pattern, content, re.DOTALL)
        
        interventions = []
        all_seen_users = set(initial_users)
        
        for turn_num, turn_content in turns:
            # Находим всех пользователей в этом ходу
            turn_users = set()
            user_blocks = re.findall(r'<USER login="([^"]+)"[^>]*>(.*?)</USER>', turn_content, re.DOTALL)
            
            for login, user_content in user_blocks:
                turn_users.add(login)
                
                # Проверяем, новый ли это пользователь
                if login not in all_seen_users:
                    # Ищем sf атрибут как признак появления на карте
                    sf_match = re.search(r'<a sf="(\d+)"', user_content)
                    appearance_frame = int(sf_match.group(1)) if sf_match else None
                    
                    # Определяем тип участника
                    participant_type = 'monster' if login.startswith('$') else 'player'
                    
                    intervention = {
                        'turn': int(turn_num),
                        'login': login,
                        'type': participant_type,
                        'appearance_frame': appearance_frame,
                        'has_actions': bool(user_content.strip())
                    }
                    interventions.append(intervention)
                    all_seen_users.add(login)
        
        # Разделяем изначальных участников по типам
        initial_players = [login for login in initial_users if not login.startswith('$')]
        initial_monsters = [login for login in initial_users if login.startswith('$')]
        
        return {
            'initial_participants': {
                'players': initial_players,
                'monsters': initial_monsters,
                'total': len(initial_users)
            },
            'interventions': interventions,
            'intervention_summary': {
                'total_interventions': len(interventions),
                'player_interventions': len([i for i in interventions if i['type'] == 'player']),
                'monster_interventions': len([i for i in interventions if i['type'] == 'monster']),
                'turns_with_interventions': len(set(i['turn'] for i in interventions))
            }
        }

    def _get_stance_name(self, run_value: str) -> str:
        """Возвращает название стойки по коду run"""
        stance_names = {
            '1': 'Ходьба',
            '2': 'Бег', 
            '3': 'Сел',
            '4': 'Присел',
            '5': 'Лег/Укрылся'
        }
        return stance_names.get(str(run_value), f'Неизвестная стойка ({run_value})') if run_value else 'Смена стойки'

    def _get_attack_type_name(self, attack_type: str) -> str:
        """Возвращает название типа атаки по коду"""
        attack_types = {
            'useperk': 'Использовать перк',
            '0': 'Ударить',
            '1': 'Ударить',
            '2': 'Выстрел навскидку',
            '3': 'Прицельный выстрел',
            '4': 'Очередь (3 патрона)',
            '5': 'Очередь (4 патрона)',
            '6': 'Очередь (5 патронов)',
            '7': 'Метнуть по цели',
            '8': 'Использовать на цели',
            '9': 'Запустить по цели',
            '10': 'Выстрелить',
            '11': 'Короткий луч',
            '12': 'Длинный луч',
            '13': 'Применить на себя',
            '14': 'Применить на цель',
            '15': 'Применить на цель',
            '16': 'Применить по цели',
            '29': 'Применить на себя',
            '30': 'Использовать пси по цели'
        }
        return attack_types.get(str(attack_type), f'Неизвестный тип ({attack_type})')

    def parse_kills_from_xml(self, xml_text: str, battle_id: int | None = None,
                             mode: str = "frame_only") -> List[Kill]:
        """
        Парсит убийства из XML по алгоритму пользователя (regex-based).
        
        mode:
          - "frame_only": суммируем урон (t=5) только в том же кадре sf, где зафиксирован kill (t=20).
          - "accumulate_to_death": суммируем урон по жертве от этого киллера во всех кадрах <= sf смерти.
        
        Возвращает список Kill, отсортированный по (turn, sf).
        """
        if battle_id is None:
            battle_id = -1

        kills = []
        
        # Идём по ходам по порядку
        for turn_match in re.finditer(r'<TURN[^>]*turn="(\d+)"[^>]*>([\s\S]*?)</TURN>', xml_text):
            turn = int(turn_match.group(1))
            turn_body = turn_match.group(2)
            
            # 1) Собираем действия по каждому USER (участнику)
            user_actions = defaultdict(list)
            deaths = set()
            
            # Парсим USER блоки в этом TURN - используем более точный подход
            # Находим все USER теги и их позиции
            user_starts = []
            for match in re.finditer(r'<USER[^>]*login="([^"]+)"[^>]*>', turn_body):
                user_starts.append((match.start(), match.end(), match.group(1)))
            
            # Для каждого USER находим соответствующий </USER>
            for i, (start, user_tag_end, ulogin) in enumerate(user_starts):
                # Ищем следующий </USER> после этого USER
                next_start = user_starts[i + 1][0] if i + 1 < len(user_starts) else len(turn_body)
                user_section = turn_body[user_tag_end:next_start]
                
                # Находим последний </USER> в этой секции
                last_user_end = user_section.rfind('</USER>')
                if last_user_end != -1:
                    user_body = user_section[:last_user_end]
                else:
                    user_body = user_section
                
                # Парсим действия <a> в этом USER
                for a_match in re.finditer(r'<a[^>]*sf="(\d+)"[^>]*t="(\d+)"[^>]*/>', user_body):
                    sf = int(a_match.group(1))
                    t = int(a_match.group(2))
                    
                    # Извлекаем дополнительные атрибуты
                    code_match = re.search(r'code="([^"]*)"', a_match.group(0))
                    target_match = re.search(r'login="([^"]*)"', a_match.group(0))
                    hp_match = re.search(r'HP="([^"]*)"', a_match.group(0))
                    type_match = re.search(r'type="([^"]*)"', a_match.group(0))
                    
                    rec = {
                        "sf": sf,
                        "t": t,
                        "code": code_match.group(1) if code_match else None,
                        "target": target_match.group(1) if target_match else None,
                        "hp": hp_match.group(1) if hp_match else None,
                        "type": type_match.group(1) if type_match else None,
                    }
                    user_actions[ulogin].append(rec)
                    
                    # фиксируем смерть (t=7) в индексе deaths
                    if t == 7:
                        deaths.add((ulogin, sf))

            # 2) Ищем строки "kill credit": у кого в действиях есть t=20 code=7 login="<victim>"
            for killer, acts in user_actions.items():
                # индексируем по кадру и цели, чтобы быстро суммировать урон
                acts_by_sf_target = defaultdict(list)
                # для режима accumulate_to_death — индекс по цели в разрезе sf
                acts_by_target_all = defaultdict(list)

                for rec in acts:
                    if rec["t"] == 5 and rec["target"]:
                        key = (rec["sf"], rec["target"])
                        acts_by_sf_target[key].append(rec)
                        acts_by_target_all[rec["target"]].append(rec)

                for rec in acts:
                    if rec["t"] == 20 and rec.get("code") == "7" and rec.get("target"):
                        victim = rec["target"]
                        sf = rec["sf"]
                        # killer - это владелец USER блока, victim - это target в событии t="20"

                        # 2.a) проверка, что у жертвы есть t=7 в этом же кадре (необязательно, но полезно)
                        has_death_mark = (victim, sf) in deaths

                        # 2.b) считаем урон
                        damage = 0
                        shots = 0

                        if mode == "frame_only":
                            # суммируем только попадания этого киллера по этой жертве в том же sf
                            for hit in acts_by_sf_target.get((sf, victim), []):
                                dmg = self.parse_damage(hit["hp"])
                                damage += dmg
                                shots += 1

                        elif mode == "accumulate_to_death":
                            # суммируем все попадания этого киллера по жертве до кадра смерти включительно
                            for hit in acts_by_target_all.get(victim, []):
                                if hit["sf"] <= sf:
                                    dmg = self.parse_damage(hit["hp"])
                                    damage += dmg
                                    shots += 1

                        kills.append(Kill(battle_id, turn, sf, killer, victim, damage, shots))

        # Сортируем по (turn, sf)
        kills.sort(key=lambda k: (k.turn, k.sf, k.killer, k.victim))
        return kills


