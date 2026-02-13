import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.services.sheets import (
    _analyze_categories,
    _analyze_patterns,
    _analyze_comparison,
    calculate_month_summary,
    get_period_summary,
    get_yearly_monthly_breakdown,
)


def make_mock_spreadsheet(rows):
    mock_worksheet = MagicMock()
    mock_worksheet.get_all_values.return_value = rows

    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    return mock_spreadsheet


class TestAnalyzeCategories:
    def test_basic_stats(self, sample_transactions_list):
        by_category = {"Еда": 8600, "Такси": 500, "Развлечения": 800, "Здоровье": 1200}
        result = _analyze_categories(sample_transactions_list, by_category)

        assert len(result) > 0
        food = next((c for c in result if c["name"] == "Еда"), None)
        assert food is not None
        assert food["amount"] == 8600
        assert food["transaction_count"] >= 1

    def test_percent_calculation(self):
        transactions = [
            {"date": "2025-01-05", "type": "расход", "category": "Еда", "description": "Обед", "amount": 500},
            {"date": "2025-01-06", "type": "расход", "category": "Такси", "description": "Такси", "amount": 500},
        ]
        by_category = {"Еда": 500, "Такси": 500}
        result = _analyze_categories(transactions, by_category)

        for cat in result:
            assert cat["percent"] == 50.0

    def test_with_previous_summary_trend(self):
        transactions = [
            {"date": "2025-01-05", "type": "расход", "category": "Еда", "description": "Обед", "amount": 1500},
        ]
        by_category = {"Еда": 1500}
        prev_summary = {"by_category": {"Еда": 1000}}

        result = _analyze_categories(transactions, by_category, prev_summary)
        food = result[0]
        assert food["trend_vs_prev_period"] == 50.0

    def test_trend_none_when_no_previous(self):
        transactions = [
            {"date": "2025-01-05", "type": "расход", "category": "Еда", "description": "Обед", "amount": 500},
        ]
        by_category = {"Еда": 500}
        result = _analyze_categories(transactions, by_category)
        assert result[0]["trend_vs_prev_period"] is None

    def test_max_transaction(self):
        transactions = [
            {"date": "2025-01-05", "type": "расход", "category": "Еда", "description": "Обед", "amount": 300},
            {"date": "2025-01-06", "type": "расход", "category": "Еда", "description": "Ресторан", "amount": 3000},
        ]
        by_category = {"Еда": 3300}
        result = _analyze_categories(transactions, by_category)
        assert result[0]["max_transaction"]["amount"] == 3000
        assert result[0]["max_transaction"]["description"] == "Ресторан"

    def test_empty_category_skipped(self):
        transactions = [
            {"date": "2025-01-05", "type": "доход", "category": "Доход", "description": "Зарплата", "amount": 100000},
        ]
        by_category = {"Доход": 100000}
        result = _analyze_categories(transactions, by_category)
        assert len(result) == 0

    def test_weekday_weekend_split(self):
        transactions = [
            {"date": "2025-01-06", "type": "расход", "category": "Еда", "description": "Обед", "amount": 500},
            {"date": "2025-01-11", "type": "расход", "category": "Еда", "description": "Ужин", "amount": 2000},
        ]
        by_category = {"Еда": 2500}
        result = _analyze_categories(transactions, by_category)
        food = result[0]
        assert food["weekday_amount"] == 500
        assert food["weekend_amount"] == 2000


