import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from src.config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
from src.bot.handlers.menu import start_command
from src.bot.handlers.text import text_message_handler
from src.bot.handlers.voice import voice_message_handler
from src.bot.handlers.callbacks import (
    menu_callback,
    period_callback,
    transactions_callback,
    backup_callback,
    transaction_callback,
    edit_callback,
    category_callback,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

_application = None


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


def main():
    """Точка входа в приложение."""
    global _application

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    try:
        from src.services.sheets import init_spreadsheet
        init_spreadsheet()
        logger.info("Spreadsheet structure initialized")
    except Exception as e:
        logger.warning(f"Could not initialize spreadsheet: {e}")

    _application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    _application.add_handler(CommandHandler("start", start_command))

    _application.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    _application.add_handler(CallbackQueryHandler(period_callback, pattern=r"^period:"))
    _application.add_handler(CallbackQueryHandler(transactions_callback, pattern=r"^transactions:"))
    _application.add_handler(CallbackQueryHandler(backup_callback, pattern=r"^backup:"))
    _application.add_handler(CallbackQueryHandler(transaction_callback, pattern=r"^tx:"))
    _application.add_handler(CallbackQueryHandler(edit_callback, pattern=r"^edit:"))
    _application.add_handler(CallbackQueryHandler(category_callback, pattern=r"^cat:"))

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
