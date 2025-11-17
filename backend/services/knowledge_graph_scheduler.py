"""
Knowledge Graph Background Task Scheduler

Runs periodic maintenance tasks:
- Confidence decay updates
- Stale relationship pruning
- Statistics computation
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from db.database import AsyncSessionLocal
from services.knowledge_graph_service import KnowledgeGraphService
from services.knowledge_graph_config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeGraphScheduler:
    """Background task scheduler for knowledge graph maintenance."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def apply_decay_task(self):
        """Periodic task to apply confidence decay to all relationships."""
        if not config.DECAY_ENABLED:
            logger.info("Decay is disabled, skipping decay task")
            return

        logger.info("Starting decay update task...")

        try:
            async with AsyncSessionLocal() as db:
                kg_service = KnowledgeGraphService(db)
                stats = await kg_service.apply_decay_to_all_edges()

                logger.info(
                    f"Decay task completed: "
                    f"{stats['edges_decayed']} edges decayed, "
                    f"avg decay: {stats['avg_decay_per_edge']:.4f}, "
                    f"{stats['edges_below_threshold']} below threshold"
                )

        except Exception as e:
            logger.error(f"Decay task failed: {str(e)}")

    async def prune_stale_task(self):
        """Periodic task to prune relationships below threshold."""
        if not config.DECAY_ENABLED:
            return

        logger.info("Starting stale relationship pruning task...")

        try:
            async with AsyncSessionLocal() as db:
                kg_service = KnowledgeGraphService(db)
                stats = await kg_service.prune_stale_relationships()

                logger.info(
                    f"Pruning task completed: "
                    f"{stats['edges_pruned']} edges pruned "
                    f"(threshold: {stats['threshold']:.2f})"
                )

        except Exception as e:
            logger.error(f"Pruning task failed: {str(e)}")

    async def compute_stats_task(self):
        """Periodic task to update graph statistics."""
        logger.info("Computing knowledge graph statistics...")

        try:
            async with AsyncSessionLocal() as db:
                kg_service = KnowledgeGraphService(db)
                stats = await kg_service.compute_graph_stats()

                logger.info(
                    f"Stats computed: "
                    f"{stats['total_nodes']} nodes, "
                    f"{stats['total_edges']} edges"
                )

        except Exception as e:
            logger.error(f"Stats computation failed: {str(e)}")

    def start(self):
        """Start the background scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting Knowledge Graph scheduler...")

        # Task 1: Apply decay periodically
        # Default: Every 24 hours
        self.scheduler.add_job(
            self.apply_decay_task,
            trigger=IntervalTrigger(hours=config.DECAY_UPDATE_INTERVAL_HOURS),
            id="apply_decay",
            name="Apply Confidence Decay",
            replace_existing=True,
            next_run_time=datetime.now()  # Run immediately on startup
        )

        # Task 2: Prune stale relationships
        # Default: Weekly on Sunday at 2 AM
        self.scheduler.add_job(
            self.prune_stale_task,
            trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
            id="prune_stale",
            name="Prune Stale Relationships",
            replace_existing=True
        )

        # Task 3: Compute statistics
        # Default: Daily at midnight
        self.scheduler.add_job(
            self.compute_stats_task,
            trigger=CronTrigger(hour=0, minute=0),
            id="compute_stats",
            name="Compute Graph Statistics",
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True

        logger.info(
            f"Scheduler started successfully. "
            f"Decay updates every {config.DECAY_UPDATE_INTERVAL_HOURS}h"
        )

    def stop(self):
        """Stop the background scheduler."""
        if not self.is_running:
            return

        logger.info("Stopping Knowledge Graph scheduler...")
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("Scheduler stopped")

    def get_jobs(self):
        """Get list of scheduled jobs."""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in self.scheduler.get_jobs()
        ]


# Singleton scheduler instance
scheduler = KnowledgeGraphScheduler()
