import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.keyboards import (
    main_menu_keyboard,
    analytics_period_keyboard,
    backup_keyboard,
    transactions_list_keyboard,
    confirm_transaction_keyboard,
    edit_transaction_keyboard,
    categories_keyboard,
)
from src.bot.handlers.menu import help_callback
from src.models.category import TransactionType, get_category_by_code

logger = logging.getLogger(__name__)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов главного меню."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]

    if action == "transactions":
        await show_transactions(update, context)
    elif action == "analytics":
        await show_analytics_menu(update, context)
    elif action == "charts":
        await show_charts(update, context)
    elif action == "backup":
        await show_backup_menu(update, context)
    elif action == "sheets":
        await open_sheets(update, context)
    elif action == "help":
        await help_callback(update, context)


async def show_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает последние транзакции."""
    query = update.callback_query

    try:
        from src.services.sheets import get_transactions
        from src.utils.formatters import format_transaction_list

        transactions = get_transactions(limit=10)
        if transactions:
            tx_text = format_transaction_list(transactions)
            text = f"📋 ПОСЛЕДНИЕ ТРАНЗАКЦИИ\n\n{tx_text}"
            has_more = len(transactions) == 10
        else:
            text = (
                "📋 ПОСЛЕДНИЕ ТРАНЗАКЦИИ\n\n"
                "Пока транзакций нет.\n"
                "Отправь голосовое или текстовое сообщение, чтобы добавить первую."
            )
            has_more = False
    except Exception as e:
        logger.error(f"Failed to load transactions: {e}")
        text = (
            "📋 ПОСЛЕДНИЕ ТРАНЗАКЦИИ\n\n"
            "Не удалось загрузить транзакции. Проверь настройки Google Sheets."
        )
        has_more = False

    try:
        await query.edit_message_text(text, reply_markup=transactions_list_keyboard(has_more=has_more))
    except Exception:
        await query.message.reply_text(text, reply_markup=transactions_list_keyboard(has_more=has_more))


async def show_analytics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню выбора периода аналитики."""
    query = update.callback_query

    text = (
        "АНАЛИТИКА\n\n"
        "Выбери период для AI-анализа расходов:"
    )

    try:
        await query.edit_message_text(text, reply_markup=analytics_period_keyboard())
    except Exception:
        await query.message.reply_text(text, reply_markup=analytics_period_keyboard())


async def show_charts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает графики расходов."""
    query = update.callback_query

    if query.message.text:
        try:
            await query.edit_message_text("📈 Генерирую графики...", reply_markup=None)
        except Exception:
            await query.message.reply_text("📈 Генерирую графики...")
    else:
        await query.message.reply_text("📈 Генерирую графики...")

    try:
        from src.services.sheets import get_expenses_by_category, get_month_summary, get_current_balance
        from src.services.charts import generate_monthly_summary_chart
        from src.utils.formatters import month_name

        now = datetime.now()
        summary = get_month_summary(now.year, now.month)
        balance = get_current_balance()

        if summary.get("expenses", 0) == 0 and summary.get("income", 0) == 0:
            await query.message.reply_text(
                "📈 ГРАФИКИ\n\n"
                "Пока недостаточно данных для построения графиков.\n"
                "Добавь несколько транзакций.",
                reply_markup=main_menu_keyboard()
            )
            return

        chart = generate_monthly_summary_chart(summary, month_name(now.month), now.year)

        await query.message.reply_photo(
            photo=chart,
            caption=f"📈 Финансовая сводка за {month_name(now.month)} {now.year}\n\n"
                    f"Текущий баланс: {balance:,.0f} руб.".replace(",", " "),
            reply_markup=main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Failed to generate charts: {e}")
        await query.message.reply_text(
            "📈 Не удалось построить графики.\n"
            f"Ошибка: {str(e)[:100]}",
            reply_markup=main_menu_keyboard()
        )


async def show_backup_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню бэкапов."""
    query = update.callback_query

    text = (
        "БЭКАП И ЭКСПОРТ\n\n"
        "Автоматический бэкап: каждое воскресенье в 03:00\n"
        "Хранится: последние 4 бэкапа (1 месяц)"
    )

    try:
        await query.edit_message_text(text, reply_markup=backup_keyboard())
    except Exception:
        await query.message.reply_text(text, reply_markup=backup_keyboard())


