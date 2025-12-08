import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from src.services.sheets import get_month_summary, get_month_transactions_markdown, create_backup, get_enriched_analytics
from src.services.ai_analyzer import generate_monthly_report
from src.utils.formatters import month_name

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

_report_callback = None


def set_report_callback(callback):
    """Устанавливает callback для отправки отчётов."""
    global _report_callback
    _report_callback = callback


async def generate_and_send_monthly_report():
    """Генерирует и отправляет ежемесячный отчёт."""
    if not _report_callback:
        logger.warning("Report callback not set")
        return

    now = datetime.now()
    year = now.year
    month = now.month

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    try:
        summary = get_month_summary(year, month)
        previous_summary = get_month_summary(prev_year, prev_month)

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        prev_start = datetime(prev_year, prev_month, 1)
        prev_end = start_date

        enriched_data = get_enriched_analytics(start_date, end_date, prev_start, prev_end)

        report = await generate_monthly_report(
            summary=summary,
            previous_summary=previous_summary,
            transactions_markdown="",
            month_name=month_name(month),
            year=year,
            enriched_data=enriched_data,
        )

        await _report_callback(report)
        logger.info(f"Monthly report for {month_name(month)} {year} sent")

    except Exception as e:
        logger.error(f"Failed to generate monthly report: {e}")


async def create_weekly_backup():
    """Создаёт еженедельный бэкап."""
    try:
        backup_name = create_backup()
        logger.info(f"Weekly backup created: {backup_name}")
    except Exception as e:
        logger.error(f"Failed to create weekly backup: {e}")


def start_scheduler():
    """Запускает планировщик задач."""
    moscow_tz = pytz.timezone("Europe/Moscow")

    scheduler.add_job(
        generate_and_send_monthly_report,
        CronTrigger(day="last", hour=20, minute=0, timezone=moscow_tz),
        id="monthly_report",
        replace_existing=True,
    )

    scheduler.add_job(
        create_weekly_backup,
        CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=moscow_tz),
        id="weekly_backup",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with monthly reports and weekly backups")


def stop_scheduler():
    """Останавливает планировщик."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
