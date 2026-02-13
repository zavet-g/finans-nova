import logging
import re

from telegram import Update
from telegram.error import BadRequest, TimedOut
from telegram.ext import ContextTypes

from src.bot.handlers.menu import is_user_allowed
from src.bot.keyboards import confirm_transaction_keyboard, edit_transaction_keyboard
from src.utils.metrics_decorator import track_request

logger = logging.getLogger(__name__)


async def safe_reply(message, text: str, reply_markup=None):
    try:
        return await message.reply_text(text, reply_markup=reply_markup)
    except TimedOut:
        logger.warning("Reply timeout, retrying once...")
        try:
            return await message.reply_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Reply retry failed: {e}")
            return None
    except BadRequest as e:
        logger.warning(f"BadRequest in reply: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in reply: {e}", exc_info=True)
        return None


def parse_multiple_transactions(text: str) -> list[dict]:
    """Парсит несколько транзакций из текста."""

    transactions = []

    parts = re.split(r"[,;]\s*|\s+и\s+", text)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        amount = parse_amount_from_part(part)
        if amount is None:
            continue

        tx_type, category = determine_type_and_category(part)
        description = clean_description(part)

        if description:
            transactions.append(
                {
                    "type": tx_type,
                    "category": category,
                    "description": description,
                    "amount": amount,
                }
            )

    return transactions


