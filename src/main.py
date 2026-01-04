import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError, TimedOut, NetworkError

from src.config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
from src.bot.handlers.menu import start_command
from src.bot.handlers.text import text_message_handler
from src.bot.handlers.voice import voice_message_handler
from src.bot.handlers.admin import health_command, stats_command
from src.bot.handlers.callbacks import (
    menu_callback,
    period_callback,
    transactions_callback,
    backup_callback,
    transaction_callback,
    edit_callback,
    category_callback,
    health_callback,
)

from src.utils.logging_config import setup_logging
from src.services.health_check import get_health_checker
from src.services.resource_monitor import get_resource_monitor

setup_logging()
logger = logging.getLogger(__name__)

_application = None


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    get_health_checker().record_request(success=False)

    if isinstance(context.error, TimedOut):
        logger.warning("Telegram API timeout, continuing...")
        return

    if isinstance(context.error, NetworkError):
        logger.warning(f"Network error: {context.error}, continuing...")
        return

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Произошла ошибка при обработке запроса. Попробуй ещё раз."
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


async def send_report_to_users(report: str):
    """Отправляет отчёт всем разрешённым пользователям."""
    if not _application or not ALLOWED_USER_IDS:
        return

    for user_id in ALLOWED_USER_IDS:
        try:
            await _application.bot.send_message(chat_id=user_id, text=report)
            logger.info(f"Report sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send report to {user_id}: {e}")


async def post_init(app: Application) -> None:
    logger.info("Initializing bot resources...")

    resource_monitor = get_resource_monitor()
    await resource_monitor.start_monitoring()
    logger.info("Resource monitoring started")

    try:
        from src.services.sheets_async import async_init_spreadsheet
        await async_init_spreadsheet()
        logger.info("Spreadsheet structure initialized")
    except Exception as e:
        logger.warning(f"Could not initialize spreadsheet: {e}")

    health_status = get_health_checker().get_health_status()
    logger.info(f"Bot initialized, ready to serve - Status: {health_status['status']}")


async def post_shutdown(app: Application) -> None:
    logger.info("Cleaning up resources...")
    try:
        resource_monitor = get_resource_monitor()
        await resource_monitor.stop_monitoring()

        from src.services.speech import close_speech_session
        from src.services.ai_analyzer import close_gpt_session
        from src.services.sheets_async import shutdown_executor

        await close_speech_session()
        await close_gpt_session()
        shutdown_executor()

        health_status = get_health_checker().get_health_status()
        logger.info(f"Shutdown complete - Final stats: {health_status['requests']}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def main():
    """Точка входа в приложение."""
    global _application

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    _application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(5)
        .get_updates_read_timeout(60)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    _application.add_error_handler(error_handler)

    _application.add_handler(CommandHandler("start", start_command))
    _application.add_handler(CommandHandler("health", health_command))
    _application.add_handler(CommandHandler("stats", stats_command))

    _application.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    _application.add_handler(CallbackQueryHandler(period_callback, pattern=r"^period:"))
    _application.add_handler(CallbackQueryHandler(transactions_callback, pattern=r"^transactions:"))
    _application.add_handler(CallbackQueryHandler(backup_callback, pattern=r"^backup:"))
    _application.add_handler(CallbackQueryHandler(transaction_callback, pattern=r"^tx:"))
    _application.add_handler(CallbackQueryHandler(edit_callback, pattern=r"^edit:"))
    _application.add_handler(CallbackQueryHandler(category_callback, pattern=r"^cat:"))
    _application.add_handler(CallbackQueryHandler(health_callback, pattern=r"^health:"))

    _application.add_handler(MessageHandler(filters.VOICE, voice_message_handler))
    _application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    try:
        from src.services.scheduler import start_scheduler, set_report_callback
        set_report_callback(send_report_to_users)
        start_scheduler()
        logger.info("Scheduler initialized")
    except Exception as e:
        logger.warning(f"Scheduler not started: {e}")

    logger.info("Starting bot...")
    _application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