class TestAnalyzePatterns:
    def test_empty_transactions(self):
        result = _analyze_patterns([])
        assert result["anomalies"] == []
        assert result["top_descriptions"] == []
        assert result["time_patterns"] == {}

    def test_only_income_returns_empty(self):
        transactions = [
            {"date": "2025-01-05", "type": "доход", "category": "Доход", "description": "Зарплата", "amount": 100000},
        ]
        result = _analyze_patterns(transactions)
        assert result["anomalies"] == []

    def test_anomaly_detection(self):
        transactions = [
            {"date": "2025-01-05", "type": "расход", "category": "Еда", "description": "Обед", "amount": 300},
            {"date": "2025-01-06", "type": "расход", "category": "Еда", "description": "Обед", "amount": 350},
            {"date": "2025-01-07", "type": "расход", "category": "Еда", "description": "Обед", "amount": 400},
            {"date": "2025-01-08", "type": "расход", "category": "Еда", "description": "Обед", "amount": 300},
            {"date": "2025-01-09", "type": "расход", "category": "Еда", "description": "Обед", "amount": 350},
            {"date": "2025-01-10", "type": "расход", "category": "Развлечения", "description": "Концерт", "amount": 15000},
        ]
        result = _analyze_patterns(transactions)
        assert len(result["anomalies"]) > 0
        assert result["anomalies"][0]["amount"] == 15000

    def test_top_descriptions(self):
        transactions = [
            {"date": "2025-01-05", "type": "расход", "category": "Еда", "description": "Обед в столовой", "amount": 300},
            {"date": "2025-01-06", "type": "расход", "category": "Еда", "description": "Обед в столовой", "amount": 350},
            {"date": "2025-01-07", "type": "расход", "category": "Еда", "description": "Обед в столовой", "amount": 400},
        ]
        result = _analyze_patterns(transactions)
        assert len(result["top_descriptions"]) > 0
        assert result["top_descriptions"][0]["count"] == 3

    def test_time_patterns_most_expensive_day(self):
        transactions = [
            {"date": "2025-01-06", "type": "расход", "category": "Еда", "description": "Обед", "amount": 500},
            {"date": "2025-01-07", "type": "расход", "category": "Еда", "description": "Обед", "amount": 3000},
        ]
        result = _analyze_patterns(transactions)
        assert "most_expensive_day" in result["time_patterns"]
        assert result["time_patterns"]["most_expensive_day_amount"] == 3000

    def test_short_descriptions_skipped(self):
        transactions = [
            {"date": "2025-01-05", "type": "расход", "category": "Еда", "description": "ab", "amount": 500},
        ]
        result = _analyze_patterns(transactions)
        assert len(result["top_descriptions"]) == 0

    def test_anomalies_limited_to_five(self):
        transactions = []
        for i in range(10):
            transactions.append({"date": "2025-01-05", "type": "расход", "category": "Еда", "description": f"Обед {i}", "amount": 100})
        for i in range(10):
            transactions.append({"date": "2025-01-05", "type": "расход", "category": "Еда", "description": f"Большая трата {i}", "amount": 50000})
        result = _analyze_patterns(transactions)
        assert len(result["anomalies"]) <= 5


class TestAnalyzeComparison:
    def test_expenses_growth(self):
        current = {"income": 100000, "expenses": 50000, "by_category": {"Еда": 20000}}
        previous = {"income": 100000, "expenses": 40000, "by_category": {"Еда": 15000}}
        result = _analyze_comparison(current, previous)
        assert result["expenses_change"] == 25.0

    def test_expenses_decrease(self):
        current = {"income": 100000, "expenses": 30000, "by_category": {}}
        previous = {"income": 100000, "expenses": 50000, "by_category": {}}
        result = _analyze_comparison(current, previous)
        assert result["expenses_change"] == -40.0

    def test_zero_previous_expenses(self):
        current = {"income": 100000, "expenses": 50000, "by_category": {}}
        previous = {"income": 100000, "expenses": 0, "by_category": {}}
        result = _analyze_comparison(current, previous)
        assert result["expenses_change"] is None

    def test_growing_categories(self):
        current = {"income": 0, "expenses": 0, "by_category": {"Еда": 15000, "Такси": 8000}}
        previous = {"income": 0, "expenses": 0, "by_category": {"Еда": 10000, "Такси": 8000}}
        result = _analyze_comparison(current, previous)
        growing_names = [g["category"] for g in result["growing_categories"]]
        assert "Еда" in growing_names

    def test_shrinking_categories(self):
        current = {"income": 0, "expenses": 0, "by_category": {"Еда": 5000}}
        previous = {"income": 0, "expenses": 0, "by_category": {"Еда": 10000}}
        result = _analyze_comparison(current, previous)
        shrinking_names = [s["category"] for s in result["shrinking_categories"]]
        assert "Еда" in shrinking_names

    def test_new_category(self):
        current = {"income": 0, "expenses": 0, "by_category": {"Подписки": 500}}
        previous = {"income": 0, "expenses": 0, "by_category": {}}
        result = _analyze_comparison(current, previous)
        growing_names = [g["category"] for g in result["growing_categories"]]
        assert "Подписки" in growing_names

    def test_income_change_positive(self):
        current = {"income": 120000, "expenses": 0, "by_category": {}}
        previous = {"income": 100000, "expenses": 0, "by_category": {}}
        result = _analyze_comparison(current, previous)
        assert result["income_change"] == 20.0

    def test_income_change_negative(self):
        current = {"income": 80000, "expenses": 0, "by_category": {}}
        previous = {"income": 100000, "expenses": 0, "by_category": {}}
        result = _analyze_comparison(current, previous)
        assert result["income_change"] == -20.0

    def test_income_change_zero_previous(self):
        current = {"income": 100000, "expenses": 0, "by_category": {}}
        previous = {"income": 0, "expenses": 0, "by_category": {}}
        result = _analyze_comparison(current, previous)
        assert result["income_change"] is None

    def test_category_within_threshold_not_listed(self):
        current = {"income": 0, "expenses": 0, "by_category": {"Еда": 11000}}
        previous = {"income": 0, "expenses": 0, "by_category": {"Еда": 10000}}
        result = _analyze_comparison(current, previous)
        assert len(result["growing_categories"]) == 0
        assert len(result["shrinking_categories"]) == 0

    def test_growing_limited_to_three(self):
        current = {"income": 0, "expenses": 0, "by_category": {f"Cat{i}": 5000 for i in range(5)}}
        previous = {"income": 0, "expenses": 0, "by_category": {f"Cat{i}": 1000 for i in range(5)}}
        result = _analyze_comparison(current, previous)
        assert len(result["growing_categories"]) <= 3


