# =============================================================================
# app/services/deadline_scheduler.py
#
# APScheduler job that runs once daily and fires deadline notifications
# for any deadline due within 30 days that hasn't been notified yet.
#
# Register in main.py:
#
#   from app.services.deadline_scheduler import start_deadline_scheduler
#
#   @app.on_event("startup")
#   async def on_startup():
#       start_deadline_scheduler()
#
# =============================================================================

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.database import AsyncSessionLocal  # your async session factory
from app.models.visamodels import Deadline
from app.services.employee.notification_service import fire_deadline_approaching

logger = logging.getLogger(__name__)

# Notify when deadline is within this many days
DEADLINE_NOTIFY_DAYS = 30


async def _check_deadlines() -> None:
    """
    Runs daily. Finds all active deadlines due within DEADLINE_NOTIFY_DAYS
    that haven't had a reminder sent yet, then fires notifications.
    """
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=DEADLINE_NOTIFY_DAYS)

    logger.info("Deadline scheduler running at %s", now.isoformat())

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Deadline).where(
                    Deadline.is_completed == False,   # noqa: E712
                    Deadline.is_dismissed == False,   # noqa: E712
                    Deadline.reminder_sent == False,  # noqa: E712
                    Deadline.due_date <= cutoff,
                    Deadline.due_date >= now,         # don't notify past-due
                )
            )
            deadlines = result.scalars().all()

            logger.info("Found %d deadline(s) to notify", len(deadlines))

            for deadline in deadlines:
                days_remaining = (deadline.due_date - now).days
                await fire_deadline_approaching(
                    db,
                    deadline,
                    days_remaining=max(days_remaining, 0),
                )

            await db.commit()

        except Exception:
            await db.rollback()
            logger.exception("Deadline scheduler job failed")


def start_deadline_scheduler() -> AsyncIOScheduler:
    """
    Creates and starts the AsyncIO scheduler.
    Runs _check_deadlines every day at 08:00 UTC.
    Returns the scheduler so it can be shut down on app teardown if needed.
    """
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _check_deadlines,
        trigger="cron",
        hour=8,
        minute=0,
        id="deadline_notifications",
        replace_existing=True,
        misfire_grace_time=3600,  # If server was down, run within 1 hour of wake
    )
    scheduler.start()
    logger.info("Deadline notification scheduler started (daily at 08:00 UTC)")
    return scheduler