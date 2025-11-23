"""
Database Migration: Phase 6 - Cognitive Nexus Knowledge Graph Enhancements

Adds tables for:
1. ConceptNodes - Domain-specific concepts with importance scoring
2. ConversationThreads - Conversation tracking with decisions and questions
3. TaskOutcomes - Task completion outcomes with lessons learned
4. ConceptRelationships - Relationships between concepts
5. TaskSimilarityIndex - Pre-computed task similarity for fast lookups
6. ConceptTaskLinks - Links between concepts and tasks

These extensions transform the KG from simple entity tracking to a rich
contextual memory system that learns from outcomes and builds strategic understanding.

Run with:
    python -m db.migrations.006_add_phase6_kg_tables

Rollback with:
    python -m db.migrations.006_add_phase6_kg_tables rollback
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
    """Run Phase 6 database migration."""
    print("🚀 Starting Phase 6 (Cognitive Nexus KG Enhancements) database migration...")

    # Get database URL
    db_url = get_database_url()
    print(f"Database: {db_url}")

    # Create async engine
    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        # Create Phase 6 tables
        print("\n📦 Creating Phase 6 knowledge graph tables...")

        # ConceptNodes table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS concept_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL UNIQUE,
                definition TEXT,
                importance_score REAL DEFAULT 0.0 NOT NULL,
                confidence_tier VARCHAR(50) DEFAULT 'TENTATIVE' NOT NULL,
                first_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                last_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                mention_count_30d INTEGER DEFAULT 1 NOT NULL,
                mention_count_total INTEGER DEFAULT 1 NOT NULL,
                related_projects JSON,
                related_markets JSON,
                related_people JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archived_at TIMESTAMP
            )
        """))
        print("✓ Created concept_nodes table")

        # ConversationThreads table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversation_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic VARCHAR(500) NOT NULL,
                participants JSON NOT NULL,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                message_count INTEGER DEFAULT 1 NOT NULL,
                key_decisions JSON NOT NULL,
                unresolved_questions JSON NOT NULL,
                related_projects JSON,
                related_tasks JSON,
                importance_score REAL DEFAULT 0.5 NOT NULL,
                is_active BOOLEAN DEFAULT 1 NOT NULL,
                is_archived BOOLEAN DEFAULT 0 NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archived_at TIMESTAMP
            )
        """))
        print("✓ Created conversation_threads table")

        # TaskOutcomes table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_outcomes (
                task_id VARCHAR PRIMARY KEY,
                outcome VARCHAR(50) NOT NULL,
                completion_quality REAL,
                estimated_effort_hours REAL,
                actual_effort_hours REAL,
                effort_variance REAL,
                blockers JSON NOT NULL,
                lessons_learned TEXT,
                task_title VARCHAR(500),
                task_project VARCHAR(255),
                task_market VARCHAR(255),
                task_assignee VARCHAR(255),
                follow_up_task_count INTEGER DEFAULT 0 NOT NULL,
                user_satisfaction INTEGER,
                user_notes TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """))
        print("✓ Created task_outcomes table")

        # ConceptRelationships table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS concept_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept_id INTEGER NOT NULL,
                related_to_id INTEGER NOT NULL,
                relationship_type VARCHAR(100) NOT NULL,
                strength REAL DEFAULT 1.0 NOT NULL,
                confidence REAL DEFAULT 1.0 NOT NULL,
                reason TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                last_reinforced TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (concept_id) REFERENCES concept_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (related_to_id) REFERENCES concept_nodes(id) ON DELETE CASCADE
            )
        """))
        print("✓ Created concept_relationships table")

        # TaskSimilarityIndex table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_similarity_index (
                task_id VARCHAR PRIMARY KEY,
                similar_task_ids JSON NOT NULL,
                similar_task_titles JSON NOT NULL,
                similarity_scores JSON NOT NULL,
                similarity_explanations JSON NOT NULL,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                is_stale BOOLEAN DEFAULT 0 NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """))
        print("✓ Created task_similarity_index table")

        # ConceptTaskLinks table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS concept_task_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept_id INTEGER NOT NULL,
                task_id VARCHAR NOT NULL,
                strength REAL DEFAULT 1.0 NOT NULL,
                mention_location VARCHAR(50),
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (concept_id) REFERENCES concept_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """))
        print("✓ Created concept_task_links table")

        # Create indexes for performance
        print("\n🔍 Creating performance indexes...")

        # ConceptNodes indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_concept_name
            ON concept_nodes(name)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_concept_importance
            ON concept_nodes(importance_score DESC)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_concept_tier
            ON concept_nodes(confidence_tier)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_concept_last_mentioned
            ON concept_nodes(last_mentioned DESC)
        """))

        print("✓ Created concept_nodes indexes")

        # ConversationThreads indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversation_topic
            ON conversation_threads(topic)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversation_last_updated
            ON conversation_threads(last_updated DESC)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversation_active
            ON conversation_threads(is_active)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conversation_importance
            ON conversation_threads(importance_score DESC)
        """))

        print("✓ Created conversation_threads indexes")

        # TaskOutcomes indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_outcome_type
            ON task_outcomes(outcome)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_outcome_quality
            ON task_outcomes(completion_quality DESC)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_outcome_project
            ON task_outcomes(task_project)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_outcome_market
            ON task_outcomes(task_market)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_outcome_completed
            ON task_outcomes(completed_at DESC)
        """))

        print("✓ Created task_outcomes indexes")

        # ConceptRelationships indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_concept_relationship
            ON concept_relationships(concept_id, related_to_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationship_type
            ON concept_relationships(relationship_type)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationship_strength
            ON concept_relationships(strength DESC)
        """))

        print("✓ Created concept_relationships indexes")

        # TaskSimilarityIndex indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_similarity_computed
            ON task_similarity_index(computed_at DESC)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_similarity_stale
            ON task_similarity_index(is_stale)
        """))

        print("✓ Created task_similarity_index indexes")

        # ConceptTaskLinks indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_concept_task_concept
            ON concept_task_links(concept_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_concept_task_task
            ON concept_task_links(task_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_concept_task_both
            ON concept_task_links(concept_id, task_id)
        """))

        print("✓ Created concept_task_links indexes")

    await engine.dispose()

    print("\n✅ Phase 6 migration completed successfully!")
    print("\nNew tables created:")
    print("  - concept_nodes (Domain-specific concepts with importance scoring)")
    print("  - conversation_threads (Conversation tracking with decisions and questions)")
    print("  - task_outcomes (Task completion outcomes with lessons learned)")
    print("  - concept_relationships (Relationships between concepts)")
    print("  - task_similarity_index (Pre-computed task similarity)")
    print("  - concept_task_links (Links between concepts and tasks)")
    print("\nIndexes created for optimal query performance (<500ms target).")
    print("\nPhase 6 Cognitive Nexus KG enhancements ready! 🧠")


async def rollback_migration():
    """Rollback Phase 6 migration (drop tables)."""
    print("⚠️  Rolling back Phase 6 database migration...")

    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        print("\n🗑️  Dropping Phase 6 tables...")

        # Drop in reverse order (respecting foreign keys)
        await conn.execute(text("DROP TABLE IF EXISTS concept_task_links"))
        print("✓ Dropped concept_task_links table")

        await conn.execute(text("DROP TABLE IF EXISTS task_similarity_index"))
        print("✓ Dropped task_similarity_index table")

        await conn.execute(text("DROP TABLE IF EXISTS concept_relationships"))
        print("✓ Dropped concept_relationships table")

        await conn.execute(text("DROP TABLE IF EXISTS task_outcomes"))
        print("✓ Dropped task_outcomes table")

        await conn.execute(text("DROP TABLE IF EXISTS conversation_threads"))
        print("✓ Dropped conversation_threads table")

        await conn.execute(text("DROP TABLE IF EXISTS concept_nodes"))
        print("✓ Dropped concept_nodes table")

    await engine.dispose()

    print("\n✅ Phase 6 rollback completed successfully!")


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback_migration())
    else:
        asyncio.run(run_migration())


if __name__ == "__main__":
    main()
