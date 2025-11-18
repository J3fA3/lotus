"""
Migration: Add Phase 2 AI Assistant Tables

This migration adds the following changes for Phase 2:
1. New columns to tasks table:
   - confidence_score: AI confidence when task was created (0.0-1.0)
   - source_context_id: Links to ContextItem that generated this task
   - auto_created: Whether task was auto-created by AI (vs user approval)

2. New tables:
   - chat_messages: Chat conversation history between user and AI Assistant
   - feedback_events: User feedback on AI-proposed tasks for learning

Run this migration if you have an existing database from Phase 1.
For new installations, these tables are created automatically by init_db().
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from db.database import engine


async def run_migration():
    """Run the migration to add Phase 2 tables and columns."""
    print("🔄 Starting Phase 2 AI Assistant migration...")

    async with engine.begin() as conn:
        # Step 1: Add new columns to tasks table
        print("📊 Adding new columns to tasks table...")

        # Check if columns already exist
        result = await conn.execute(text("PRAGMA table_info(tasks)"))
        existing_columns = {row[1] for row in result.fetchall()}

        if "confidence_score" not in existing_columns:
            await conn.execute(text(
                "ALTER TABLE tasks ADD COLUMN confidence_score REAL"
            ))
            print("  ✓ Added confidence_score column")
        else:
            print("  ⚠ confidence_score column already exists, skipping")

        if "source_context_id" not in existing_columns:
            await conn.execute(text(
                "ALTER TABLE tasks ADD COLUMN source_context_id INTEGER"
            ))
            print("  ✓ Added source_context_id column")
        else:
            print("  ⚠ source_context_id column already exists, skipping")

        if "auto_created" not in existing_columns:
            await conn.execute(text(
                "ALTER TABLE tasks ADD COLUMN auto_created BOOLEAN DEFAULT 0"
            ))
            print("  ✓ Added auto_created column")
        else:
            print("  ⚠ auto_created column already exists, skipping")

        # Step 2: Create chat_messages table
        print("📊 Creating chat_messages table...")
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages'"
        ))
        if not result.scalar():
            await conn.execute(text("""
                CREATE TABLE chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await conn.execute(text(
                "CREATE INDEX ix_chat_messages_session_id ON chat_messages(session_id)"
            ))
            await conn.execute(text(
                "CREATE INDEX ix_chat_messages_created_at ON chat_messages(created_at)"
            ))
            print("  ✓ Created chat_messages table with indexes")
        else:
            print("  ⚠ chat_messages table already exists, skipping")

        # Step 3: Create feedback_events table
        print("📊 Creating feedback_events table...")
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback_events'"
        ))
        if not result.scalar():
            await conn.execute(text("""
                CREATE TABLE feedback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id VARCHAR,
                    event_type VARCHAR(50) NOT NULL,
                    original_data JSON,
                    modified_data JSON,
                    context_item_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    FOREIGN KEY(context_item_id) REFERENCES context_items(id) ON DELETE SET NULL
                )
            """))
            await conn.execute(text(
                "CREATE INDEX ix_feedback_events_event_type ON feedback_events(event_type)"
            ))
            await conn.execute(text(
                "CREATE INDEX ix_feedback_events_created_at ON feedback_events(created_at)"
            ))
            print("  ✓ Created feedback_events table with indexes")
        else:
            print("  ⚠ feedback_events table already exists, skipping")

    print("✅ Migration completed successfully!")
    print("\n📋 Changes applied:")
    print("  - Added confidence_score, source_context_id, auto_created to tasks table")
    print("  - Created chat_messages table (AI Assistant conversation history)")
    print("  - Created feedback_events table (user feedback tracking)")
    print("\n🎉 Phase 2 AI Assistant is ready to use!")


async def rollback_migration():
    """Rollback the migration (remove Phase 2 changes)."""
    print("⚠️  Rolling back Phase 2 AI Assistant migration...")

    async with engine.begin() as conn:
        print("🗑️  Dropping Phase 2 tables...")
        await conn.execute(text("DROP TABLE IF EXISTS feedback_events"))
        await conn.execute(text("DROP TABLE IF EXISTS chat_messages"))

        # Note: SQLite doesn't support dropping columns easily
        # Users will need to manually recreate tasks table if they want to remove columns
        print("⚠️  Note: SQLite doesn't support dropping columns.")
        print("    New columns (confidence_score, source_context_id, auto_created) remain in tasks table.")
        print("    They will be ignored by the application.")

    print("✅ Rollback completed!")


async def check_migration_status():
    """Check if migration has been applied."""
    async with engine.begin() as conn:
        # Check if chat_messages table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages'"
        ))
        chat_messages_exists = result.scalar() is not None

        # Check if feedback_events table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback_events'"
        ))
        feedback_events_exists = result.scalar() is not None

        # Check if new task columns exist
        result = await conn.execute(text("PRAGMA table_info(tasks)"))
        existing_columns = {row[1] for row in result.fetchall()}
        has_confidence = "confidence_score" in existing_columns
        has_context_link = "source_context_id" in existing_columns
        has_auto_created = "auto_created" in existing_columns

        migration_complete = (
            chat_messages_exists and
            feedback_events_exists and
            has_confidence and
            has_context_link and
            has_auto_created
        )

        if migration_complete:
            print("✅ Phase 2 AI Assistant migration is complete")

            # Get stats
            result = await conn.execute(text("SELECT COUNT(*) FROM chat_messages"))
            message_count = result.scalar()

            result = await conn.execute(text("SELECT COUNT(*) FROM feedback_events"))
            feedback_count = result.scalar()

            print(f"📊 Current stats:")
            print(f"  - Chat messages: {message_count}")
            print(f"  - Feedback events: {feedback_count}")
        else:
            print("❌ Phase 2 AI Assistant migration not complete")
            print(f"  - chat_messages table: {'✅' if chat_messages_exists else '❌'}")
            print(f"  - feedback_events table: {'✅' if feedback_events_exists else '❌'}")
            print(f"  - tasks.confidence_score: {'✅' if has_confidence else '❌'}")
            print(f"  - tasks.source_context_id: {'✅' if has_context_link else '❌'}")
            print(f"  - tasks.auto_created: {'✅' if has_auto_created else '❌'}")
            print("Run: python migrations/002_add_phase2_assistant_tables.py migrate")

        return migration_complete


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrations/002_add_phase2_assistant_tables.py migrate   - Apply migration")
        print("  python migrations/002_add_phase2_assistant_tables.py rollback  - Rollback migration")
        print("  python migrations/002_add_phase2_assistant_tables.py status    - Check migration status")
        sys.exit(1)

    command = sys.argv[1]

    if command == "migrate":
        asyncio.run(run_migration())
    elif command == "rollback":
        asyncio.run(rollback_migration())
    elif command == "status":
        asyncio.run(check_migration_status())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
