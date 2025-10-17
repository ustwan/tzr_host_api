#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

from app.database import BattleDatabase
from app.loader import BattleLoader
from app.parser import BattleParser


async def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: run_batch.py /absolute/path/to/dir [glob=*.tzb*]", file=sys.stderr)
        return 2

    directory = sys.argv[1]
    pattern = sys.argv[2] if len(sys.argv) > 2 else "*.tzb*"

    # Ensure DB_MODE present (default test)
    os.environ.setdefault("DB_MODE", "test")

    db = BattleDatabase()
    parser = BattleParser()
    loader = BattleLoader(db, parser)

    stats = await loader.load_battles_from_directory(directory, pattern)
    print(stats)
    await db.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))



