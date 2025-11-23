"""
Phase 6 Learning Background Task Scheduler

Runs periodic learning system tasks:
1. Daily Aggregation (2 AM) - Roll up raw signals into aggregates
2. Weekly Training (Sunday 3 AM) - Train learning models from aggregates
3. Weekly Correlation (Sunday 4 AM) - Analyze feature-outcome correlations

These jobs are critical for the learning loop to function.
"""

import os
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from db.database import AsyncSessionLocal
from services.implicit_learning_service import get_implicit_learning_service
from services.outcome_learning_service import get_outcome_learning_service

logger = logging.getLogger(__name__)


class Phase6LearningScheduler:
    """Background task scheduler for Phase 6 learning system."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def daily_aggregation_job(self):
        """Daily job to aggregate unprocessed signals into daily rollups."""
        logger.info("Starting daily signal aggregation job...")

        try:
            async with AsyncSessionLocal() as db:
                service = await get_implicit_learning_service(db)
                count = await service.aggregate_signals_daily()

                logger.info(f"Daily aggregation completed: {count} aggregates created")

        except Exception as e:
            logger.error(f"Daily aggregation job failed: {str(e)}", exc_info=True)

    async def weekly_training_job(self):
        """Weekly job to train learning models from aggregated signals."""
        logger.info("Starting weekly model training job...")

        try:
            async with AsyncSessionLocal() as db:
                service = await get_implicit_learning_service(db)
                count = await service.train_models_from_aggregates()

                logger.info(f"Weekly training completed: {count} models trained")

        except Exception as e:
            logger.error(f"Weekly training job failed: {str(e)}", exc_info=True)

    async def weekly_correlation_job(self):
        """Weekly job to analyze feature-outcome correlations."""
        logger.info("Starting weekly correlation analysis job...")

        try:
            async with AsyncSessionLocal() as db:
                service = await get_outcome_learning_service(db)
                count = await service.analyze_feature_correlations()

                logger.info(f"Weekly correlation analysis completed: {count} correlations analyzed")

        except Exception as e:
            logger.error(f"Weekly correlation job failed: {str(e)}", exc_info=True)

    def start(self):
        """Start the background scheduler."""
        if self.is_running:
            logger.warning("Phase 6 learning scheduler already running")
            return

        # Check if jobs are enabled
        enabled = os.getenv("ENABLE_PHASE6_LEARNING_JOBS", "true").lower() == "true"
        if not enabled:
            logger.info("Phase 6 learning jobs disabled via ENABLE_PHASE6_LEARNING_JOBS")
            return

        logger.info("Starting Phase 6 learning scheduler...")

        # Job 1: Daily aggregation at 2 AM
        self.scheduler.add_job(
            self.daily_aggregation_job,
            trigger=CronTrigger(hour=2, minute=0),
            id="phase6_daily_aggregation",
            name="Daily Signal Aggregation",
            replace_existing=True
        )
        logger.info("Scheduled daily aggregation at 2:00 AM")

        # Job 2: Weekly training on Sunday at 3 AM
        self.scheduler.add_job(
            self.weekly_training_job,
            trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
            id="phase6_weekly_training",
            name="Weekly Model Training",
            replace_existing=True
        )
        logger.info("Scheduled weekly training on Sunday at 3:00 AM")

        # Job 3: Weekly correlation on Sunday at 4 AM
        self.scheduler.add_job(
            self.weekly_correlation_job,
            trigger=CronTrigger(day_of_week="sun", hour=4, minute=0),
            id="phase6_weekly_correlation",
            name="Weekly Correlation Analysis",
            replace_existing=True
        )
        logger.info("Scheduled weekly correlation analysis on Sunday at 4:00 AM")

        self.scheduler.start()
        self.is_running = True

        logger.info("✅ Phase 6 learning scheduler started successfully")

    def stop(self):
        """Stop the background scheduler."""
        if not self.is_running:
            return

        logger.info("Stopping Phase 6 learning scheduler...")
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("Phase 6 learning scheduler stopped")

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


# Singleton instance
_phase6_learning_scheduler = None


def get_phase6_learning_scheduler() -> Phase6LearningScheduler:
    """Get singleton Phase 6 learning scheduler instance.

    Returns:
        Phase6LearningScheduler instance
    """
    global _phase6_learning_scheduler
    if _phase6_learning_scheduler is None:
        _phase6_learning_scheduler = Phase6LearningScheduler()
    return _phase6_learning_scheduler