class TestCalculateMonthSummary:
    def test_filters_by_month(self, sample_sheets_rows):
        mock_ss = make_mock_spreadsheet(sample_sheets_rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = calculate_month_summary(2025, 1)

        assert result["income"] == 100000
        assert result["expenses"] == 11100
        assert "Еда" in result["by_category"]

    def test_different_month(self, sample_sheets_rows):
        mock_ss = make_mock_spreadsheet(sample_sheets_rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = calculate_month_summary(2025, 2)

        assert result["income"] == 30000
        assert result["expenses"] == 2500

    def test_empty_sheet(self):
        rows = [["Дата", "Время", "Тип", "Категория", "Описание", "Сумма", "Баланс"]]
        mock_ss = make_mock_spreadsheet(rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = calculate_month_summary(2025, 1)

        assert result == {"income": 0, "expenses": 0, "balance": 0, "by_category": {}}

    def test_invalid_row_skipped(self):
        rows = [
            ["Дата", "Время", "Тип", "Категория", "Описание", "Сумма", "Баланс"],
            ["2025-01-05", "10:00", "расход", "Еда", "Обед", "500", ""],
            ["invalid", "", "", "", "", "", ""],
            ["2025-01-06", "10:00", "расход", "Такси", "Такси", "not_a_number", ""],
        ]
        mock_ss = make_mock_spreadsheet(rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = calculate_month_summary(2025, 1)

        assert result["expenses"] == 500

    def test_balance_calculation(self, sample_sheets_rows):
        mock_ss = make_mock_spreadsheet(sample_sheets_rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = calculate_month_summary(2025, 1)

        assert result["balance"] == result["income"] - result["expenses"]


class TestGetPeriodSummary:
    def test_filters_by_date_range(self, sample_sheets_rows):
        mock_ss = make_mock_spreadsheet(sample_sheets_rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = get_period_summary(datetime(2025, 1, 1), datetime(2025, 1, 10))

        assert result["income"] == 100000
        tx_dates = [t["date"] for t in result["transactions"]]
        assert all(d <= "2025-01-10" for d in tx_dates)

    def test_includes_transactions_list(self, sample_sheets_rows):
        mock_ss = make_mock_spreadsheet(sample_sheets_rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = get_period_summary(datetime(2025, 1, 1), datetime(2025, 1, 31))

        assert len(result["transactions"]) > 0
        assert "date" in result["transactions"][0]
        assert "amount" in result["transactions"][0]

    def test_empty_period(self, sample_sheets_rows):
        mock_ss = make_mock_spreadsheet(sample_sheets_rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = get_period_summary(datetime(2025, 6, 1), datetime(2025, 6, 30))

        assert result["income"] == 0
        assert result["expenses"] == 0
        assert len(result["transactions"]) == 0


class TestGetYearlyMonthlyBreakdown:
    def test_returns_12_months(self, sample_sheets_rows):
        mock_ss = make_mock_spreadsheet(sample_sheets_rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = get_yearly_monthly_breakdown(2025)

        assert len(result["income"]) == 12
        assert len(result["expenses"]) == 12

    def test_correct_month_assignment(self, sample_sheets_rows):
        mock_ss = make_mock_spreadsheet(sample_sheets_rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = get_yearly_monthly_breakdown(2025)

        assert result["income"][1] == 100000
        assert result["income"][2] == 30000
        assert result["expenses"][1] == 11100

    def test_empty_year(self):
        rows = [["Дата", "Время", "Тип", "Категория", "Описание", "Сумма", "Баланс"]]
        mock_ss = make_mock_spreadsheet(rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = get_yearly_monthly_breakdown(2025)

        assert all(v == 0 for v in result["income"].values())
        assert all(v == 0 for v in result["expenses"].values())

    def test_different_year_filtered(self, sample_sheets_rows):
        mock_ss = make_mock_spreadsheet(sample_sheets_rows)
        with patch("src.services.sheets.get_spreadsheet", return_value=mock_ss):
            result = get_yearly_monthly_breakdown(2024)

        assert all(v == 0 for v in result["income"].values())
