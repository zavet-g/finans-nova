import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.bot.handlers.menu import help_callback
from src.bot.keyboards import (
    analytics_period_keyboard,
    analytics_result_keyboard,
    backup_keyboard,
    categories_keyboard,
    charts_menu_keyboard,
    confirm_transaction_keyboard,
    edit_transaction_keyboard,
    health_keyboard,
    main_menu_keyboard,
    transactions_list_keyboard,
    yearly_charts_keyboard,
)
from src.bot.message_manager import EFFECT_CELEBRATE, update_main_message
from src.models.category import TransactionType, get_category_by_code

logger = logging.getLogger(__name__)


async def safe_answer_callback(query):
    try:
        await query.answer()
    except BadRequest as e:
        if "query is too old" in str(e).lower():
            logger.debug("Callback query too old, ignoring")
        else:
            raise


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов главного меню."""
    query = update.callback_query
    await safe_answer_callback(query)

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
    elif action == "health":
        await show_health(update, context)


async def show_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает последние транзакции как изображение."""
    chat_id = update.effective_chat.id

    await update_main_message(context, chat_id, text="Загружаю транзакции...")

    try:
        import asyncio

        from src.services.charts import generate_transactions_image
        from src.services.sheets_async import async_get_transactions

        transactions = await async_get_transactions(limit=15)
        if not transactions:
            await update_main_message(
                context,
                chat_id,
                text="Пока транзакций нет.\n"
                "Отправь голосовое или текстовое сообщение, чтобы добавить первую.",
                reply_markup=transactions_list_keyboard(),
            )
            return

        loop = asyncio.get_event_loop()
        image = await loop.run_in_executor(None, generate_transactions_image, transactions)

        await update_main_message(
            context,
            chat_id,
            photo=image,
            caption=f"Последние {len(transactions)} транзакций",
            reply_markup=transactions_list_keyboard(),
            show_caption_above_media=True,
        )

    except Exception as e:
        logger.error(f"Failed to load transactions: {e}")
        await update_main_message(
            context,
            chat_id,
            text="Не удалось загрузить транзакции. Проверь настройки Google Sheets.",
            reply_markup=transactions_list_keyboard(),
        )


DRAFT_THROTTLE_INTERVAL = 0.8


async def _stream_ai_report(context, chat_id: int, prompt: str, period_name: str) -> str:
    """Генерирует AI-отчёт со стримингом через sendMessageDraft (если доступен)."""
    import time

    from src.services.ai_analyzer import call_yandex_gpt_stream

    header = f"AI-АНАЛИЗ ЗА {period_name.upper()}\n\n"
    accumulated = ""
    draft_supported = True
    last_draft_time = 0.0

    async for chunk in call_yandex_gpt_stream(prompt):
        accumulated += chunk

        now = time.monotonic()
        if draft_supported and (now - last_draft_time) >= DRAFT_THROTTLE_INTERVAL:
            try:
                await context.bot.send_message_draft(
                    chat_id=chat_id,
                    draft_id=1,
                    text=header + accumulated,
                )
                last_draft_time = now
            except Exception as e:
                logger.debug(f"sendMessageDraft unavailable: {e}")
                draft_supported = False

    return accumulated


async def show_analytics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню выбора периода аналитики."""
    chat_id = update.effective_chat.id
    text = "АНАЛИТИКА\n\nВыбери период для AI-анализа расходов:"
    await update_main_message(context, chat_id, text=text, reply_markup=analytics_period_keyboard())


async def show_charts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает подменю графиков."""
    chat_id = update.effective_chat.id
    await update_main_message(
        context, chat_id, text="Выбери период для графиков:", reply_markup=charts_menu_keyboard()
    )


