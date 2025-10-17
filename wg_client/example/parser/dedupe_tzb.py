#!/usr/bin/env python3
import sys
import os


def dedupe_tzb_content(content: str) -> str:
    # Remove <BLOOK> and </BLOOK> tags if present
    content = content.replace('<BLOOK>', '').replace('</BLOOK>', '')
    
    # Find starts of <BATTLE
    indices = []
    start = 0
    while True:
        i = content.find('<BATTLE', start)
        if i == -1:
            break
        indices.append(i)
        start = i + 7

    if len(indices) < 2:
        return content

    # If a second <BATTLE> exists, assume concatenated duplication; keep only until second start
    second = indices[1]
    first_part = content[:second]

    # Heuristic validation: if the rest begins with the first part (or its large prefix), it's duplicated
    rest = content[second:second + len(first_part)]
    # If not similar, still cut at second to avoid double counting
    return first_part


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python3 dedupe_tzb.py INPUT.tzb [OUTPUT.tzb]', file=sys.stderr)
        sys.exit(2)

    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) >= 3 else None

    with open(in_path, 'r', encoding='utf-8') as f:
        content = f.read()

    dedup = dedupe_tzb_content(content)

    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(dedup)
        print(f"Wrote deduplicated file: {out_path}")
    else:
        sys.stdout.write(dedup)


if __name__ == '__main__':
    main()


