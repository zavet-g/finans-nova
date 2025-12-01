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

TRANSACTIONS_HEADERS = ["Дата", "Время", "Тип", "Категория", "Описание", "Сумма", "Баланс"]


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


def init_spreadsheet():
    """Инициализирует структуру таблицы: Транзакции + Сводка."""
    spreadsheet = get_spreadsheet()

    _init_transactions_sheet(spreadsheet)
    _init_summary_sheet(spreadsheet)

    logger.info("Spreadsheet initialized")


def _get_or_create_sheet(spreadsheet: gspread.Spreadsheet, name: str, rows: int = 1000, cols: int = 20) -> gspread.Worksheet:
    """Получает или создаёт лист."""
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)


def _init_transactions_sheet(spreadsheet: gspread.Spreadsheet):
    """Инициализирует лист Транзакции."""
    sheet = _get_or_create_sheet(spreadsheet, "Транзакции", rows=10000, cols=7)

    existing = sheet.get_all_values()
    if len(existing) == 0:
        sheet.update(values=[TRANSACTIONS_HEADERS], range_name="A1:G1", value_input_option="USER_ENTERED")

        sheet.format("A1:G1", {
            "backgroundColor": {"red": 0.35, "green": 0.45, "blue": 0.55},
            "textFormat": {
                "bold": True,
                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                "fontSize": 10
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE"
        })

        sheet.set_basic_filter()
        sheet.freeze(rows=1)

        sheet.columns_auto_resize(0, 7)

        logger.info("Лист Транзакции создан")


def _init_summary_sheet(spreadsheet: gspread.Spreadsheet):
    """Инициализирует лист Сводка с формулами."""
    sheet = _get_or_create_sheet(spreadsheet, "Сводка", rows=30, cols=4)

    existing = sheet.get_all_values()
    if len(existing) <= 1:
        categories = ["Еда", "Жильё и быт", "Такси", "Здоровье", "Развлечения", "Одежда", "Подписки", "Подарки", "Дом", "Прочее"]

        month_start = 'TEXT(EOMONTH(TODAY();-1)+1;"YYYY-MM-DD")'
        month_end = 'TEXT(EOMONTH(TODAY();0);"YYYY-MM-DD")'

        summary_data = [
            ["НАСТРОЙКИ", ""],
            ["Начальный баланс", 0],
            ["", ""],
            ["БАЛАНС", ""],
            ["Текущий баланс", '=IF(COUNTA(Транзакции!G:G)>1; INDEX(Транзакции!G:G; COUNTA(Транзакции!G:G)); B2)'],
            ["", ""],
            ["ТЕКУЩИЙ МЕСЯЦ", ""],
            ["Доходы", f'=SUMIFS(Транзакции!F:F; Транзакции!C:C; "доход"; Транзакции!A:A; ">="&{month_start}; Транзакции!A:A; "<="&{month_end})'],
            ["Расходы", f'=SUMIFS(Транзакции!F:F; Транзакции!C:C; "расход"; Транзакции!A:A; ">="&{month_start}; Транзакции!A:A; "<="&{month_end})'],
            ["Баланс месяца", "=B8-B9"],
            ["", ""],
            ["РАСХОДЫ ПО КАТЕГОРИЯМ", "Сумма"],
        ]

        row_num = 13
        for cat in categories:
            formula = f'=SUMIFS(Транзакции!F:F; Транзакции!C:C; "расход"; Транзакции!D:D; "{cat}"; Транзакции!A:A; ">="&{month_start}; Транзакции!A:A; "<="&{month_end})'
            summary_data.append([cat, formula])
            row_num += 1

        summary_data.append(["", ""])
        summary_data.append(["ИТОГО расходы", f"=SUM(B13:B{row_num-1})"])

        sheet.update(values=summary_data, range_name=f"A1:B{len(summary_data)}", value_input_option="USER_ENTERED")

        dark_header = {
            "backgroundColor": {"red": 0.35, "green": 0.45, "blue": 0.55},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}, "fontSize": 10},
            "borders": _get_borders()
        }

        light_header = {
            "backgroundColor": {"red": 0.93, "green": 0.93, "blue": 0.93},
            "textFormat": {"bold": True, "fontSize": 10},
            "borders": _get_borders()
        }

        green_cell = {
            "backgroundColor": {"red": 0.93, "green": 0.97, "blue": 0.93},
            "borders": _get_borders()
        }

        warm_cell = {
            "backgroundColor": {"red": 0.97, "green": 0.95, "blue": 0.93},
            "borders": _get_borders()
        }

        blue_cell = {
            "backgroundColor": {"red": 0.93, "green": 0.95, "blue": 0.97},
            "borders": _get_borders()
        }

        normal_cell = {
            "backgroundColor": {"red": 1, "green": 1, "blue": 1},
            "borders": _get_borders()
        }

        sheet.format("A1:B1", dark_header)
        sheet.format("A2:B2", normal_cell)

        sheet.format("A4:B4", dark_header)
        sheet.format("A5:B5", blue_cell)

        sheet.format("A7:B7", dark_header)
        sheet.format("A8:B8", green_cell)
        sheet.format("A9:B9", warm_cell)
        sheet.format("A10:B10", blue_cell)

        sheet.format("A12:B12", light_header)

        for i in range(13, row_num):
            sheet.format(f"A{i}:B{i}", normal_cell)

        sheet.format(f"A{row_num+1}:B{row_num+1}", {
            "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
            "textFormat": {"bold": True},
            "borders": _get_borders()
        })

        sheet.format("B2:B30", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}})

        sheet.columns_auto_resize(0, 2)

        logger.info("Лист Сводка создан")


