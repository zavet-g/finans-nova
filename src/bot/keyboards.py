from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from src.models.category import EXPENSE_CATEGORIES, INCOME_CATEGORY, TransactionType


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
            InlineKeyboardButton("✅ Добавить", callback_data="tx:confirm"),
            InlineKeyboardButton("✏️ Изменить", callback_data="tx:edit"),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data="tx:cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def edit_transaction_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура редактирования транзакции."""
    buttons = [
        [
            InlineKeyboardButton("📁 Категория", callback_data="edit:category"),
            InlineKeyboardButton("💰 Сумма", callback_data="edit:amount"),
        ],
        [
            InlineKeyboardButton("📝 Описание", callback_data="edit:description"),
            InlineKeyboardButton("🔄 Тип", callback_data="edit:type"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="edit:back")],
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
        [[InlineKeyboardButton("◀️ Назад", callback_data="transactions:back")]]
    )


def backup_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела бэкапов."""
    buttons = [
        [InlineKeyboardButton("📥 Скачать CSV", callback_data="backup:csv")],
        [InlineKeyboardButton("💾 Сделать бэкап сейчас", callback_data="backup:now")],
        [InlineKeyboardButton("◀️ Назад", callback_data="backup:back")],
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