async def charts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов подменю графиков."""
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id
    action = query.data.split(":")[1]

    if action == "back":
        welcome_text = "Отправь голосовое или текстовое сообщение с информацией о расходе/доходе."
        await update_main_message(
            context, chat_id, text=welcome_text, reply_markup=main_menu_keyboard()
        )

    elif action == "menu":
        await update_main_message(
            context,
            chat_id,
            text="Выбери период для графиков:",
            reply_markup=charts_menu_keyboard(),
        )

    elif action == "current_month":
        await _generate_current_month_chart(context, chat_id)

    elif action == "yearly":
        await update_main_message(
            context,
            chat_id,
            text="Выбери тип годового графика:",
            reply_markup=yearly_charts_keyboard(),
        )

    elif action == "yearly_income":
        await _generate_yearly_chart(context, chat_id, chart_type="income")

    elif action == "yearly_expense":
        await _generate_yearly_chart(context, chat_id, chart_type="expenses")


async def _generate_current_month_chart(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Генерирует график за текущий месяц."""
    await update_main_message(context, chat_id, text="Генерирую графики...")

    try:
        import asyncio

        from src.services.charts import generate_monthly_summary_chart
        from src.services.sheets_async import async_get_month_summary
        from src.utils.formatters import month_name

        now = datetime.now()
        summary = await async_get_month_summary(now.year, now.month)

        if summary.get("expenses", 0) == 0 and summary.get("income", 0) == 0:
            await update_main_message(
                context,
                chat_id,
                text="ГРАФИКИ\n\n"
                "Пока недостаточно данных для построения графиков.\n"
                "Добавь несколько транзакций.",
                reply_markup=charts_menu_keyboard(),
            )
            return

        loop = asyncio.get_event_loop()
        chart = await loop.run_in_executor(
            None, generate_monthly_summary_chart, summary, month_name(now.month), now.year
        )
        balance = summary.get("balance", 0)

        await update_main_message(
            context,
            chat_id,
            photo=chart,
            caption=f"Финансовая сводка за {month_name(now.month)} {now.year}\n\n"
            f"Баланс месяца: {balance:,.0f} руб.".replace(",", " "),
            reply_markup=charts_menu_keyboard(),
            show_caption_above_media=True,
        )

    except Exception as e:
        logger.error(f"Failed to generate monthly chart: {e}")
        await update_main_message(
            context,
            chat_id,
            text=f"Не удалось построить графики.\nОшибка: {str(e)[:100]}",
            reply_markup=charts_menu_keyboard(),
        )


async def _generate_yearly_chart(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, chart_type: str
) -> None:
    """Генерирует годовой график доходов или расходов."""
    is_income = chart_type == "income"
    label = "доходов" if is_income else "расходов"
    await update_main_message(context, chat_id, text=f"Генерирую график {label} за год...")

    try:
        import asyncio

        from src.services.charts import generate_yearly_expense_chart, generate_yearly_income_chart
        from src.services.sheets_async import async_get_yearly_monthly_breakdown
        from src.utils.formatters import format_amount

        now = datetime.now()
        data = await async_get_yearly_monthly_breakdown(now.year)

        monthly_data = data[chart_type]
        total = sum(monthly_data.values())

        if total == 0:
            await update_main_message(
                context,
                chat_id,
                text=f"ГРАФИК ЗА ГОД\n\nНет данных о {label} за {now.year} год.",
                reply_markup=yearly_charts_keyboard(),
            )
            return

        loop = asyncio.get_event_loop()
        if is_income:
            chart = await loop.run_in_executor(
                None, generate_yearly_income_chart, monthly_data, now.year
            )
        else:
            chart = await loop.run_in_executor(
                None, generate_yearly_expense_chart, monthly_data, now.year
            )

        type_label = "Доходы" if is_income else "Расходы"
        await update_main_message(
            context,
            chat_id,
            photo=chart,
            caption=f"{type_label} по месяцам за {now.year} год\n\n"
            f"Итого: {format_amount(total)} руб.",
            reply_markup=yearly_charts_keyboard(),
            show_caption_above_media=True,
        )

    except Exception as e:
        logger.error(f"Failed to generate yearly {chart_type} chart: {e}")
        await update_main_message(
            context,
            chat_id,
            text=f"Не удалось построить график.\nОшибка: {str(e)[:100]}",
            reply_markup=yearly_charts_keyboard(),
        )


