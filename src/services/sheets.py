import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from src.config import GOOGLE_SHEETS_CREDENTIALS_FILE, GOOGLE_SHEETS_SPREADSHEET_ID, BASE_DIR
from src.models.transaction import Transaction
from src.models.category import TransactionType

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client: Optional[gspread.Client] = None
_spreadsheet: Optional[gspread.Spreadsheet] = None


def get_client() -> gspread.Client:
    """Возвращает авторизованный клиент Google Sheets."""
    global _client
    if _client is None:
        creds_path = Path(GOOGLE_SHEETS_CREDENTIALS_FILE)
        if not creds_path.is_absolute():
            creds_path = BASE_DIR / creds_path

        if not creds_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")

        credentials = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
        _client = gspread.authorize(credentials)
        logger.info("Google Sheets client authorized")

    return _client


def get_spreadsheet() -> gspread.Spreadsheet:
    """Возвращает объект таблицы."""
    global _spreadsheet
    if _spreadsheet is None:
        if not GOOGLE_SHEETS_SPREADSHEET_ID:
            raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID not set")

        client = get_client()
        _spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
        logger.info(f"Opened spreadsheet: {_spreadsheet.title}")

    return _spreadsheet


def add_transaction(transaction: Transaction) -> int:
    """Добавляет транзакцию в таблицу Transactions."""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet("Transactions")

    all_values = worksheet.get_all_values()
    next_tx_id = len(all_values)

    transaction.tx_id = next_tx_id

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    year = now.year
    month = now.month
    date_added = now.strftime("%Y-%m-%d %H:%M")

    tx_type = "income" if transaction.type == TransactionType.INCOME else "expense"

    prev_balance = get_last_balance()
    if tx_type == "income":
        new_balance = prev_balance + transaction.amount
    else:
        new_balance = prev_balance - transaction.amount

    row = [
        date_str,
        time_str,
        next_tx_id,
        tx_type,
        transaction.category,
        transaction.description,
        transaction.amount,
        new_balance,
        year,
        month,
        "Да",
        date_added,
    ]

    worksheet.append_row(row, value_input_option="USER_ENTERED")

    update_balance_sheet(new_balance)

    logger.info(f"Added transaction #{next_tx_id}: {transaction.description}")
    return next_tx_id


def get_last_balance() -> float:
    """Возвращает последний баланс из транзакций."""
    try:
        spreadsheet = get_spreadsheet()
        worksheet = spreadsheet.worksheet("Transactions")

        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            balance_sheet = spreadsheet.worksheet("Balance")
            value = balance_sheet.acell("B2").value
            return float(value) if value else 0

        last_row = all_values[-1]
        if len(last_row) >= 8 and last_row[7]:
            return float(last_row[7])

        return 0
    except Exception as e:
        logger.error(f"Failed to get last balance: {e}")
        return 0


def update_balance_sheet(new_balance: float):
    """Обновляет текущий баланс на листе Balance."""
    try:
        spreadsheet = get_spreadsheet()
        balance_sheet = spreadsheet.worksheet("Balance")
        balance_sheet.update_acell("B2", new_balance)
    except Exception as e:
        logger.error(f"Failed to update balance sheet: {e}")


def get_transactions(limit: int = 10, offset: int = 0) -> list[dict]:
    """Возвращает список последних транзакций."""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet("Transactions")

    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return []

    headers = all_values[0]
    data = all_values[1:]

    data.reverse()

    result = []
    for row in data[offset:offset + limit]:
        tx = dict(zip(headers, row))
        result.append(tx)

    return result


def get_month_summary(year: int, month: int) -> dict:
    """Возвращает сводку за месяц."""
    return calculate_month_summary(year, month)


def calculate_month_summary(year: int, month: int) -> dict:
    """Вычисляет сводку за месяц из транзакций."""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet("Transactions")

    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return {"income": 0, "expenses": 0, "balance": 0, "by_category": {}}

    income = 0
    expenses = 0
    by_category = {}

    for row in all_values[1:]:
        try:
            tx_year = int(row[8]) if len(row) > 8 and row[8] else 0
            tx_month = int(row[9]) if len(row) > 9 and row[9] else 0

            if tx_year != year or tx_month != month:
                continue

            amount = float(row[6]) if len(row) > 6 and row[6] else 0
            tx_type = row[3] if len(row) > 3 else ""
            category = row[4] if len(row) > 4 else ""

            if tx_type == "income":
                income += amount
            else:
                expenses += amount
                by_category[category] = by_category.get(category, 0) + amount

        except (ValueError, IndexError):
            continue

    return {
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
        "by_category": by_category,
    }


