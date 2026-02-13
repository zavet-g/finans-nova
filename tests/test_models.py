from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.category import (
    ALL_CATEGORIES,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORY,
    TransactionType,
    get_categories_by_type,
    get_category_by_code,
)
from src.models.transaction import Transaction


class TestTransaction:
    def test_create_valid_expense(self):
        tx = Transaction(
            type=TransactionType.EXPENSE,
            category="Еда",
            description="Обед",
            amount=500,
        )
        assert tx.type == TransactionType.EXPENSE
        assert tx.amount == 500
        assert tx.confirmed is False
        assert tx.tx_id is None

    def test_create_valid_income(self):
        tx = Transaction(
            type=TransactionType.INCOME,
            category="Доход",
            description="Зарплата",
            amount=100000,
        )
        assert tx.type == TransactionType.INCOME

    def test_zero_amount_raises(self):
        with pytest.raises(ValidationError):
            Transaction(
                type=TransactionType.EXPENSE,
                category="Еда",
                description="Обед",
                amount=0,
            )

    def test_negative_amount_raises(self):
        with pytest.raises(ValidationError):
            Transaction(
                type=TransactionType.EXPENSE,
                category="Еда",
                description="Обед",
                amount=-100,
            )

    def test_default_date_is_set(self):
        tx = Transaction(
            type=TransactionType.EXPENSE,
            category="Еда",
            description="Обед",
            amount=500,
        )
        assert isinstance(tx.date, datetime)


class TestToSheetsRow:
    def test_row_length(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert len(row) == 12

    def test_date_format(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert row[0] == "2025-01-15"

    def test_time_format(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert row[1] == "12:30"

    def test_tx_id_none_becomes_empty(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert row[2] == ""

    def test_tx_id_present(self, sample_transaction):
        sample_transaction.tx_id = 42
        row = sample_transaction.to_sheets_row()
        assert row[2] == 42

    def test_type_value(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert row[3] == "expense"

    def test_category(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert row[4] == "Еда"

    def test_description(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert row[5] == "Обед в столовой"

    def test_amount(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert row[6] == 500.0

    def test_year_and_month(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert row[8] == 2025
        assert row[9] == 1

    def test_confirmed_field(self, sample_transaction):
        row = sample_transaction.to_sheets_row()
        assert row[10] == "Нет"

        sample_transaction.confirmed = True
        row = sample_transaction.to_sheets_row()
        assert row[10] == "Да"


class TestToSheetsRowIncome:
    def test_income_type_value(self, sample_income_transaction):
        row = sample_income_transaction.to_sheets_row()
        assert row[3] == "income"

    def test_income_amount(self, sample_income_transaction):
        row = sample_income_transaction.to_sheets_row()
        assert row[6] == 100000.0

    def test_income_row_length(self, sample_income_transaction):
        row = sample_income_transaction.to_sheets_row()
        assert len(row) == 12


class TestFormatForUser:
    def test_expense_format(self, sample_transaction):
        result = sample_transaction.format_for_user()
        assert "Обед в столовой" in result
        assert "Еда" in result
        assert "-500" in result

    def test_income_format(self, sample_income_transaction):
        result = sample_income_transaction.format_for_user()
        assert "Зарплата за январь" in result
        assert "+100" in result

    def test_expense_has_minus_sign(self, sample_transaction):
        result = sample_transaction.format_for_user()
        assert "Сумма: -" in result

    def test_income_has_plus_sign(self, sample_income_transaction):
        result = sample_income_transaction.format_for_user()
        assert "Сумма: +" in result


class TestCategory:
    def test_transaction_type_values(self):
        assert TransactionType.INCOME.value == "income"
        assert TransactionType.EXPENSE.value == "expense"

    def test_expense_categories_count(self):
        assert len(EXPENSE_CATEGORIES) >= 9

    def test_income_category(self):
        assert INCOME_CATEGORY.code == "income"
        assert INCOME_CATEGORY.type == TransactionType.INCOME

    def test_all_categories_includes_all(self):
        assert len(ALL_CATEGORIES) == len(EXPENSE_CATEGORIES) + 1

    def test_get_category_by_code_found(self):
        cat = get_category_by_code("food")
        assert cat is not None
        assert cat.name == "Еда"
        assert cat.type == TransactionType.EXPENSE

    def test_get_category_by_code_income(self):
        cat = get_category_by_code("income")
        assert cat is not None
        assert cat.name == "Доход"

    def test_get_category_by_code_not_found(self):
        assert get_category_by_code("nonexistent") is None

    def test_get_categories_by_type_expense(self):
        cats = get_categories_by_type(TransactionType.EXPENSE)
        assert len(cats) == len(EXPENSE_CATEGORIES)
        assert all(c.type == TransactionType.EXPENSE for c in cats)

    def test_get_categories_by_type_income(self):
        cats = get_categories_by_type(TransactionType.INCOME)
        assert len(cats) == 1
        assert cats[0].code == "income"

    def test_each_category_has_keywords(self):
        for cat in EXPENSE_CATEGORIES:
            if cat.code != "other":
                assert len(cat.keywords) > 0, f"Category {cat.code} has no keywords"
