#!/usr/bin/env python3
import sys
import json
from battle_parser import BattleParser
from dedupe_tzb import dedupe_tzb_content


def _dedupe_in_place(file_path: str) -> None:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    deduped_content = dedupe_tzb_content(content)
    
    if deduped_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(deduped_content)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 main.py /absolute/path/to/file.tzb", file=sys.stderr)
        sys.exit(2)

    file_path = sys.argv[1]
    # Always dedupe in-place before parsing
    _dedupe_in_place(file_path)
    parser = BattleParser()
    result = parser.parse_file(file_path)

    # Output JSON per requested schema
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