def parse_amount_from_part(text: str) -> float | None:
    """Извлекает сумму из части текста."""
    text_clean = text.lower().replace("\u00a0", " ")

    patterns = [
        r"(\d+[\s.]*\d*)\s*(?:т(?:ыс)?(?:яч)?\.?)\s*(?:р|руб|рублей|₽)?",
        r"(\d+[\s.]*\d*)\s*(?:р|руб|рублей|₽)",
        r"(?:за|на|потратил|заплатил|получил|доход|оплатил)\s*(\d+[\s.]*\d*)",
        r"(\d+[\s.]*\d*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text_clean)
        if match:
            try:
                num_str = match.group(1).replace(" ", "").replace(".", "")
                amount = float(num_str)

                if "тыс" in text_clean or "т." in text_clean or "т " in text_clean:
                    if amount < 1000:
                        amount *= 1000

                if amount > 0:
                    return amount
            except ValueError:
                continue

    return None


@track_request("text", "yandex_gpt")
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_user_allowed(user.id):
        return

    text = update.message.text.strip()

    editing_field = context.user_data.get("editing_field")
    pending_tx = context.user_data.get("pending_transaction")

    if editing_field and pending_tx:
        if editing_field == "amount":
            try:
                amount = parse_amount(text)
                pending_tx.amount = amount
                context.user_data.pop("editing_field", None)
                await safe_reply(
                    update.message,
                    f"Сумма изменена.\n\n{pending_tx.format_for_user()}",
                    reply_markup=edit_transaction_keyboard(),
                )
            except ValueError:
                await safe_reply(update.message, "Не удалось распознать сумму. Введи число:")
            return

        elif editing_field == "description":
            pending_tx.description = text
            context.user_data.pop("editing_field", None)
            await safe_reply(
                update.message,
                f"Описание изменено.\n\n{pending_tx.format_for_user()}",
                reply_markup=edit_transaction_keyboard(),
            )
            return

    await process_transaction_text(update, context, text)


async def process_transaction_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> None:
    """Обрабатывает текст и создаёт транзакции через AI."""
    from src.models.transaction import Transaction
    from src.services.ai_analyzer import parse_transactions

    processing_msg = await safe_reply(update.message, "Анализирую через AI...")
    if not processing_msg:
        return

    try:
        ai_results = await parse_transactions(text)
        try:
            await processing_msg.delete()
        except Exception:
            pass
    except Exception:
        try:
            await processing_msg.delete()
        except Exception:
            pass
        raise

    if ai_results:
        transactions = [
            Transaction(
                type=tx["type"],
                category=tx["category"],
                description=tx["description"],
                amount=tx["amount"],
            )
            for tx in ai_results
        ]

        if len(transactions) == 1:
            context.user_data["pending_transaction"] = transactions[0]
            context.user_data.pop("pending_transactions", None)
            await safe_reply(
                update.message,
                f"Распознана транзакция:\n\n{transactions[0].format_for_user()}",
                reply_markup=confirm_transaction_keyboard(),
            )
        else:
            context.user_data["pending_transactions"] = transactions
            context.user_data["current_tx_index"] = 0
            context.user_data.pop("pending_transaction", None)
            await show_next_transaction(update, context)
        return

    parsed = parse_multiple_transactions(text)

    if not parsed:
        amount = parse_amount_from_part(text)
        if amount is None:
            await safe_reply(
                update.message,
                "Не удалось распознать сумму. Попробуй написать иначе.\n"
                "Например: «потратил 500 на такси»",
            )
            return

        tx_type, category = determine_type_and_category(text)
        parsed = [
            {
                "type": tx_type,
                "category": category,
                "description": clean_description(text) or text,
                "amount": amount,
            }
        ]

    if len(parsed) == 1:
        tx_data = parsed[0]
        transaction = Transaction(
            type=tx_data["type"],
            category=tx_data["category"],
            description=tx_data["description"],
            amount=tx_data["amount"],
        )
        context.user_data["pending_transaction"] = transaction
        context.user_data.pop("pending_transactions", None)

        await safe_reply(
            update.message,
            f"Распознана транзакция:\n\n{transaction.format_for_user()}",
            reply_markup=confirm_transaction_keyboard(),
        )
    else:
        transactions = [
            Transaction(
                type=tx["type"],
                category=tx["category"],
                description=tx["description"],
                amount=tx["amount"],
            )
            for tx in parsed
        ]

        context.user_data["pending_transactions"] = transactions
        context.user_data["current_tx_index"] = 0
        context.user_data.pop("pending_transaction", None)

        await show_next_transaction(update, context)


async def show_next_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает следующую транзакцию из списка для подтверждения."""
    transactions = context.user_data.get("pending_transactions", [])
    index = context.user_data.get("current_tx_index", 0)

    if index >= len(transactions):
        await safe_reply(update.message, "Все транзакции обработаны!", reply_markup=None)
        context.user_data.pop("pending_transactions", None)
        context.user_data.pop("current_tx_index", None)
        return

    tx = transactions[index]
    context.user_data["pending_transaction"] = tx

    total = len(transactions)
    current = index + 1

    await safe_reply(
        update.message,
        f"Транзакция {current} из {total}:\n\n{tx.format_for_user()}",
        reply_markup=confirm_transaction_keyboard(),
    )


def parse_amount(text: str) -> float | None:
    """Извлекает сумму из текста."""
    import re

    text = text.lower().replace(" ", "").replace("\u00a0", "")
    text = text.replace(".", "").replace(",", "")

    patterns = [
        r"(\d+)\s*(?:р|руб|рублей|₽)",
        r"(?:за|на|потратил|заплатил|получил|доход)\s*(\d+)",
        r"(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue

    return None


def determine_type_and_category(text: str) -> tuple:
    """Определяет тип и категорию транзакции по тексту."""
    from src.models.category import EXPENSE_CATEGORIES, INCOME_CATEGORY, TransactionType

    text_lower = text.lower()

    income_keywords = ["зарплата", "получил", "доход", "заработал", "премия", "перевод от"]
    if any(kw in text_lower for kw in income_keywords):
        return TransactionType.INCOME, INCOME_CATEGORY.name

    for category in EXPENSE_CATEGORIES:
        for keyword in category.keywords:
            if keyword in text_lower:
                return TransactionType.EXPENSE, category.name

    return TransactionType.EXPENSE, "Прочее"


def clean_description(text: str) -> str:
    """Очищает описание от лишних слов."""
    import re

    text = re.sub(r"\d+\s*(?:р|руб|рублей|₽|тысяч|тыс)?", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    remove_words = ["потратил", "заплатил", "на", "за", "купил"]
    words = text.split()
    words = [w for w in words if w.lower() not in remove_words]

    result = " ".join(words).strip()
    return result if result else text
