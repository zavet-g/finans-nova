import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.config import ALLOWED_USER_IDS
from src.bot.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


def is_user_allowed(user_id: int) -> bool:
    """Проверяет, разрешён ли доступ пользователю."""
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    if not is_user_allowed(user.id):
        await update.message.reply_text("Доступ запрещён.")
        logger.warning(f"Unauthorized access attempt from user {user.id}")
        return

    welcome_text = (
        f"Привет, {user.first_name}!\n\n"
        "Я твой личный финансовый аналитик.\n\n"
        "Отправь голосовое или текстовое сообщение с информацией о расходе/доходе.\n\n"
        "Например: «потратил 500 на такси» или «получил зарплату 100000»"
    )

    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard())
    logger.info(f"User {user.id} started the bot")


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку по использованию бота."""
    help_text = (
        "Как использовать бота:\n\n"
        "1. Отправь голосовое или текстовое сообщение с описанием траты или дохода\n"
        "2. Бот распознает сумму и категорию\n"
        "3. Подтверди или отредактируй транзакцию\n"
        "4. Данные сохранятся в Google Sheets\n\n"
        "Примеры сообщений:\n"
        "• «потратил 1200 на доставку еды»\n"
        "• «заплатил за такси 450 рублей»\n"
        "• «получил зарплату 100000»\n"
        "• «подписка на spotify 199р»\n\n"
        "Разделы меню:\n"
        "📋 Последние транзакции — история операций\n"
        "📊 Аналитика — AI-анализ расходов\n"
        "📈 Графики — визуализация трат\n"
        "💾 Бэкап — экспорт данных"
    )

    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(help_text, reply_markup=main_menu_keyboard())
    else:
        await update.message.reply_text(help_text, reply_markup=main_menu_keyboard())
