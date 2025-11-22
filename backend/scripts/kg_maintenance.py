#!/usr/bin/env python3
"""
Knowledge Graph Maintenance Script - Phase 6

Automated scheduled task for KG lifecycle management.

Schedule with cron:
    # Weekly full cleanup (Sunday 3am)
    0 3 * * 0 cd /path/to/task-crate/backend && python scripts/kg_maintenance.py --full

    # Daily similarity index rebuild (every day 3am)
    0 3 * * * cd /path/to/task-crate/backend && python scripts/kg_maintenance.py --similarity-only

Usage:
    # Dry run (safe testing)
    python scripts/kg_maintenance.py --dry-run

    # Full cleanup (production)
    python scripts/kg_maintenance.py --full

    # Similarity index only
    python scripts/kg_maintenance.py --similarity-only

    # Health check only
    python scripts/kg_maintenance.py --health
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

from db.database import get_database_url
from services.kg_lifecycle_manager import get_kg_lifecycle_manager, KGLifecycleConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_full_cleanup(dry_run: bool = True):
    """Run full KG cleanup cycle."""
    logger.info("=" * 80)
    logger.info(f"Starting KG Maintenance (dry_run={dry_run})")
    logger.info("=" * 80)

    # Get database URL
    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=False)

    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # Get lifecycle manager
            manager = await get_kg_lifecycle_manager(session)

            # Run cleanup
            report = await manager.run_cleanup(dry_run=dry_run)

            # Print report
            logger.info("\n" + "=" * 80)
            logger.info("CLEANUP REPORT")
            logger.info("=" * 80)
            logger.info(f"Started:  {report.started_at}")
            logger.info(f"Completed: {report.completed_at}")
            logger.info(f"Duration: {(report.completed_at - report.started_at).total_seconds():.2f}s")
            logger.info("")
            logger.info("OPERATIONS:")
            logger.info(f"  Concepts archived:      {report.concepts_archived}")
            logger.info(f"  Conversations archived: {report.conversations_archived}")
            logger.info(f"  Relationships pruned:   {report.relationships_pruned}")
            logger.info(f"  Concepts merged:        {report.concepts_merged}")
            logger.info(f"  Concepts deleted:       {report.concepts_deleted}")
            logger.info(f"  Similarity rebuilt:     {report.similarity_entries_rebuilt}")
            logger.info("")
            logger.info("KG SIZE:")
            logger.info(f"  Nodes before: {report.nodes_before}")
            logger.info(f"  Nodes after:  {report.nodes_after}")
            logger.info(f"  Edges before: {report.edges_before}")
            logger.info(f"  Edges after:  {report.edges_after}")
            logger.info(f"  Reduction:    {report.nodes_before - report.nodes_after} nodes, {report.edges_before - report.edges_after} edges")

            if report.errors:
                logger.error("\nERRORS:")
                for error in report.errors:
                    logger.error(f"  - {error}")

            logger.info("=" * 80)

            if dry_run:
                logger.warning("DRY RUN - No changes committed")
            else:
                logger.info("✅ Cleanup completed successfully")

            return report

        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)
            raise

        finally:
            await engine.dispose()


async def rebuild_similarity_index_only():
    """Rebuild similarity index only (faster operation)."""
    logger.info("=" * 80)
    logger.info("Starting Similarity Index Rebuild")
    logger.info("=" * 80)

    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=False)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            manager = await get_kg_lifecycle_manager(session)
            count = await manager.rebuild_similarity_index()
            await session.commit()

            logger.info(f"✅ Rebuilt similarity index for {count} tasks")
            return count

        except Exception as e:
            logger.error(f"Similarity rebuild failed: {e}", exc_info=True)
            await session.rollback()
            raise

        finally:
            await engine.dispose()


async def print_health_report():
    """Print KG health metrics."""
    logger.info("=" * 80)
    logger.info("Knowledge Graph Health Report")
    logger.info("=" * 80)

    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=False)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            manager = await get_kg_lifecycle_manager(session)
            health = await manager.get_health_report()

            # Print formatted health report
            logger.info("\nKG SIZE:")
            logger.info(f"  Total nodes: {health['kg_size']['total_nodes']} / {health['kg_size']['target']}")
            logger.info(f"  Total edges: {health['kg_size']['total_edges']}")
            logger.info(f"  Status:      {health['kg_size']['health'].upper()}")

            logger.info("\nCONCEPTS:")
            logger.info(f"  Total:              {health['concepts']['total']}")
            logger.info(f"  Avg importance:     {health['concepts']['avg_importance']:.2f}")
            logger.info(f"  Established:        {health['concepts']['established_count']} ({health['concepts']['established_percentage']:.1f}%)")

            logger.info("\nRELATIONSHIPS:")
            logger.info(f"  Total:          {health['relationships']['total']}")
            logger.info(f"  Avg strength:   {health['relationships']['avg_strength']:.2f}")

            logger.info("\nTASK OUTCOMES:")
            logger.info(f"  Total:          {health['outcomes']['total']}")
            logger.info(f"  Completed:      {health['outcomes']['completed_count']}")
            logger.info(f"  Avg quality:    {health['outcomes']['avg_quality']:.2f}/5.0")

            logger.info("\n" + "=" * 80)

            # Recommendations
            if health['kg_size']['total_nodes'] > 4000:
                logger.warning("⚠️  KG approaching size limit - consider running cleanup")
            if health['concepts']['established_percentage'] < 30:
                logger.warning("⚠️  Low established concept percentage - most concepts are tentative")
            if health['relationships']['avg_strength'] < 0.5:
                logger.warning("⚠️  Low average relationship strength - consider pruning weak edges")

            return health

        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            raise

        finally:
            await engine.dispose()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Knowledge Graph Maintenance Script"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run cleanup without committing changes (safe testing)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full cleanup cycle (archive, prune, merge)"
    )
    parser.add_argument(
        "--similarity-only",
        action="store_true",
        help="Rebuild similarity index only (faster)"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Print health report only"
    )

    args = parser.parse_args()

    # Determine operation
    if args.health:
        asyncio.run(print_health_report())
    elif args.similarity_only:
        asyncio.run(rebuild_similarity_index_only())
    elif args.full:
        asyncio.run(run_full_cleanup(dry_run=False))
    else:
        # Default: dry run
        asyncio.run(run_full_cleanup(dry_run=True))


if __name__ == "__main__":
    main()
