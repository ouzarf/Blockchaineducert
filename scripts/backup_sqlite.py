"""Create a consistent SQLite backup for EduCert.

Usage (from the project root):
    python scripts/backup_sqlite.py
    python scripts/backup_sqlite.py --database data/educert.sqlite3 --output backups
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/educert.sqlite3")
    parser.add_argument("--output", default="backups")
    args = parser.parse_args()
    source = Path(args.database)
    if not source.exists():
        raise SystemExit(f"Base SQLite introuvable : {source}")
    destination_dir = Path(args.output)
    destination_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_dir / f"educert_{stamp}.sqlite3"
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    print(f"Sauvegarde créée : {destination}")


if __name__ == "__main__":
    main()
