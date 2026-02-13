import sys
from pathlib import Path
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.transaction import Transaction
from src.models.category import TransactionType


@pytest.fixture
def sample_transaction():
    return Transaction(
        type=TransactionType.EXPENSE,
        category="Еда",
        description="Обед в столовой",
        amount=500.0,
        date=datetime(2025, 1, 15, 12, 30),
    )


@pytest.fixture
def sample_income_transaction():
    return Transaction(
        type=TransactionType.INCOME,
        category="Доход",
        description="Зарплата за январь",
        amount=100000.0,
        date=datetime(2025, 1, 10, 9, 0),
    )


@pytest.fixture
def sample_summary():
    return {
        "income": 100000,
        "expenses": 45000,
        "balance": 55000,
        "by_category": {
            "Еда": 15000,
            "Такси": 8000,
            "Развлечения": 12000,
            "Подписки": 5000,
            "Прочее": 5000,
        },
    }


@pytest.fixture
def sample_previous_summary():
    return {
        "income": 90000,
        "expenses": 40000,
        "balance": 50000,
        "by_category": {
            "Еда": 12000,
            "Такси": 10000,
            "Развлечения": 8000,
            "Подписки": 5000,
            "Прочее": 5000,
        },
    }


@pytest.fixture
def sample_sheets_rows():
    return [
        ["Дата", "Время", "Тип", "Категория", "Описание", "Сумма", "Баланс"],
        ["2025-01-05", "10:00", "расход", "Еда", "Продукты", "3000", "97000"],
        ["2025-01-06", "12:00", "расход", "Такси", "До работы", "500", "96500"],
        ["2025-01-07", "09:00", "доход", "Доход", "Зарплата", "100000", "196500"],
        ["2025-01-10", "18:00", "расход", "Развлечения", "Кино", "800", "195700"],
        ["2025-01-11", "14:00", "расход", "Еда", "Обед", "600", "195100"],
        ["2025-01-15", "20:00", "расход", "Еда", "Ужин в ресторане", "5000", "190100"],
        ["2025-01-20", "11:00", "расход", "Здоровье", "Аптека", "1200", "188900"],
        ["2025-02-01", "10:00", "расход", "Еда", "Продукты", "2500", "186400"],
        ["2025-02-05", "09:00", "доход", "Доход", "Фриланс", "30000", "216400"],
    ]


@pytest.fixture
def sample_transactions_list():
    return [
        {"date": "2025-01-05", "type": "расход", "category": "Еда", "description": "Продукты", "amount": 3000},
        {"date": "2025-01-06", "type": "расход", "category": "Такси", "description": "До работы", "amount": 500},
        {"date": "2025-01-07", "type": "доход", "category": "Доход", "description": "Зарплата", "amount": 100000},
        {"date": "2025-01-10", "type": "расход", "category": "Развлечения", "description": "Кино", "amount": 800},
        {"date": "2025-01-11", "type": "расход", "category": "Еда", "description": "Обед", "amount": 600},
        {"date": "2025-01-15", "type": "расход", "category": "Еда", "description": "Ужин в ресторане", "amount": 5000},
        {"date": "2025-01-20", "type": "расход", "category": "Здоровье", "description": "Аптека", "amount": 1200},
    ]
