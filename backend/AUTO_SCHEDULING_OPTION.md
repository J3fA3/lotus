"""
Add this to backend/services/calendar_scheduler.py
to enable automatic scheduling suggestions
"""

# ADD THIS METHOD to CalendarScheduler class:

async def _update_scheduling_suggestions(self):
    """Background job: Update scheduling suggestions hourly."""
    try:
        logger.info("Updating scheduling suggestions...")

        from db.database import AsyncSessionLocal
        from agents.scheduling_agent import get_scheduling_agent
        from sqlalchemy import select
        from db.models import Task

        async with AsyncSessionLocal() as db:
            # Get all active tasks
            query = select(Task).where(
                Task.status.in_(['todo', 'doing'])
            )
            result = await db.execute(query)
            tasks = result.scalars().all()

            if not tasks:
                logger.info("No active tasks to schedule")
                return

            # Generate suggestions for default user
            user_id = 1
            agent = get_scheduling_agent()

            suggestions = await agent.schedule_tasks(
                tasks=list(tasks),
                user_id=user_id,
                db=db,
                days_ahead=7,
                max_suggestions=10
            )

            logger.info(f"Updated {len(suggestions)} scheduling suggestions")

    except Exception as e:
        logger.error(f"Scheduling suggestions update failed: {e}")


# THEN UPDATE the start() method to enable this:

def start(self):
    """Start background scheduler with calendar sync jobs."""
    if self.is_running:
        logger.warning("Calendar scheduler already running")
        return

    # Job 1: Sync calendar every 15 minutes (EXISTING)
    self.scheduler.add_job(
        self._sync_all_calendars,
        trigger=IntervalTrigger(minutes=self.sync_interval_minutes),
        id='calendar_sync',
        name='Sync Google Calendar',
        replace_existing=True
    )

    # Job 2: Meeting prep notifications daily at 8am (EXISTING)
    if os.getenv("ENABLE_MEETING_PREP_NOTIFICATIONS", "true").lower() == "true":
        self.scheduler.add_job(
            self._send_meeting_prep_notifications,
            trigger=CronTrigger(hour=8, minute=0),
            id='meeting_prep_notifications',
            name='Send meeting prep notifications',
            replace_existing=True
        )

    # Job 3: Update scheduling suggestions every hour (NEW!)
    if os.getenv("ENABLE_AUTO_SCHEDULING", "false").lower() == "true":
        self.scheduler.add_job(
            self._update_scheduling_suggestions,
            trigger=IntervalTrigger(hours=1),
            id='auto_scheduling',
            name='Auto-update scheduling suggestions',
            replace_existing=True
        )
        logger.info("Scheduled automatic scheduling suggestions (hourly)")

    self.scheduler.start()
    self.is_running = True
    logger.info("✅ Calendar scheduler started")
