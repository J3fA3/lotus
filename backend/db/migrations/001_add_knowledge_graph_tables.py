"""
Migration: Add Knowledge Graph Tables

This migration adds the following tables for cross-context knowledge persistence:
- knowledge_nodes: Canonical entities deduplicated across contexts
- knowledge_edges: Aggregated relationships with strength scores
- entity_knowledge_links: Links between raw entities and canonical nodes
- team_structure_evolution: Dynamically discovered team structures
- knowledge_graph_stats: Graph statistics and analytics

Run this migration if you have an existing database from before the knowledge graph feature.
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
from db.knowledge_graph_models import (
    KnowledgeNode,
    KnowledgeEdge,
    EntityKnowledgeLink,
    TeamStructureEvolution,
    KnowledgeGraphStats
)


async def run_migration():
    """Run the migration to add knowledge graph tables."""
    print("🔄 Starting Knowledge Graph tables migration...")

    async with engine.begin() as conn:
        # Create all knowledge graph tables
        print("📊 Creating knowledge_nodes table...")
        await conn.run_sync(KnowledgeNode.metadata.create_all, checkfirst=True)

        print("📊 Creating knowledge_edges table...")
        await conn.run_sync(KnowledgeEdge.metadata.create_all, checkfirst=True)

        print("📊 Creating entity_knowledge_links table...")
        await conn.run_sync(EntityKnowledgeLink.metadata.create_all, checkfirst=True)

        print("📊 Creating team_structure_evolution table...")
        await conn.run_sync(TeamStructureEvolution.metadata.create_all, checkfirst=True)

        print("📊 Creating knowledge_graph_stats table...")
        await conn.run_sync(KnowledgeGraphStats.metadata.create_all, checkfirst=True)

    print("✅ Migration completed successfully!")
    print("\n📋 New tables created:")
    print("  - knowledge_nodes (canonical entities)")
    print("  - knowledge_edges (aggregated relationships)")
    print("  - entity_knowledge_links (entity-to-node mapping)")
    print("  - team_structure_evolution (discovered org structure)")
    print("  - knowledge_graph_stats (graph analytics)")
    print("\n🎉 Knowledge graph is ready to use!")


async def rollback_migration():
    """Rollback the migration (drop knowledge graph tables)."""
    print("⚠️  Rolling back Knowledge Graph tables migration...")

    async with engine.begin() as conn:
        print("🗑️  Dropping knowledge graph tables...")
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_graph_stats"))
        await conn.execute(text("DROP TABLE IF EXISTS team_structure_evolution"))
        await conn.execute(text("DROP TABLE IF EXISTS entity_knowledge_links"))
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_edges"))
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_nodes"))

    print("✅ Rollback completed!")


async def check_migration_status():
    """Check if migration has been applied."""
    async with engine.begin() as conn:
        # Check if knowledge_nodes table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_nodes'"
        ))
        table_exists = result.scalar() is not None

        if table_exists:
            print("✅ Knowledge Graph tables are already present")

            # Get stats
            result = await conn.execute(text("SELECT COUNT(*) FROM knowledge_nodes"))
            node_count = result.scalar()

            result = await conn.execute(text("SELECT COUNT(*) FROM knowledge_edges"))
            edge_count = result.scalar()

            print(f"📊 Current graph stats:")
            print(f"  - Nodes: {node_count}")
            print(f"  - Edges: {edge_count}")
        else:
            print("❌ Knowledge Graph tables not found")
            print("Run: python migrations/001_add_knowledge_graph_tables.py migrate")

        return table_exists


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrations/001_add_knowledge_graph_tables.py migrate   - Apply migration")
        print("  python migrations/001_add_knowledge_graph_tables.py rollback  - Rollback migration")
        print("  python migrations/001_add_knowledge_graph_tables.py status    - Check migration status")
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
