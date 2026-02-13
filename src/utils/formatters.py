from datetime import datetime

MONTHS_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}

MONTHS_RU_SHORT = {
    1: "Янв",
    2: "Фев",
    3: "Мар",
    4: "Апр",
    5: "Май",
    6: "Июн",
    7: "Июл",
    8: "Авг",
    9: "Сен",
    10: "Окт",
    11: "Ноя",
    12: "Дек",
}


def month_name(month: int) -> str:
    """Возвращает название месяца на русском."""
    return MONTHS_RU.get(month, str(month))


def month_name_short(month: int) -> str:
    """Возвращает сокращенное название месяца."""
    return MONTHS_RU_SHORT.get(month, str(month))


def format_amount(amount: float, with_sign: bool = False) -> str:
    """Форматирует сумму для отображения."""
    formatted = f"{amount:,.0f}".replace(",", " ")
    if with_sign and amount > 0:
        return f"+{formatted}"
    return formatted


def format_transaction_list(transactions: list[dict]) -> str:
    """Форматирует список транзакций для отображения."""
    if not transactions:
        return "Пока транзакций нет."

    lines = []
    for tx in transactions:
        date = tx.get("Дата", tx.get("Date", ""))
        category = tx.get("Категория", tx.get("Category", ""))
        amount = tx.get("Сумма", tx.get("Amount", "0"))
        tx_type = tx.get("Тип", tx.get("Type", "expense"))

        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_str = date_obj.strftime("%d.%m")
        except ValueError:
            date_str = date

        is_income = tx_type in ("income", "доход")
        sign = "+" if is_income else "−"

        try:
            amount_clean = str(amount).replace("\xa0", "").replace(" ", "")
            amount_str = f"{float(amount_clean):,.0f}".replace(",", " ")
        except ValueError:
            amount_str = amount

        lines.append(f"{date_str}  {category}  {sign}{amount_str} ₽")

    return "\n".join(lines)


def format_report_header(month: int, year: int) -> str:
    """Форматирует заголовок отчёта."""
    return f"ФИНАНСОВЫЙ ОТЧЁТ ЗА {month_name(month).upper()} {year}"


def calculate_change_percent(current: float, previous: float) -> str:
    """Вычисляет процент изменения."""
    if previous == 0:
        return "—"
    change = ((current - previous) / previous) * 100
    return f"{change:+.1f}%"


def format_summary(summary: dict, previous_summary: dict = None) -> str:
    """Форматирует сводку для пользователя."""
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    balance = income - expenses

    lines = [
        f"ДОХОДЫ: {format_amount(income)} руб.",
        f"РАСХОДЫ: {format_amount(expenses)} руб.",
        f"БАЛАНС: {format_amount(balance, with_sign=True)} руб.",
    ]

    if previous_summary:
        prev_income = previous_summary.get("income", 0)
        prev_expenses = previous_summary.get("expenses", 0)

        income_change = calculate_change_percent(income, prev_income)
        expenses_change = calculate_change_percent(expenses, prev_expenses)

        lines[0] += f" ({income_change})"
        lines[1] += f" ({expenses_change})"

    lines.append("")
    lines.append("РАСХОДЫ ПО КАТЕГОРИЯМ:")

    for cat_name, amount in summary.get("by_category", {}).items():
        prev_amount = 0
        if previous_summary:
            prev_amount = previous_summary.get("by_category", {}).get(cat_name, 0)

        change_str = ""
        if previous_summary and prev_amount > 0:
            change_str = f" ({calculate_change_percent(amount, prev_amount)})"

        lines.append(f"- {cat_name}: {format_amount(amount)} руб.{change_str}")

    return "\n".join(lines)
