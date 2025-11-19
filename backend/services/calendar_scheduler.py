"""
Calendar Background Scheduler - Phase 4

Runs background tasks for calendar integration:
1. Auto-sync calendar every 15 minutes
2. Generate daily meeting prep notifications (8am)
3. Update scheduling suggestions

Uses APScheduler for reliable background task execution.
"""

import os
import logging
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class CalendarScheduler:
    """Background scheduler for calendar sync and notifications."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.sync_interval_minutes = int(os.getenv("CALENDAR_SYNC_INTERVAL_MINUTES", "15"))
        self.is_running = False

    def start(self):
        """Start background scheduler with calendar sync jobs."""
        if self.is_running:
            logger.warning("Calendar scheduler already running")
            return

        # Job 1: Sync calendar every 15 minutes
        self.scheduler.add_job(
            self._sync_all_calendars,
            trigger=IntervalTrigger(minutes=self.sync_interval_minutes),
            id='calendar_sync',
            name='Sync Google Calendar',
            replace_existing=True
        )
        logger.info(f"Scheduled calendar sync every {self.sync_interval_minutes} minutes")

        # Job 2: Generate meeting prep notifications daily at 8am
        if os.getenv("ENABLE_MEETING_PREP_NOTIFICATIONS", "true").lower() == "true":
            self.scheduler.add_job(
                self._send_meeting_prep_notifications,
                trigger=CronTrigger(hour=8, minute=0),  # 8am every day
                id='meeting_prep_notifications',
                name='Send meeting prep notifications',
                replace_existing=True
            )
            logger.info("Scheduled meeting prep notifications at 8am daily")

        # Job 3: Update scheduling suggestions every hour
        self.scheduler.add_job(
            self._update_scheduling_suggestions,
            trigger=IntervalTrigger(hours=1),
            id='update_scheduling_suggestions',
            name='Update scheduling suggestions',
            replace_existing=True
        )
        logger.info("Scheduled scheduling suggestions update every hour")

        # Start scheduler
        self.scheduler.start()
        self.is_running = True
        logger.info("✅ Calendar scheduler started")

    def stop(self):
        """Stop background scheduler."""
        if not self.is_running:
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Calendar scheduler stopped")

    async def _sync_all_calendars(self):
        """Background job: Sync calendars for all authorized users."""
        try:
            logger.info("Running background calendar sync...")

            # Import here to avoid circular imports
            from db.database import AsyncSessionLocal
            from services.calendar_sync import get_calendar_sync_service
            from services.google_oauth import get_oauth_service

            async with AsyncSessionLocal() as db:
                oauth_service = get_oauth_service()
                calendar_service = get_calendar_sync_service()

                # For now, sync for default user (user_id=1)
                # TODO Phase 5: Get all users with calendar authorization
                user_id = 1

                # Check if user is authorized
                is_authorized = await oauth_service.is_authorized(user_id, db)
                if not is_authorized:
                    logger.info(f"User {user_id} not authorized, skipping sync")
                    return

                # Sync calendar
                events = await calendar_service.sync_calendar(user_id, db)
                logger.info(f"Background sync completed: {len(events)} events for user {user_id}")

        except Exception as e:
            logger.error(f"Background calendar sync failed: {e}")

    async def _send_meeting_prep_notifications(self):
        """Background job: Send daily meeting prep notifications at 8am."""
        try:
            logger.info("Generating meeting prep notifications...")

            # Import here to avoid circular imports
            from db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                # TODO: Implement with MeetingPrepAssistant
                # - Check today's meetings
                # - Find incomplete related tasks
                # - Send notifications

                logger.info("Meeting prep notifications sent (placeholder)")

        except Exception as e:
            logger.error(f"Meeting prep notifications failed: {e}")

    async def _update_scheduling_suggestions(self):
        """Background job: Update scheduling suggestions hourly."""
        try:
            logger.info("Updating scheduling suggestions...")

            # Import here to avoid circular imports
            from db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                # TODO: Implement with SchedulingAgent
                # - Get active tasks
                # - Get calendar events
                # - Generate new scheduling suggestions

                logger.info("Scheduling suggestions updated (placeholder)")

        except Exception as e:
            logger.error(f"Scheduling suggestions update failed: {e}")


# Singleton instance
_calendar_scheduler = None


def get_calendar_scheduler() -> CalendarScheduler:
    """Get singleton calendar scheduler instance.

    Returns:
        CalendarScheduler instance
    """
    global _calendar_scheduler
    if _calendar_scheduler is None:
        _calendar_scheduler = CalendarScheduler()
    return _calendar_scheduler
