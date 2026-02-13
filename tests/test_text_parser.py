import pytest
from src.bot.handlers.text import (
    parse_amount_from_part,
    parse_amount,
    parse_multiple_transactions,
    determine_type_and_category,
    clean_description,
)
from src.models.category import TransactionType


class TestParseAmountFromPart:
    def test_simple_number(self):
        assert parse_amount_from_part("500") == 500

    def test_with_rub_short(self):
        assert parse_amount_from_part("500р") == 500

    def test_with_rub_full(self):
        assert parse_amount_from_part("500 руб") == 500

    def test_with_rub_word(self):
        assert parse_amount_from_part("500 рублей") == 500

    def test_with_currency_sign(self):
        assert parse_amount_from_part("1500₽") == 1500

    def test_thousands_short(self):
        result = parse_amount_from_part("2 тыс")
        assert result == 2000

    def test_thousands_with_rub(self):
        result = parse_amount_from_part("5 тыс руб")
        assert result == 5000

    def test_thousands_dot_short(self):
        result = parse_amount_from_part("3т.")
        assert result == 3000

    def test_with_verb_prefix(self):
        assert parse_amount_from_part("потратил 500") == 500

    def test_with_preposition_prefix(self):
        assert parse_amount_from_part("за 1200") == 1200

    def test_no_amount(self):
        assert parse_amount_from_part("просто текст без суммы") is None

    def test_empty_string(self):
        assert parse_amount_from_part("") is None

    def test_nbsp_handling(self):
        assert parse_amount_from_part("500\xa0руб") == 500

    def test_large_amount(self):
        assert parse_amount_from_part("100000") == 100000

    def test_word_with_t_triggers_thousands_bug(self):
        result = parse_amount_from_part("транспорт 500")
        assert result == 500000


class TestParseAmount:
    def test_simple_number(self):
        assert parse_amount("1500") == 1500

    def test_with_currency(self):
        assert parse_amount("500р") == 500

    def test_with_spaces(self):
        assert parse_amount("1 500") == 1500

    def test_empty_string(self):
        assert parse_amount("") is None

    def test_no_digits(self):
        assert parse_amount("нет суммы") is None

    def test_with_verb(self):
        assert parse_amount("потратил 800") == 800


class TestParseMultipleTransactions:
    def test_comma_separator(self):
        result = parse_multiple_transactions("такси 500, кофе 200")
        assert len(result) == 2
        amounts = [tx["amount"] for tx in result]
        assert 500 in amounts
        assert 200 in amounts

    def test_semicolon_separator(self):
        result = parse_multiple_transactions("такси 500; кофе 200")
        assert len(result) == 2

    def test_and_separator(self):
        result = parse_multiple_transactions("такси 500 и кофе 200")
        assert len(result) == 2

    def test_single_transaction(self):
        result = parse_multiple_transactions("такси 500")
        assert len(result) == 1
        assert result[0]["amount"] == 500

    def test_no_amount_parts_skipped(self):
        result = parse_multiple_transactions("просто текст")
        assert len(result) == 0

    def test_empty_string(self):
        result = parse_multiple_transactions("")
        assert len(result) == 0

    def test_categories_assigned(self):
        result = parse_multiple_transactions("такси 500")
        assert result[0]["category"] == "Такси"


class TestDetermineTypeAndCategory:
    def test_income_salary(self):
        tx_type, category = determine_type_and_category("зарплата 100000")
        assert tx_type == TransactionType.INCOME
        assert category == "Доход"

    def test_income_received(self):
        tx_type, category = determine_type_and_category("получил 50000")
        assert tx_type == TransactionType.INCOME

    def test_income_earned(self):
        tx_type, category = determine_type_and_category("заработал на фрилансе 30000")
        assert tx_type == TransactionType.INCOME

    def test_expense_taxi(self):
        tx_type, category = determine_type_and_category("такси 500")
        assert tx_type == TransactionType.EXPENSE
        assert category == "Такси"

    def test_expense_food(self):
        tx_type, category = determine_type_and_category("продукты 3000")
        assert tx_type == TransactionType.EXPENSE
        assert category == "Еда"

    def test_expense_health(self):
        tx_type, category = determine_type_and_category("аптека 800")
        assert tx_type == TransactionType.EXPENSE
        assert category == "Здоровье"

    def test_expense_entertainment(self):
        tx_type, category = determine_type_and_category("кино 500")
        assert tx_type == TransactionType.EXPENSE
        assert category == "Развлечения"

    def test_expense_subscription(self):
        tx_type, category = determine_type_and_category("подписка youtube premium 200")
        assert tx_type == TransactionType.EXPENSE
        assert category == "Подписки"

    def test_unknown_defaults_to_other(self):
        tx_type, category = determine_type_and_category("что-то непонятное 500")
        assert tx_type == TransactionType.EXPENSE
        assert category == "Прочее"

    def test_case_insensitive(self):
        tx_type, category = determine_type_and_category("ТАКСИ 500")
        assert tx_type == TransactionType.EXPENSE
        assert category == "Такси"

    def test_income_keyword_priority(self):
        tx_type, _ = determine_type_and_category("получил подарок 3000")
        assert tx_type == TransactionType.INCOME


class TestCleanDescription:
    def test_removes_amount(self):
        result = clean_description("такси 500 руб")
        assert "500" not in result

    def test_removes_filler_words(self):
        result = clean_description("потратил 500 на такси")
        assert "потратил" not in result.lower()

    def test_preserves_meaningful_text(self):
        result = clean_description("такси 500")
        assert "такси" in result.lower()

    def test_empty_input(self):
        assert clean_description("") == ""

    def test_only_amount(self):
        assert clean_description("500") == ""
