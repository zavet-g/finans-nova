import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.bot.keyboards import main_menu_keyboard
from src.bot.message_manager import delete_user_message, setup_reply_keyboard, update_main_message
from src.config import ALLOWED_USER_IDS

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

    chat_id = update.effective_chat.id
    logger.debug(
        f"start_command: user={user.id}, update_id={update.update_id}, "
        f"message_id={update.message.message_id}"
    )

    welcome_text = (
        f"Привет, {user.first_name}!\n\n"
        "Я твой личный финансовый аналитик.\n\n"
        "Отправь голосовое или текстовое сообщение с информацией о расходе/доходе.\n\n"
        "Например: «потратил 500 на такси» или «получил зарплату 100000»"
    )

    context.user_data.pop("main_message_id", None)
    await setup_reply_keyboard(context, chat_id)
    await update_main_message(
        context, chat_id, text=welcome_text, reply_markup=main_menu_keyboard()
    )
    await delete_user_message(update.message)
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

    chat_id = update.effective_chat.id
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except BadRequest as e:
            if "query is too old" not in str(e).lower():
                raise

    await update_main_message(context, chat_id, text=help_text, reply_markup=main_menu_keyboard())
