"""
Database Migration: Phase 3 - User Profiles & Task Enrichment

Adds tables for:
1. UserProfile - Store user context (name, projects, markets, colleagues)
2. TaskEnrichment - Track task enrichments (auto-updates)

Also adds database indexes for performance optimization.

Run with:
    python -m db.migrations.003_add_phase3_tables
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from db.database import get_database_url
from db.models import Base, UserProfile, TaskEnrichment


async def run_migration():
    """Run Phase 3 database migration."""
    print("🚀 Starting Phase 3 database migration...")

    # Get database URL
    db_url = get_database_url()
    print(f"Database: {db_url}")

    # Create async engine
    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        # Create Phase 3 tables
        print("\n📦 Creating Phase 3 tables...")

        # UserProfile table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                name VARCHAR(255) NOT NULL,
                aliases JSON,
                role VARCHAR(255),
                company VARCHAR(255),
                projects JSON,
                markets JSON,
                colleagues JSON,
                preferences JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("✓ Created user_profiles table")

        # TaskEnrichment table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_enrichments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id VARCHAR NOT NULL,
                context_item_id INTEGER,
                enrichment_type VARCHAR(50) NOT NULL,
                before_value JSON,
                after_value JSON,
                reasoning TEXT,
                confidence_score REAL,
                auto_applied BOOLEAN DEFAULT 0,
                user_approved BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (context_item_id) REFERENCES context_items(id) ON DELETE SET NULL
            )
        """))
        print("✓ Created task_enrichments table")

        # Create indexes for performance
        print("\n🔍 Creating performance indexes...")

        # User profiles
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id
            ON user_profiles(user_id)
        """))

        # Tasks - critical for fast queries
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tasks_created_at
            ON tasks(created_at DESC)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tasks_assignee
            ON tasks(assignee)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON tasks(status)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tasks_value_stream
            ON tasks(value_stream)
        """))

        # Entities - for knowledge graph queries
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_entities_name
            ON entities(name)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_entities_type
            ON entities(type)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_entities_created_at
            ON entities(created_at DESC)
        """))

        # Relationships
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationships_subject
            ON relationships(subject_entity_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationships_object
            ON relationships(object_entity_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationships_predicate
            ON relationships(predicate)
        """))

        # Context items
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_context_items_source_type
            ON context_items(source_type)
        """))

        # Task enrichments
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_task_enrichments_task_id
            ON task_enrichments(task_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_task_enrichments_created_at
            ON task_enrichments(created_at DESC)
        """))

        print("✓ Created all performance indexes")

        # Seed default user profile (Jef)
        print("\n👤 Seeding default user profile...")

        # Check if profile exists
        result = await conn.execute(text("SELECT COUNT(*) FROM user_profiles WHERE user_id = 1"))
        count = result.scalar()

        if count == 0:
            await conn.execute(text("""
                INSERT INTO user_profiles (
                    user_id, name, aliases, role, company, projects, markets, colleagues
                ) VALUES (
                    1,
                    'Jef Adriaenssens',
                    '["Jeff", "Jef", "jef", "JA"]',
                    'Product Manager',
                    'JustEat Takeaway',
                    '["CRESCO", "RF16", "Just Deals"]',
                    '["Spain", "UK", "Netherlands"]',
                    '{"Andy": "Andy Maclean", "Alberto": "Alberto Moraleda Fernandez - Spain market", "Maran": "Maran Vleems", "Sarah": "Sarah (Last Name Unknown)"}'
                )
            """))
            print("✓ Seeded default user profile for Jef Adriaenssens")
        else:
            print("✓ User profile already exists")

    await engine.dispose()

    print("\n✅ Phase 3 migration completed successfully!")
    print("\nNext steps:")
    print("1. Restart the backend server")
    print("2. Test Gemini integration (set GOOGLE_AI_API_KEY in .env)")
    print("3. Try sample messages to verify relevance filtering")


async def rollback_migration():
    """Rollback Phase 3 migration (for testing)."""
    print("⚠️  Rolling back Phase 3 migration...")

    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS task_enrichments"))
        await conn.execute(text("DROP TABLE IF EXISTS user_profiles"))
        print("✓ Dropped Phase 3 tables")

        # Drop indexes (they'll be dropped with tables, but explicit for clarity)
        indexes = [
            "idx_user_profiles_user_id",
            "idx_tasks_created_at",
            "idx_tasks_assignee",
            "idx_tasks_status",
            "idx_tasks_value_stream",
            "idx_entities_name",
            "idx_entities_type",
            "idx_entities_created_at",
            "idx_relationships_subject",
            "idx_relationships_object",
            "idx_relationships_predicate",
            "idx_context_items_source_type",
            "idx_task_enrichments_task_id",
            "idx_task_enrichments_created_at"
        ]

        for idx in indexes:
            try:
                await conn.execute(text(f"DROP INDEX IF EXISTS {idx}"))
            except:
                pass  # Index might not exist

        print("✓ Dropped indexes")

    await engine.dispose()
    print("✅ Rollback completed")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback_migration())
    else:
        asyncio.run(run_migration())