def _get_borders():
    """Возвращает стиль границ для ячеек."""
    border_style = {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}}
    return {
        "top": border_style,
        "bottom": border_style,
        "left": border_style,
        "right": border_style
    }


def add_transaction(transaction: Transaction) -> int:
    """Добавляет транзакцию в лист Транзакции."""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet("Транзакции")

    all_values = worksheet.get_all_values()
    row_num = len(all_values) + 1

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    tx_type = "доход" if transaction.type == TransactionType.INCOME else "расход"

    if row_num == 2:
        balance_formula = f'=Сводка!$B$2 + IF(C{row_num}="доход"; F{row_num}; -F{row_num})'
    else:
        balance_formula = f'=IF(F{row_num}=""; ""; G{row_num-1} + IF(C{row_num}="доход"; F{row_num}; -F{row_num}))'

    row = [
        date_str,
        time_str,
        tx_type,
        transaction.category,
        transaction.description,
        transaction.amount,
        balance_formula,
    ]

    worksheet.append_row(row, value_input_option="USER_ENTERED")

    transaction.tx_id = row_num - 1

    logger.info(f"Транзакция #{transaction.tx_id}: {transaction.description}")
    return transaction.tx_id


def get_last_balance() -> float:
    """Возвращает последний баланс из транзакций."""
    try:
        spreadsheet = get_spreadsheet()
        worksheet = spreadsheet.worksheet("Транзакции")

        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            summary = spreadsheet.worksheet("Сводка")
            value = summary.acell("B2").value
            return float(value) if value else 0

        last_row = all_values[-1]
        if len(last_row) >= 7 and last_row[6]:
            try:
                return float(last_row[6])
            except ValueError:
                return 0

        return 0
    except Exception as e:
        logger.error(f"Ошибка получения баланса: {e}")
        return 0


def get_current_balance() -> float:
    """Возвращает текущий баланс."""
    return get_last_balance()


def get_transactions(limit: int = 10, offset: int = 0) -> list[dict]:
    """Возвращает список последних транзакций."""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet("Транзакции")

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
    worksheet = spreadsheet.worksheet("Транзакции")

    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return {"income": 0, "expenses": 0, "balance": 0, "by_category": {}}

    income = 0
    expenses = 0
    by_category = {}

    month_str = f"{year}-{month:02d}"

    for row in all_values[1:]:
        try:
            date_str = row[0] if row[0] else ""
            if not date_str.startswith(month_str):
                continue

            amount = float(row[5]) if len(row) > 5 and row[5] else 0
            tx_type = row[2] if len(row) > 2 else ""
            category = row[3] if len(row) > 3 else ""

            if tx_type == "доход":
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
    worksheet = spreadsheet.worksheet("Транзакции")

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

            amount = float(row[5]) if len(row) > 5 and row[5] else 0
            tx_type = row[2] if len(row) > 2 else ""
            category = row[3] if len(row) > 3 else ""
            description = row[4] if len(row) > 4 else ""

            if tx_type == "доход":
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
    worksheet = spreadsheet.worksheet("Транзакции")

    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return "Нет транзакций"

    transactions = []
    month_str = f"{year}-{month:02d}"

    for row in all_values[1:]:
        try:
            date_str = row[0] if row[0] else ""
            if not date_str.startswith(month_str):
                continue

            transactions.append({
                "date": row[0],
                "type": row[2],
                "category": row[3],
                "description": row[4],
                "amount": row[5],
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
        result.append(f"""Транзакция {i}:
дата: {tx['date']}
тип: {tx['type']}
категория: {tx['category']}
описание: {tx['description']}
сумма: {tx['amount']}""")

    return "\n---\n".join(result)


def get_expenses_by_category(year: int = None, month: int = None) -> dict:
    """Возвращает расходы по категориям за период."""
    if year and month:
        summary = get_month_summary(year, month)
    else:
        now = datetime.now()
        summary = get_month_summary(now.year, now.month)

    return summary.get("by_category", {})




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
    worksheet = spreadsheet.worksheet("Транзакции")

    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return "Дата,Время,Тип,Категория,Описание,Сумма,Баланс\n"

    lines = []
    headers = all_values[0]
    lines.append(",".join(headers))

    for row in all_values[1:]:
        line = ",".join([str(cell).replace(",", ";") for cell in row])
        lines.append(line)

    return "\n".join(lines)


def set_initial_balance(balance: float):
    """Устанавливает начальный баланс в Сводке."""
    try:
        spreadsheet = get_spreadsheet()
        summary = spreadsheet.worksheet("Сводка")
        summary.update_acell("B2", balance)
        logger.info(f"Начальный баланс: {balance}")
    except Exception as e:
        logger.error(f"Ошибка установки баланса: {e}")


def reset_spreadsheet():
    """Удаляет все листы и пересоздаёт структуру с нуля."""
    spreadsheet = get_spreadsheet()

    sheets_to_delete = ["Транзакции", "Сводка", "Графики", "Transactions", "Categories", "Dashboard", "Monthly", "Settings"]
    for sheet_name in sheets_to_delete:
        try:
            sheet = spreadsheet.worksheet(sheet_name)
            spreadsheet.del_worksheet(sheet)
            logger.info(f"Удалён лист: {sheet_name}")
        except gspread.WorksheetNotFound:
            pass

    init_spreadsheet()
    logger.info("Таблица пересоздана")