async def show_backup_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню бэкапов."""
    chat_id = update.effective_chat.id

    text = (
        "БЭКАП И ЭКСПОРТ\n\n"
        "Автоматический бэкап: каждое воскресенье в 03:00\n"
        "Хранится: последние 4 бэкапа (1 месяц)"
    )

    await update_main_message(context, chat_id, text=text, reply_markup=backup_keyboard())


async def open_sheets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет ссылку на Google Sheets."""
    chat_id = update.effective_chat.id

    from src.config import GOOGLE_SHEETS_SPREADSHEET_ID

    if GOOGLE_SHEETS_SPREADSHEET_ID:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_SPREADSHEET_ID}"
        text = f"Ссылка на таблицу:\n{url}"
    else:
        text = "Google Sheets не настроен. Добавь GOOGLE_SHEETS_SPREADSHEET_ID в .env"

    await update_main_message(context, chat_id, text=text, reply_markup=main_menu_keyboard())


async def period_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора периода аналитики."""
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id
    action = query.data.split(":")[1]

    if action == "back":
        welcome_text = "Отправь голосовое или текстовое сообщение с информацией о расходе/доходе."
        await update_main_message(
            context, chat_id, text=welcome_text, reply_markup=main_menu_keyboard()
        )
        return

    await update_main_message(context, chat_id, text="📊 Анализирую данные...")

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
            await update_main_message(
                context,
                chat_id,
                text="Выбери период из списка.",
                reply_markup=analytics_period_keyboard(),
            )
            return

        delta, period_name = period_config[action]
        start_date = now - delta
        end_date = now

        prev_start = start_date - delta
        prev_end = start_date

        import asyncio

        from src.services.ai_analyzer import (
            build_period_report_prompt,
            generate_fallback_period_report,
        )
        from src.services.sheets_async import async_get_enriched_analytics, async_get_period_summary

        summary, enriched_data = await asyncio.wait_for(
            asyncio.gather(
                async_get_period_summary(start_date, end_date),
                async_get_enriched_analytics(start_date, end_date, prev_start, prev_end),
            ),
            timeout=30.0,
        )

        if summary.get("expenses", 0) == 0 and summary.get("income", 0) == 0:
            await update_main_message(
                context,
                chat_id,
                text=f"Анализ за {period_name}\n\nНет транзакций за выбранный период.",
                reply_markup=main_menu_keyboard(),
            )
            return

        prompt = build_period_report_prompt(
            summary=summary,
            transactions_markdown="",
            period_name=period_name,
            enriched_data=enriched_data,
        )

        if prompt:
            report = await _stream_ai_report(context, chat_id, prompt, period_name)
        else:
            report = generate_fallback_period_report(summary, period_name)

        from src.utils.formatters import format_amount

        income = summary.get("income", 0)
        expenses = summary.get("expenses", 0)
        balance = income - expenses
        copy_summary = (
            f"Финансы за {period_name}:\n"
            f"Доходы: {format_amount(income)} руб.\n"
            f"Расходы: {format_amount(expenses)} руб.\n"
            f"Баланс: {format_amount(balance, with_sign=True)} руб."
        )

        display_text = f"AI-АНАЛИЗ ЗА {period_name.upper()}\n\n{report}"
        await update_main_message(
            context,
            chat_id,
            text=display_text,
            reply_markup=analytics_result_keyboard(copy_summary),
        )

    except asyncio.TimeoutError:
        logger.error("Analytics generation timeout")
        await update_main_message(
            context,
            chat_id,
            text="📊 Время ожидания истекло. Попробуй выбрать меньший период.",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Failed to generate analytics: {e}")
        await update_main_message(
            context,
            chat_id,
            text=f"📊 Не удалось выполнить анализ.\nОшибка: {str(e)[:100]}",
            reply_markup=main_menu_keyboard(),
        )


async def analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов результата аналитики."""
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id
    action = query.data.split(":")[1]

    if action == "back":
        welcome_text = "Отправь голосовое или текстовое сообщение с информацией о расходе/доходе."
        await update_main_message(
            context, chat_id, text=welcome_text, reply_markup=main_menu_keyboard()
        )


