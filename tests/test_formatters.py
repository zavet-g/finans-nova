from src.utils.formatters import (
    calculate_change_percent,
    format_amount,
    format_report_header,
    format_summary,
    format_transaction_list,
    month_name,
    month_name_short,
)


class TestMonthName:
    def test_january(self):
        assert month_name(1) == "Январь"

    def test_december(self):
        assert month_name(12) == "Декабрь"

    def test_invalid_month_returns_string(self):
        assert month_name(13) == "13"

    def test_zero_returns_string(self):
        assert month_name(0) == "0"


class TestMonthNameShort:
    def test_january(self):
        assert month_name_short(1) == "Янв"

    def test_may(self):
        assert month_name_short(5) == "Май"

    def test_december(self):
        assert month_name_short(12) == "Дек"

    def test_invalid_returns_string(self):
        assert month_name_short(13) == "13"


class TestFormatAmount:
    def test_simple(self):
        assert format_amount(500) == "500"

    def test_thousands(self):
        assert format_amount(1500) == "1 500"

    def test_millions(self):
        assert format_amount(1500000) == "1 500 000"

    def test_zero(self):
        assert format_amount(0) == "0"

    def test_with_sign_positive(self):
        assert format_amount(500, with_sign=True) == "+500"

    def test_with_sign_zero(self):
        result = format_amount(0, with_sign=True)
        assert result == "0"

    def test_with_sign_negative(self):
        assert format_amount(-500, with_sign=True) == "-500"


class TestCalculateChangePercent:
    def test_increase(self):
        assert calculate_change_percent(150, 100) == "+50.0%"

    def test_decrease(self):
        assert calculate_change_percent(80, 100) == "-20.0%"

    def test_no_change(self):
        assert calculate_change_percent(100, 100) == "+0.0%"

    def test_division_by_zero(self):
        assert calculate_change_percent(100, 0) == "—"

    def test_both_zero(self):
        assert calculate_change_percent(0, 0) == "—"

    def test_double_increase(self):
        assert calculate_change_percent(200, 100) == "+100.0%"


class TestFormatTransactionList:
    def test_empty_list(self):
        assert format_transaction_list([]) == "Пока транзакций нет."

    def test_expense_has_minus(self):
        txs = [{"Дата": "2025-01-15", "Категория": "Еда", "Сумма": "500", "Тип": "expense"}]
        result = format_transaction_list(txs)
        assert "15.01" in result
        assert "Еда" in result

    def test_income_has_plus(self):
        txs = [{"Дата": "2025-01-10", "Категория": "Доход", "Сумма": "100000", "Тип": "income"}]
        result = format_transaction_list(txs)
        assert "+" in result

    def test_invalid_date_handled(self):
        txs = [{"Дата": "invalid", "Категория": "Еда", "Сумма": "500", "Тип": "expense"}]
        result = format_transaction_list(txs)
        assert "invalid" in result

    def test_empty_amount_handled(self):
        txs = [{"Дата": "2025-01-15", "Категория": "Еда", "Сумма": "", "Тип": "expense"}]
        result = format_transaction_list(txs)
        assert "Еда" in result
        assert "15.01" in result

    def test_multiple_transactions(self):
        txs = [
            {"Дата": "2025-01-15", "Категория": "Еда", "Сумма": "500", "Тип": "expense"},
            {"Дата": "2025-01-16", "Категория": "Такси", "Сумма": "300", "Тип": "expense"},
        ]
        result = format_transaction_list(txs)
        assert "Еда" in result
        assert "Такси" in result

    def test_nbsp_in_amount(self):
        txs = [{"Дата": "2025-01-15", "Категория": "Еда", "Сумма": "1\xa0500", "Тип": "expense"}]
        result = format_transaction_list(txs)
        assert "1 500" in result


class TestFormatReportHeader:
    def test_basic(self):
        result = format_report_header(1, 2025)
        assert "ЯНВАРЬ" in result
        assert "2025" in result


class TestFormatSummary:
    def test_basic(self, sample_summary):
        result = format_summary(sample_summary)
        assert "ДОХОДЫ" in result
        assert "РАСХОДЫ" in result
        assert "БАЛАНС" in result
        assert "100 000" in result

    def test_with_previous(self, sample_summary, sample_previous_summary):
        result = format_summary(sample_summary, sample_previous_summary)
        assert "%" in result

    def test_without_previous(self, sample_summary):
        result = format_summary(sample_summary)
        assert "%" not in result

    def test_categories_listed(self, sample_summary):
        result = format_summary(sample_summary)
        assert "Еда" in result
        assert "Такси" in result

    def test_previous_with_zero_income(self):
        summary = {"income": 50000, "expenses": 30000, "by_category": {}}
        previous = {"income": 0, "expenses": 20000, "by_category": {}}
        result = format_summary(summary, previous)
        assert "—" in result
