#!/usr/bin/env python3
"""
Export all task data from the Lotus database to a JSON file.

Handles both old (v1) and new (v2) schemas gracefully — reads whatever
columns exist and exports them all. This ensures no data is lost regardless
of which schema version the database is on.

Usage:
    python backend/scripts/export_data.py [--db PATH] [--output PATH]

Defaults:
    --db      backend/tasks.db
    --output  backend/data_export.json
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime


def get_table_columns(cursor: sqlite3.Cursor, table: str) -> list[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def export_table(cursor: sqlite3.Cursor, table: str) -> list[dict]:
    columns = get_table_columns(cursor, table)
    if not columns:
        return []
    cursor.execute(f"SELECT {', '.join(columns)} FROM {table}")
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def main():
    parser = argparse.ArgumentParser(description="Export Lotus task data")
    parser.add_argument("--db", default="backend/tasks.db", help="Path to SQLite database")
    parser.add_argument("--output", default="backend/data_export.json", help="Output JSON file")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database not found at {args.db}")
        print("No data to export. If your database is elsewhere, use --db PATH")
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    # Discover which tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    existing_tables = {row[0] for row in cursor.fetchall()}

    tables_to_export = ["tasks", "comments", "attachments", "value_streams", "shortcut_configs"]
    export = {"exported_at": datetime.utcnow().isoformat(), "tables": {}}

    for table in tables_to_export:
        if table in existing_tables:
            rows = export_table(cursor, table)
            export["tables"][table] = rows
            print(f"  {table}: {len(rows)} rows")
        else:
            print(f"  {table}: (table not found, skipping)")

    conn.close()

    with open(args.output, "w") as f:
        json.dump(export, f, indent=2, default=str)

    total = sum(len(rows) for rows in export["tables"].values())
    print(f"\nExported {total} total rows to {args.output}")


if __name__ == "__main__":
    main()
