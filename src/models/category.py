from enum import Enum
from typing import NamedTuple


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Category(NamedTuple):
    code: str
    name: str
    type: TransactionType
    keywords: list[str] = []


EXPENSE_CATEGORIES = [
    Category(
        "food",
        "Еда",
        TransactionType.EXPENSE,
        ["продукты", "доставка", "ресторан", "кафе", "магазин", "пятёрочка"],
    ),
    Category(
        "housing",
        "Жильё и быт",
        TransactionType.EXPENSE,
        ["аренда", "жкх", "коммуналка", "интернет", "мебель", "ремонт"],
    ),
    Category(
        "taxi", "Такси", TransactionType.EXPENSE, ["такси", "uber", "яндекс такси", "каршеринг"]
    ),
    Category(
        "health",
        "Здоровье",
        TransactionType.EXPENSE,
        ["аптека", "врач", "клиника", "лекарства", "анализы"],
    ),
    Category(
        "entertainment", "Развлечения", TransactionType.EXPENSE, ["кино", "игры", "концерт", "бар"]
    ),
    Category("clothes", "Одежда", TransactionType.EXPENSE, ["одежда", "обувь"]),
    Category(
        "subscriptions",
        "Подписки",
        TransactionType.EXPENSE,
        ["подписка", "youtube premium", "icloud", "netflix", "spotify"],
    ),
    Category("gifts", "Подарки", TransactionType.EXPENSE, ["подарок", "день рождения"]),
    Category("other", "Прочее", TransactionType.EXPENSE, []),
]

INCOME_CATEGORY = Category(
    "income", "Доход", TransactionType.INCOME, ["зарплата", "доход", "перевод"]
)

ALL_CATEGORIES = EXPENSE_CATEGORIES + [INCOME_CATEGORY]


def get_category_by_code(code: str) -> Category | None:
    for cat in ALL_CATEGORIES:
        if cat.code == code:
            return cat
    return None


def get_categories_by_type(tx_type: TransactionType) -> list[Category]:
    return [cat for cat in ALL_CATEGORIES if cat.type == tx_type]