async def transactions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов списка транзакций."""
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id
    action = query.data.split(":")[1]

    if action == "back":
        welcome_text = "Отправь голосовое или текстовое сообщение с информацией о расходе/доходе."
        await update_main_message(
            context, chat_id, text=welcome_text, reply_markup=main_menu_keyboard()
        )


async def backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов бэкапа."""
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id
    action = query.data.split(":")[1]

    if action == "back":
        welcome_text = "Отправь голосовое или текстовое сообщение с информацией о расходе/доходе."
        await update_main_message(
            context, chat_id, text=welcome_text, reply_markup=main_menu_keyboard()
        )

    elif action == "csv":
        await update_main_message(context, chat_id, text="📥 Экспортирую данные...")

        try:
            from io import BytesIO

            from src.services.sheets_async import async_export_to_csv

            csv_data = await async_export_to_csv()

            file = BytesIO(csv_data.encode("utf-8"))
            file.name = f"transactions_{datetime.now().strftime('%Y%m%d')}.csv"

            await update_main_message(
                context,
                chat_id,
                document=file,
                filename=file.name,
                caption="📥 Экспорт транзакций в CSV",
                reply_markup=backup_keyboard(),
            )
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            await update_main_message(
                context,
                chat_id,
                text=f"📥 Не удалось экспортировать данные.\nОшибка: {str(e)[:100]}",
                reply_markup=backup_keyboard(),
            )

    elif action == "now":
        await update_main_message(context, chat_id, text="💾 Создаю бэкап...")

        try:
            from src.services.sheets_async import async_create_backup

            backup_name = await async_create_backup()
            await update_main_message(
                context,
                chat_id,
                text=f"💾 Бэкап создан!\n\nНазвание: {backup_name}\n\n"
                "Копия таблицы сохранена на Google Drive.",
                reply_markup=backup_keyboard(),
            )
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            await update_main_message(
                context,
                chat_id,
                text=f"💾 Не удалось создать бэкап.\nОшибка: {str(e)[:100]}",
                reply_markup=backup_keyboard(),
            )


