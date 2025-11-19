"""
Database Migration: Phase 5 - Gmail Integration

Adds tables for:
1. EmailAccounts - Gmail account authentication
2. EmailMessages - Processed email messages
3. EmailThreads - Email thread consolidation
4. EmailTaskLinks - Links between emails and tasks

Also adds indexes for optimal query performance.

Run with:
    python -m db.migrations.004_add_phase5_email_tables
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from db.database import get_database_url


async def run_migration():
    """Run Phase 5 database migration."""
    print("🚀 Starting Phase 5 (Gmail Integration) database migration...")

    # Get database URL
    db_url = get_database_url()
    print(f"Database: {db_url}")

    # Create async engine
    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        # Create Phase 5 tables
        print("\n📦 Creating Phase 5 email tables...")

        # EmailAccounts table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                email_address VARCHAR(255) NOT NULL UNIQUE,
                provider VARCHAR(50) NOT NULL DEFAULT 'gmail',
                auth_token_encrypted TEXT,
                last_sync_at TIMESTAMP,
                sync_enabled BOOLEAN DEFAULT 1,
                sync_interval_minutes INTEGER DEFAULT 20,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("✓ Created email_accounts table")

        # EmailMessages table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail_message_id VARCHAR(255) NOT NULL UNIQUE,
                thread_id VARCHAR(255) NOT NULL,
                account_id INTEGER NOT NULL,
                subject TEXT,
                sender VARCHAR(500),
                sender_name VARCHAR(255),
                sender_email VARCHAR(255),
                recipient_to TEXT,
                recipient_cc TEXT,
                recipient_bcc TEXT,
                body_text TEXT,
                body_html TEXT,
                snippet TEXT,
                labels JSON,
                has_attachments BOOLEAN DEFAULT 0,
                links JSON,
                action_phrases JSON,
                is_meeting_invite BOOLEAN DEFAULT 0,
                received_at TIMESTAMP,
                processed_at TIMESTAMP,
                classification VARCHAR(50),
                classification_confidence REAL,
                task_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES email_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
            )
        """))
        print("✓ Created email_messages table")

        # EmailThreads table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail_thread_id VARCHAR(255) NOT NULL UNIQUE,
                account_id INTEGER NOT NULL,
                subject TEXT,
                participant_emails JSON,
                message_count INTEGER DEFAULT 1,
                first_message_at TIMESTAMP,
                last_message_at TIMESTAMP,
                is_consolidated BOOLEAN DEFAULT 0,
                consolidated_task_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES email_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (consolidated_task_id) REFERENCES tasks(id) ON DELETE SET NULL
            )
        """))
        print("✓ Created email_threads table")

        # EmailTaskLinks table (many-to-many relationship)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_task_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER NOT NULL,
                task_id VARCHAR NOT NULL,
                relationship_type VARCHAR(50) DEFAULT 'created_from',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES email_messages(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                UNIQUE(email_id, task_id)
            )
        """))
        print("✓ Created email_task_links table")

        # Create indexes for performance
        print("\n🔍 Creating performance indexes...")

        # Email messages - critical for queries
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_messages_gmail_id
            ON email_messages(gmail_message_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_messages_thread_id
            ON email_messages(thread_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_messages_processed_at
            ON email_messages(processed_at)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_messages_classification
            ON email_messages(classification)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_messages_task_id
            ON email_messages(task_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_messages_received_at
            ON email_messages(received_at DESC)
        """))

        # Email threads
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_threads_gmail_thread_id
            ON email_threads(gmail_thread_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_threads_consolidated_task_id
            ON email_threads(consolidated_task_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_threads_last_message_at
            ON email_threads(last_message_at DESC)
        """))

        # Email task links
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_task_links_email_id
            ON email_task_links(email_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_task_links_task_id
            ON email_task_links(task_id)
        """))

        # Email accounts
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_accounts_user_id
            ON email_accounts(user_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_email_accounts_email_address
            ON email_accounts(email_address)
        """))

        print("✓ Created all Phase 5 indexes")

    await engine.dispose()

    print("\n✅ Phase 5 migration completed successfully!")
    print("\nNew tables created:")
    print("  - email_accounts (Gmail account management)")
    print("  - email_messages (Processed emails with classification)")
    print("  - email_threads (Thread consolidation)")
    print("  - email_task_links (Email-Task relationships)")
    print("\nIndexes created for optimal query performance.")


async def rollback_migration():
    """Rollback Phase 5 migration (drop tables)."""
    print("⚠️  Rolling back Phase 5 database migration...")

    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        print("\n🗑️  Dropping Phase 5 tables...")

        # Drop in reverse order (respecting foreign keys)
        await conn.execute(text("DROP TABLE IF EXISTS email_task_links"))
        print("✓ Dropped email_task_links table")

        await conn.execute(text("DROP TABLE IF EXISTS email_threads"))
        print("✓ Dropped email_threads table")

        await conn.execute(text("DROP TABLE IF EXISTS email_messages"))
        print("✓ Dropped email_messages table")

        await conn.execute(text("DROP TABLE IF EXISTS email_accounts"))
        print("✓ Dropped email_accounts table")

    await engine.dispose()

    print("\n✅ Phase 5 rollback completed successfully!")


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback_migration())
    else:
        asyncio.run(run_migration())


if __name__ == "__main__":
    main()
