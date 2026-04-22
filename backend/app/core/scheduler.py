"""
APScheduler - runs background jobs like daily alert summaries
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from app.core.config import settings


scheduler = AsyncIOScheduler(timezone="UTC")


async def send_daily_alert_summary():
    """Job: Generate and send daily alert summary via WhatsApp"""
    logger.info("Running daily alert summary job...")
    try:
        from app.db.database import AsyncSessionLocal
        from app.agents.employer_agent import EmployerAgent
        from app.services.whatsapp_service import WhatsAppService

        async with AsyncSessionLocal() as db:
            agent = EmployerAgent(db)
            summary = await agent.generate_daily_alert_summary(hours=24)
            wa = WhatsAppService()
            sent = await wa.send_message(summary)
            if sent:
                logger.info("Daily alert summary sent via WhatsApp")
            else:
                logger.warning("Daily alert summary could not be sent (WhatsApp not configured?)")
    except Exception as e:
        logger.error(f"Daily alert summary job failed: {e}")


def start_scheduler():
    # Parse cron from settings e.g. "0 18 * * *"
    parts = settings.DAILY_ALERT_CRON.strip().split()
    if len(parts) == 5:
        minute, hour, day, month, day_of_week = parts
    else:
        minute, hour, day, month, day_of_week = "0", "18", "*", "*", "*"

    scheduler.add_job(
        send_daily_alert_summary,
        CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        ),
        id="daily_alert_summary",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started. Daily summary cron: {settings.DAILY_ALERT_CRON}")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