async def transaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов подтверждения транзакции."""
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id
    action = query.data.split(":")[1]
    pending_tx = context.user_data.get("pending_transaction")

    if context.user_data.get("_processing_transaction"):
        logger.debug("Transaction already being processed, ignoring duplicate click")
        return

    if action == "confirm":
        if pending_tx:
            context.user_data["_processing_transaction"] = True
            try:
                from src.services.sheets_async import async_add_transaction

                tx_id = await async_add_transaction(pending_tx)
                text = f"✅ Транзакция #{tx_id} добавлена!\n\n{pending_tx.format_for_user()}"
            except Exception as e:
                logger.error(f"Failed to save transaction: {e}")
                text = f"✅ Транзакция записана.\n\n{pending_tx.format_for_user()}"
            finally:
                context.user_data.pop("_processing_transaction", None)
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

                    combined = (
                        f"{text}\n\n---\n\n"
                        f"Транзакция {current} из {total}:\n\n{next_tx.format_for_user()}"
                    )
                    await update_main_message(
                        context,
                        chat_id,
                        text=combined,
                        reply_markup=confirm_transaction_keyboard(),
                    )
                    return
                else:
                    context.user_data.pop("pending_transactions", None)
                    context.user_data.pop("current_tx_index", None)
                    text += "\n\nВсе транзакции обработаны!"
        else:
            text = "Нет транзакции для подтверждения."
        await update_main_message(
            context,
            chat_id,
            text=text,
            reply_markup=main_menu_keyboard(),
            message_effect_id=EFFECT_CELEBRATE if pending_tx else None,
        )

    elif action == "edit":
        if pending_tx:
            text = f"✏️ Что изменить?\n\n{pending_tx.format_for_user()}"
            await update_main_message(
                context, chat_id, text=text, reply_markup=edit_transaction_keyboard()
            )
        else:
            await update_main_message(
                context,
                chat_id,
                text="Нет транзакции для редактирования.",
                reply_markup=main_menu_keyboard(),
            )

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

                combined = (
                    f"❌ Пропущена.\n\n---\n\n"
                    f"Транзакция {current} из {total}:\n\n{next_tx.format_for_user()}"
                )
                await update_main_message(
                    context,
                    chat_id,
                    text=combined,
                    reply_markup=confirm_transaction_keyboard(),
                )
                return
            else:
                context.user_data.pop("pending_transactions", None)
                context.user_data.pop("current_tx_index", None)
        await update_main_message(
            context, chat_id, text="❌ Транзакция отменена.", reply_markup=main_menu_keyboard()
        )


async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-ов редактирования транзакции."""
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id
    action = query.data.split(":")[1]
    pending_tx = context.user_data.get("pending_transaction")

    if action == "back":
        if pending_tx:
            text = f"Подтвердить транзакцию?\n\n{pending_tx.format_for_user()}"
            await update_main_message(
                context, chat_id, text=text, reply_markup=confirm_transaction_keyboard()
            )
        else:
            await update_main_message(
                context,
                chat_id,
                text="Отправь голосовое или текстовое сообщение.",
                reply_markup=main_menu_keyboard(),
            )

    elif action == "category":
        if pending_tx:
            await update_main_message(
                context,
                chat_id,
                text="Выбери категорию:",
                reply_markup=categories_keyboard(pending_tx.type),
            )

    elif action == "type":
        if pending_tx:
            new_type = (
                TransactionType.INCOME
                if pending_tx.type == TransactionType.EXPENSE
                else TransactionType.EXPENSE
            )
            pending_tx.type = new_type
            if new_type == TransactionType.INCOME:
                pending_tx.category = "Доход"
            text = f"Тип изменён.\n\n{pending_tx.format_for_user()}"
            await update_main_message(
                context, chat_id, text=text, reply_markup=edit_transaction_keyboard()
            )

    elif action == "amount":
        context.user_data["editing_field"] = "amount"
        await update_main_message(context, chat_id, text="Введи новую сумму:")

    elif action == "description":
        context.user_data["editing_field"] = "description"
        await update_main_message(context, chat_id, text="Введи новое описание:")


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора категории."""
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id
    action = query.data.split(":")[1]
    pending_tx = context.user_data.get("pending_transaction")

    if action == "back":
        if pending_tx:
            text = f"✏️ Что изменить?\n\n{pending_tx.format_for_user()}"
            await update_main_message(
                context, chat_id, text=text, reply_markup=edit_transaction_keyboard()
            )
        return

    if pending_tx:
        category = get_category_by_code(action)
        if category:
            pending_tx.category = category.name
            text = f"Категория изменена.\n\n{pending_tx.format_for_user()}"
            await update_main_message(
                context, chat_id, text=text, reply_markup=confirm_transaction_keyboard()
            )


async def show_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id

    try:
        from src.services.health_monitor import get_health_monitor
        from src.services.metrics import get_metrics
        from src.utils.health_formatter import format_health_report

        metrics = get_metrics()
        health_monitor = get_health_monitor()

        metrics_summary = metrics.get_metrics_summary()
        services_status = metrics.get_services_status()
        request_types = metrics.get_request_types_stats()
        health_checks = await health_monitor.check_all_services()

        report = format_health_report(
            metrics_summary, services_status, request_types, health_checks
        )

        await update_main_message(context, chat_id, text=report, reply_markup=health_keyboard())
    except Exception as e:
        logger.error(f"Failed to load health status: {e}", exc_info=True)
        error_text = (
            f"🔧 СОСТОЯНИЕ БОТА\n\nНе удалось загрузить информацию.\nОшибка: {str(e)[:100]}"
        )
        await update_main_message(context, chat_id, text=error_text, reply_markup=health_keyboard())


async def health_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await safe_answer_callback(query)

    chat_id = update.effective_chat.id
    action = query.data.split(":")[1]

    if action == "back":
        welcome_text = "Отправь голосовое или текстовое сообщение с информацией о расходе/доходе."
        await update_main_message(
            context, chat_id, text=welcome_text, reply_markup=main_menu_keyboard()
        )
    elif action == "refresh":
        await show_health(update, context)
