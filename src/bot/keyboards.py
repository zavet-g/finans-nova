from telegram import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from src.models.category import EXPENSE_CATEGORIES, INCOME_CATEGORY, TransactionType

STYLE_PRIMARY = "primary"
STYLE_SUCCESS = "success"
STYLE_DANGER = "danger"


def _styled(text: str, callback_data: str, style: str = None, **kwargs) -> InlineKeyboardButton:
    """Создаёт InlineKeyboardButton с опциональной стилизацией (Bot API 9.4)."""
    api_kwargs = {}
    if style:
        api_kwargs["style"] = style
    return InlineKeyboardButton(
        text, callback_data=callback_data, api_kwargs=api_kwargs or None, **kwargs
    )


def start_reply_keyboard() -> ReplyKeyboardMarkup:
    """ReplyKeyboard с кнопкой главного меню."""
    return ReplyKeyboardMarkup([["Главное меню"]], resize_keyboard=True)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    buttons = [
        [InlineKeyboardButton("📋 Последние транзакции", callback_data="menu:transactions")],
        [InlineKeyboardButton("📊 Аналитика", callback_data="menu:analytics")],
        [InlineKeyboardButton("📈 Графики", callback_data="menu:charts")],
        [InlineKeyboardButton("💾 Бэкап и экспорт", callback_data="menu:backup")],
        [InlineKeyboardButton("🔧 Состояние бота", callback_data="menu:health")],
        [InlineKeyboardButton("📎 Открыть таблицу", callback_data="menu:sheets")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu:help")],
    ]
    return InlineKeyboardMarkup(buttons)


def confirm_transaction_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения транзакции."""
    buttons = [
        [
            _styled("✅ Добавить", "tx:confirm", STYLE_SUCCESS),
            _styled("✏️ Изменить", "tx:edit"),
        ],
        [_styled("❌ Отмена", "tx:cancel", STYLE_DANGER)],
    ]
    return InlineKeyboardMarkup(buttons)


def edit_transaction_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура редактирования транзакции."""
    buttons = [
        [
            _styled("📁 Категория", "edit:category"),
            _styled("💰 Сумма", "edit:amount"),
        ],
        [
            _styled("📝 Описание", "edit:description"),
            _styled("🔄 Тип", "edit:type"),
        ],
        [_styled("◀️ Назад", "edit:back")],
    ]
    return InlineKeyboardMarkup(buttons)


def categories_keyboard(tx_type: TransactionType) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории."""
    if tx_type == TransactionType.INCOME:
        buttons = [
            [
                InlineKeyboardButton(
                    INCOME_CATEGORY.name, callback_data=f"cat:{INCOME_CATEGORY.code}"
                )
            ]
        ]
    else:
        buttons = [
            [InlineKeyboardButton(cat.name, callback_data=f"cat:{cat.code}")]
            for cat in EXPENSE_CATEGORIES
        ]
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="cat:back")])
    return InlineKeyboardMarkup(buttons)


def analytics_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода для аналитики."""
    buttons = [
        [InlineKeyboardButton("📅 Последние 2 недели", callback_data="period:2w")],
        [InlineKeyboardButton("📅 Последний месяц", callback_data="period:1m")],
        [InlineKeyboardButton("📅 Последние 3 месяца", callback_data="period:3m")],
        [InlineKeyboardButton("📅 Последние 6 месяцев", callback_data="period:6m")],
        [InlineKeyboardButton("📅 Последний год", callback_data="period:1y")],
        [InlineKeyboardButton("📅 Свой период", callback_data="period:custom")],
        [InlineKeyboardButton("◀️ Назад", callback_data="period:back")],
    ]
    return InlineKeyboardMarkup(buttons)


def back_keyboard(callback_data: str = "back") -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой Назад."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=callback_data)]])


def transactions_list_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для списка транзакций."""
    return InlineKeyboardMarkup(
        [
            [_styled("🗑 Удалить транзакцию", "transactions:delete", STYLE_DANGER)],
            [InlineKeyboardButton("◀️ Назад", callback_data="transactions:back")],
        ]
    )


def delete_select_keyboard(transactions: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора транзакции для удаления."""
    from datetime import datetime

    buttons = []
    for tx in transactions:
        row_num = tx.get("_row_number", 0)
        date = tx.get("Дата", "")
        category = tx.get("Категория", "")
        amount = tx.get("Сумма", "0")
        tx_type = tx.get("Тип", "")

        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            date_str = date_obj.strftime("%d.%m")
        except ValueError:
            date_str = date

        sign = "+" if tx_type == "доход" else "-"

        try:
            amount_str = f"{float(str(amount).replace(' ', '')):,.0f}".replace(",", " ")
        except ValueError:
            amount_str = amount

        label = f"{date_str}  {category}  {sign}{amount_str}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"del:{row_num}")])

    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="del:back")])
    return InlineKeyboardMarkup(buttons)


def confirm_delete_keyboard(row_number: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления."""
    buttons = [
        [_styled("🗑 Удалить", f"del:confirm:{row_number}", STYLE_DANGER)],
        [InlineKeyboardButton("◀️ Отмена", callback_data="del:back")],
    ]
    return InlineKeyboardMarkup(buttons)


def backup_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела бэкапов."""
    buttons = [
        [_styled("📥 Скачать CSV", "backup:csv", STYLE_PRIMARY)],
        [_styled("💾 Сделать бэкап сейчас", "backup:now")],
        [_styled("◀️ Назад", "backup:back")],
    ]
    return InlineKeyboardMarkup(buttons)


def health_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура состояния бота."""
    buttons = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="health:refresh")],
        [InlineKeyboardButton("◀️ Назад", callback_data="health:back")],
    ]
    return InlineKeyboardMarkup(buttons)


def charts_menu_keyboard() -> InlineKeyboardMarkup:
    """Подменю раздела графиков."""
    buttons = [
        [InlineKeyboardButton("📊 График за текущий месяц", callback_data="charts:current_month")],
        [InlineKeyboardButton("📈 График за год", callback_data="charts:yearly")],
        [InlineKeyboardButton("◀️ Назад", callback_data="charts:back")],
    ]
    return InlineKeyboardMarkup(buttons)


def yearly_charts_keyboard() -> InlineKeyboardMarkup:
    """Подменю годовых графиков."""
    buttons = [
        [InlineKeyboardButton("📈 Доходы по месяцам", callback_data="charts:yearly_income")],
        [InlineKeyboardButton("📉 Расходы по месяцам", callback_data="charts:yearly_expense")],
        [InlineKeyboardButton("◀️ Назад", callback_data="charts:menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def analytics_result_keyboard(summary_text: str) -> InlineKeyboardMarkup:
    """Клавиатура результата аналитики с кнопкой копирования итогов."""
    buttons = [
        [
            InlineKeyboardButton(
                "📋 Скопировать итоги", copy_text=CopyTextButton(text=summary_text[:256])
            )
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="analytics:back")],
    ]
    return InlineKeyboardMarkup(buttons)