async def open_sheets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет ссылку на Google Sheets."""
    query = update.callback_query

    from src.config import GOOGLE_SHEETS_SPREADSHEET_ID
    if GOOGLE_SHEETS_SPREADSHEET_ID:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_SPREADSHEET_ID}"
        text = f"Ссылка на таблицу:\n{url}"
    else:
        text = "Google Sheets не настроен. Добавь GOOGLE_SHEETS_SPREADSHEET_ID в .env"

    try:
        await query.edit_message_text(text, reply_markup=main_menu_keyboard())
    except Exception:
        await query.message.reply_text(text, reply_markup=main_menu_keyboard())


async def period_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора периода аналитики."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]

    if action == "back":
        welcome_text = (
            "Отправь голосовое или текстовое сообщение "
            "с информацией о расходе/доходе."
        )
        await query.edit_message_text(welcome_text, reply_markup=main_menu_keyboard())
        return

    await query.edit_message_text("📊 Анализирую данные...", reply_markup=None)

    try:
        now = datetime.now()

        period_config = {
            "2w": (timedelta(days=14), "последние 2 недели"),
            "1m": (timedelta(days=30), "последний месяц"),
            "3m": (timedelta(days=90), "последние 3 месяца"),
            "6m": (timedelta(days=180), "последние 6 месяцев"),
            "1y": (timedelta(days=365), "последний год"),
        }

        if action not in period_config:
            await query.message.reply_text(
                "Выбери период из списка.",
                reply_markup=analytics_period_keyboard()
            )
            return

        delta, period_name = period_config[action]
        start_date = now - delta
        end_date = now

        from src.services.sheets import get_period_summary, get_period_transactions_markdown
        from src.services.ai_analyzer import generate_period_report

        summary = get_period_summary(start_date, end_date)

        if summary.get("expenses", 0) == 0 and summary.get("income", 0) == 0:
            await query.message.reply_text(
                f"📊 Анализ за {period_name}\n\n"
                "Нет транзакций за выбранный период.",
                reply_markup=main_menu_keyboard()
            )
            return

        transactions_md = get_period_transactions_markdown(start_date, end_date, limit=100)

        report = await generate_period_report(
            summary=summary,
            transactions_markdown=transactions_md,
            period_name=period_name,
        )

        await query.message.reply_text(
            f"📊 AI-АНАЛИЗ ЗА {period_name.upper()}\n\n{report}",
            reply_markup=main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Failed to generate analytics: {e}")
        await query.message.reply_text(
            f"📊 Не удалось выполнить анализ.\nОшибка: {str(e)[:100]}",
            reply_markup=main_menu_keyboard()
        )


async def transactions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов списка транзакций."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]

    if action == "back":
        welcome_text = (
            "Отправь голосовое или текстовое сообщение "
            "с информацией о расходе/доходе."
        )
        await query.edit_message_text(welcome_text, reply_markup=main_menu_keyboard())
    elif action == "more":
        await show_transactions(update, context)


async def backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов бэкапа."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]

    if action == "back":
        welcome_text = (
            "Отправь голосовое или текстовое сообщение "
            "с информацией о расходе/доходе."
        )
        await query.edit_message_text(welcome_text, reply_markup=main_menu_keyboard())

    elif action == "csv":
        await query.edit_message_text("📥 Экспортирую данные...", reply_markup=None)
        try:
            from src.services.sheets import export_to_csv
            csv_data = export_to_csv()

            from io import BytesIO
            file = BytesIO(csv_data.encode('utf-8'))
            file.name = f"transactions_{datetime.now().strftime('%Y%m%d')}.csv"

            await query.message.reply_document(
                document=file,
                filename=file.name,
                caption="📥 Экспорт транзакций в CSV",
                reply_markup=backup_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            await query.message.reply_text(
                f"📥 Не удалось экспортировать данные.\nОшибка: {str(e)[:100]}",
                reply_markup=backup_keyboard()
            )

    elif action == "now":
        await query.edit_message_text("💾 Создаю бэкап...", reply_markup=None)
        try:
            from src.services.sheets import create_backup
            backup_name = create_backup()
            await query.message.reply_text(
                f"💾 Бэкап создан!\n\nНазвание: {backup_name}\n\n"
                "Копия таблицы сохранена на Google Drive.",
                reply_markup=backup_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            await query.message.reply_text(
                f"💾 Не удалось создать бэкап.\nОшибка: {str(e)[:100]}",
                reply_markup=backup_keyboard()
            )


async def transaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов подтверждения транзакции."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]
    pending_tx = context.user_data.get("pending_transaction")

    if action == "confirm":
        if pending_tx:
            try:
                from src.services.sheets import add_transaction
                tx_id = add_transaction(pending_tx)
                text = f"✅ Транзакция #{tx_id} добавлена!\n\n{pending_tx.format_for_user()}"
            except Exception as e:
                logger.error(f"Failed to save transaction: {e}")
                text = f"✅ Транзакция записана.\n\n{pending_tx.format_for_user()}"
            context.user_data.pop("pending_transaction", None)

            pending_list = context.user_data.get("pending_transactions")
            if pending_list:
                index = context.user_data.get("current_tx_index", 0) + 1
                context.user_data["current_tx_index"] = index

                if index < len(pending_list):
                    next_tx = pending_list[index]
                    context.user_data["pending_transaction"] = next_tx
                    total = len(pending_list)
                    current = index + 1
                    text += f"\n\n───────────────\n\nТранзакция {current} из {total}:\n\n{next_tx.format_for_user()}"
                    await query.edit_message_text(text, reply_markup=confirm_transaction_keyboard())
                    return
                else:
                    context.user_data.pop("pending_transactions", None)
                    context.user_data.pop("current_tx_index", None)
                    text += "\n\nВсе транзакции обработаны!"
        else:
            text = "Нет транзакции для подтверждения."
        await query.edit_message_text(text, reply_markup=main_menu_keyboard())

    elif action == "edit":
        if pending_tx:
            text = f"✏️ Что изменить?\n\n{pending_tx.format_for_user()}"
            await query.edit_message_text(text, reply_markup=edit_transaction_keyboard())
        else:
            await query.edit_message_text("Нет транзакции для редактирования.", reply_markup=main_menu_keyboard())

    elif action == "cancel":
        context.user_data.pop("pending_transaction", None)
        pending_list = context.user_data.get("pending_transactions")
        if pending_list:
            index = context.user_data.get("current_tx_index", 0) + 1
            context.user_data["current_tx_index"] = index
            if index < len(pending_list):
                next_tx = pending_list[index]
                context.user_data["pending_transaction"] = next_tx
                total = len(pending_list)
                current = index + 1
                text = f"❌ Пропущена.\n\nТранзакция {current} из {total}:\n\n{next_tx.format_for_user()}"
                await query.edit_message_text(text, reply_markup=confirm_transaction_keyboard())
                return
            else:
                context.user_data.pop("pending_transactions", None)
                context.user_data.pop("current_tx_index", None)
        await query.edit_message_text("❌ Транзакция отменена.", reply_markup=main_menu_keyboard())


async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов редактирования транзакции."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]
    pending_tx = context.user_data.get("pending_transaction")

    if action == "back":
        if pending_tx:
            text = f"Подтвердить транзакцию?\n\n{pending_tx.format_for_user()}"
            await query.edit_message_text(text, reply_markup=confirm_transaction_keyboard())
        else:
            await query.edit_message_text(
                "Отправь голосовое или текстовое сообщение.",
                reply_markup=main_menu_keyboard()
            )

    elif action == "category":
        if pending_tx:
            await query.edit_message_text(
                "Выбери категорию:",
                reply_markup=categories_keyboard(pending_tx.type)
            )

    elif action == "type":
        if pending_tx:
            new_type = TransactionType.INCOME if pending_tx.type == TransactionType.EXPENSE else TransactionType.EXPENSE
            pending_tx.type = new_type
            if new_type == TransactionType.INCOME:
                pending_tx.category = "Доход"
            text = f"Тип изменён.\n\n{pending_tx.format_for_user()}"
            await query.edit_message_text(text, reply_markup=edit_transaction_keyboard())

    elif action == "amount":
        context.user_data["editing_field"] = "amount"
        await query.edit_message_text("Введи новую сумму:")

    elif action == "description":
        context.user_data["editing_field"] = "description"
        await query.edit_message_text("Введи новое описание:")


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора категории."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]
    pending_tx = context.user_data.get("pending_transaction")

    if action == "back":
        if pending_tx:
            text = f"✏️ Что изменить?\n\n{pending_tx.format_for_user()}"
            await query.edit_message_text(text, reply_markup=edit_transaction_keyboard())
        return

    if pending_tx:
        category = get_category_by_code(action)
        if category:
            pending_tx.category = category.name
            text = f"Категория изменена.\n\n{pending_tx.format_for_user()}"
            await query.edit_message_text(text, reply_markup=confirm_transaction_keyboard())