def get_period_summary(start_date: datetime, end_date: datetime) -> dict:
    """Возвращает сводку за произвольный период."""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet("Transactions")

    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return {"income": 0, "expenses": 0, "balance": 0, "by_category": {}, "transactions": []}

    income = 0
    expenses = 0
    by_category = {}
    transactions = []

    for row in all_values[1:]:
        try:
            date_str = row[0] if row[0] else ""
            if not date_str:
                continue

            tx_date = datetime.strptime(date_str, "%Y-%m-%d")

            if tx_date < start_date or tx_date > end_date:
                continue

            amount = float(row[6]) if len(row) > 6 and row[6] else 0
            tx_type = row[3] if len(row) > 3 else ""
            category = row[4] if len(row) > 4 else ""
            description = row[5] if len(row) > 5 else ""

            if tx_type == "income":
                income += amount
            else:
                expenses += amount
                by_category[category] = by_category.get(category, 0) + amount

            transactions.append({
                "date": date_str,
                "type": tx_type,
                "category": category,
                "description": description,
                "amount": amount,
            })

        except (ValueError, IndexError):
            continue

    return {
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
        "by_category": by_category,
        "transactions": transactions,
    }


def get_month_transactions_markdown(year: int, month: int, limit: int = 100) -> str:
    """Возвращает транзакции за месяц в Markdown-KV формате для AI."""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet("Transactions")

    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return "Нет транзакций"

    transactions = []
    for row in all_values[1:]:
        try:
            tx_year = int(row[8]) if len(row) > 8 and row[8] else 0
            tx_month = int(row[9]) if len(row) > 9 and row[9] else 0

            if tx_year != year or tx_month != month:
                continue

            transactions.append({
                "date": row[0],
                "type": "расход" if row[3] == "expense" else "доход",
                "category": row[4],
                "description": row[5],
                "amount": row[6],
            })

            if len(transactions) >= limit:
                break

        except (ValueError, IndexError):
            continue

    if not transactions:
        return "Нет транзакций за этот период"

    result = []
    for i, tx in enumerate(transactions, 1):
        result.append(f"""Транзакция {i}:
дата: {tx['date']}
тип: {tx['type']}
категория: {tx['category']}
описание: {tx['description']}
сумма: {tx['amount']}""")

    return "\n---\n".join(result)


def get_period_transactions_markdown(start_date: datetime, end_date: datetime, limit: int = 100) -> str:
    """Возвращает транзакции за период в Markdown-KV формате для AI."""
    data = get_period_summary(start_date, end_date)
    transactions = data.get("transactions", [])[:limit]

    if not transactions:
        return "Нет транзакций за этот период"

    result = []
    for i, tx in enumerate(transactions, 1):
        tx_type = "расход" if tx["type"] == "expense" else "доход"
        result.append(f"""Транзакция {i}:
дата: {tx['date']}
тип: {tx_type}
категория: {tx['category']}
описание: {tx['description']}
сумма: {tx['amount']}""")

    return "\n---\n".join(result)


def get_current_balance() -> float:
    """Возвращает текущий баланс."""
    try:
        spreadsheet = get_spreadsheet()
        balance_sheet = spreadsheet.worksheet("Balance")
        value = balance_sheet.acell("B2").value
        return float(value) if value else 0
    except Exception as e:
        logger.error(f"Failed to get balance: {e}")
        return 0


def get_expenses_by_category(year: int = None, month: int = None) -> dict:
    """Возвращает расходы по категориям за период."""
    if year and month:
        summary = get_month_summary(year, month)
    else:
        now = datetime.now()
        summary = get_month_summary(now.year, now.month)

    return summary.get("by_category", {})


def update_monthly_summary(year: int, month: int):
    """Обновляет сводку за месяц в Monthly_Summary."""
    try:
        spreadsheet = get_spreadsheet()
        monthly_sheet = spreadsheet.worksheet("Monthly_Summary")

        summary = calculate_month_summary(year, month)

        month_key = f"{year}-{month:02d}"

        all_values = monthly_sheet.get_all_values()
        row_index = None
        for i, row in enumerate(all_values[1:], start=2):
            if row[0] == month_key:
                row_index = i
                break

        categories = ["Еда", "Жильё и быт", "Такси", "Здоровье", "Развлечения", "Одежда", "Подписки", "Подарки", "Прочее"]
        cat_values = [summary["by_category"].get(cat, 0) for cat in categories]

        row_data = [
            month_key,
            summary["income"],
            summary["expenses"],
            summary["balance"],
        ] + cat_values

        if row_index:
            monthly_sheet.update(values=[row_data], range_name=f"A{row_index}:M{row_index}")
        else:
            monthly_sheet.append_row(row_data, value_input_option="USER_ENTERED")

        logger.info(f"Updated Monthly_Summary for {month_key}")

    except Exception as e:
        logger.error(f"Failed to update monthly summary: {e}")


def create_backup() -> str:
    """Создаёт резервную копию таблицы."""
    spreadsheet = get_spreadsheet()
    backup_name = f"Finance_Backup_{datetime.now().strftime('%Y%m%d_%H%M')}"

    client = get_client()
    client.copy(spreadsheet.id, backup_name)

    logger.info(f"Created backup: {backup_name}")
    return backup_name


def export_to_csv() -> str:
    """Экспортирует транзакции в CSV формат."""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet("Transactions")

    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return "Date,Time,TxID,Type,Category,Description,Amount\n"

    lines = []
    headers = all_values[0][:7]
    lines.append(",".join(headers))

    for row in all_values[1:]:
        line = ",".join([str(cell).replace(",", ";") for cell in row[:7]])
        lines.append(line)

    return "\n".join(lines)
