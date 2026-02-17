#!/usr/bin/env python3
"""
Import task data from a JSON export into the Lotus v2 database.

Maps old schema fields to the new v2 schema, dropping columns that no longer
exist while preserving all core task data. Safe to run on a fresh database —
creates tables if they don't exist.

Usage:
    python backend/scripts/import_data.py [--input PATH] [--db PATH]

Defaults:
    --input   backend/data_export.json
    --db      backend/tasks.db
"""
import argparse
import json
import os
import sqlite3
import sys

# v2 schema column definitions (source of truth: backend/db/models.py)
V2_COLUMNS = {
    "tasks": [
        "id", "title", "status", "assignee", "start_date", "due_date",
        "value_stream", "description", "notes", "created_at", "updated_at",
        "completed_at", "case_study_slug",
    ],
    "comments": ["id", "task_id", "text", "author", "created_at"],
    "attachments": ["id", "task_id", "url"],
    "value_streams": ["id", "name", "color", "created_at", "updated_at"],
    "shortcut_configs": [
        "id", "category", "action", "key", "modifiers", "enabled",
        "description", "user_id", "is_default", "created_at", "updated_at",
    ],
}

CREATE_STATEMENTS = {
    "tasks": """CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL,
        assignee TEXT NOT NULL, start_date TEXT, due_date TEXT,
        value_stream TEXT, description TEXT, notes TEXT,
        created_at DATETIME, updated_at DATETIME,
        completed_at DATETIME, case_study_slug TEXT
    )""",
    "comments": """CREATE TABLE IF NOT EXISTS comments (
        id TEXT PRIMARY KEY, task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
        text TEXT NOT NULL, author TEXT NOT NULL, created_at DATETIME
    )""",
    "attachments": """CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE, url TEXT NOT NULL
    )""",
    "value_streams": """CREATE TABLE IF NOT EXISTS value_streams (
        id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, color TEXT,
        created_at DATETIME, updated_at DATETIME
    )""",
    "shortcut_configs": """CREATE TABLE IF NOT EXISTS shortcut_configs (
        id TEXT PRIMARY KEY, category TEXT NOT NULL, action TEXT NOT NULL,
        key TEXT NOT NULL, modifiers JSON, enabled BOOLEAN DEFAULT 1,
        description TEXT NOT NULL, user_id INTEGER, is_default BOOLEAN DEFAULT 1,
        created_at DATETIME, updated_at DATETIME
    )""",
}


def main():
    parser = argparse.ArgumentParser(description="Import Lotus task data")
    parser.add_argument("--input", default="backend/data_export.json", help="Input JSON file")
    parser.add_argument("--db", default="backend/tasks.db", help="Path to SQLite database")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Export file not found at {args.input}")
        sys.exit(1)

    with open(args.input) as f:
        data = json.load(f)

    print(f"Export created at: {data.get('exported_at', 'unknown')}")

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    # Create tables
    for table, ddl in CREATE_STATEMENTS.items():
        cursor.execute(ddl)

    # Import order matters (tasks before comments/attachments due to FK)
    import_order = ["value_streams", "tasks", "comments", "attachments", "shortcut_configs"]

    for table in import_order:
        rows = data.get("tables", {}).get(table, [])
        if not rows:
            continue

        v2_cols = V2_COLUMNS[table]
        imported = 0

        for row in rows:
            # Only keep columns that exist in v2 schema
            filtered = {k: v for k, v in row.items() if k in v2_cols}
            if not filtered:
                continue

            cols = list(filtered.keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)

            try:
                cursor.execute(
                    f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})",
                    list(filtered.values()),
                )
                imported += 1
            except sqlite3.Error as e:
                print(f"  Warning: skipped row in {table}: {e}")

        print(f"  {table}: {imported}/{len(rows)} rows imported")

    conn.commit()
    conn.close()
    print(f"\nImport complete. Database: {args.db}")


if __name__ == "__main__":
    main()
