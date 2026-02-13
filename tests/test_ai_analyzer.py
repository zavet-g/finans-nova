import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

from src.services.ai_analyzer import (
    fallback_categorize,
    format_categories_for_prompt,
    generate_fallback_report,
    generate_fallback_period_report,
    parse_transactions,
)
from src.models.category import TransactionType


class TestFallbackCategorize:
    def test_taxi(self):
        result = fallback_categorize("такси до работы")
        assert result["type"] == TransactionType.EXPENSE
        assert result["category"] == "Такси"
        assert result["confidence"] == "medium"

    def test_food(self):
        result = fallback_categorize("продукты в пятёрочке")
        assert result["category"] == "Еда"

    def test_health(self):
        result = fallback_categorize("аптека от простуды")
        assert result["category"] == "Здоровье"

    def test_entertainment(self):
        result = fallback_categorize("кино с друзьями")
        assert result["category"] == "Развлечения"

    def test_housing(self):
        result = fallback_categorize("аренда квартиры")
        assert result["category"] == "Жильё и быт"

    def test_housing_declined_form_not_matched(self):
        result = fallback_categorize("оплата аренды")
        assert result["category"] == "Прочее"

    def test_subscription(self):
        result = fallback_categorize("подписка netflix")
        assert result["category"] == "Подписки"

    def test_income_salary(self):
        result = fallback_categorize("зарплата за январь")
        assert result["type"] == TransactionType.INCOME
        assert result["category"] == "Доход"

    def test_income_received(self):
        result = fallback_categorize("получил перевод")
        assert result["type"] == TransactionType.INCOME

    def test_income_earned(self):
        result = fallback_categorize("заработал на фрилансе")
        assert result["type"] == TransactionType.INCOME

    def test_income_bonus(self):
        result = fallback_categorize("премия за квартал")
        assert result["type"] == TransactionType.INCOME

    def test_unknown_defaults_to_other(self):
        result = fallback_categorize("что-то непонятное")
        assert result["type"] == TransactionType.EXPENSE
        assert result["category"] == "Прочее"
        assert result["confidence"] == "low"

    def test_empty_string(self):
        result = fallback_categorize("")
        assert result["category"] == "Прочее"
        assert result["confidence"] == "low"

    def test_case_insensitive(self):
        result = fallback_categorize("ТАКСИ до работы")
        assert result["category"] == "Такси"


class TestFormatCategoriesForPrompt:
    def test_empty_dict(self):
        assert format_categories_for_prompt({}) == "- Нет данных"

    def test_single_category(self):
        result = format_categories_for_prompt({"Еда": 5000})
        assert "- Еда: 5000 руб." in result

    def test_multiple_categories(self):
        result = format_categories_for_prompt({"Еда": 5000, "Такси": 3000})
        assert "Еда" in result
        assert "Такси" in result


class TestGenerateFallbackReport:
    def test_basic_report(self, sample_summary, sample_previous_summary):
        result = generate_fallback_report(sample_summary, sample_previous_summary, "Январь", 2025)
        assert "ЯНВАРЬ 2025" in result
        assert "ДОХОДЫ" in result
        assert "РАСХОДЫ" in result
        assert "БАЛАНС" in result

    def test_categories_listed(self, sample_summary, sample_previous_summary):
        result = generate_fallback_report(sample_summary, sample_previous_summary, "Январь", 2025)
        assert "Еда" in result

    def test_zero_previous_income_no_crash(self):
        summary = {"income": 50000, "expenses": 30000, "by_category": {"Еда": 10000}}
        previous = {"income": 0, "expenses": 20000, "by_category": {"Еда": 8000}}
        result = generate_fallback_report(summary, previous, "Февраль", 2025)
        assert "ФЕВРАЛЬ 2025" in result
        assert "50,000" in result or "50 000" in result

    def test_zero_previous_expenses_no_crash(self):
        summary = {"income": 50000, "expenses": 30000, "by_category": {"Еда": 10000}}
        previous = {"income": 40000, "expenses": 0, "by_category": {}}
        result = generate_fallback_report(summary, previous, "Февраль", 2025)
        assert "ФЕВРАЛЬ 2025" in result
        assert "30,000" in result or "30 000" in result


class TestGenerateFallbackPeriodReport:
    def test_basic(self):
        summary = {"income": 100000, "expenses": 45000, "by_category": {"Еда": 15000, "Такси": 8000}}
        result = generate_fallback_period_report(summary, "Январь 2025")
        assert "ЯНВАРЬ 2025" in result
        assert "ДОХОДЫ" in result

    def test_empty_categories(self):
        summary = {"income": 0, "expenses": 0, "by_category": {}}
        result = generate_fallback_period_report(summary, "Март 2025")
        assert "Нет расходов" in result

    def test_categories_sorted_by_amount(self):
        summary = {"income": 0, "expenses": 25000, "by_category": {"Такси": 5000, "Еда": 15000, "Кино": 5000}}
        result = generate_fallback_period_report(summary, "Тест")
        lines = result.split("\n")
        cat_lines = [l for l in lines if l.startswith("- ")]
        assert "Еда" in cat_lines[0]


class TestParseTransactions:
    @pytest.mark.asyncio
    async def test_valid_json_response(self):
        mock_response = json.dumps([
            {"type": "expense", "category": "Такси", "description": "До работы", "amount": 500}
        ])

        with patch("src.services.ai_analyzer.call_yandex_gpt", new_callable=AsyncMock, return_value=mock_response):
            with patch("src.services.ai_analyzer.YANDEX_GPT_API_KEY", "test"):
                with patch("src.services.ai_analyzer.YANDEX_GPT_FOLDER_ID", "test"):
                    result = await parse_transactions("такси 500")

        assert result is not None
        assert len(result) == 1
        assert result[0]["type"] == TransactionType.EXPENSE
        assert result[0]["amount"] == 500

    @pytest.mark.asyncio
    async def test_markdown_wrapped_json(self):
        mock_response = '```json\n[{"type": "expense", "category": "Еда", "description": "Обед", "amount": 400}]\n```'

        with patch("src.services.ai_analyzer.call_yandex_gpt", new_callable=AsyncMock, return_value=mock_response):
            with patch("src.services.ai_analyzer.YANDEX_GPT_API_KEY", "test"):
                with patch("src.services.ai_analyzer.YANDEX_GPT_FOLDER_ID", "test"):
                    result = await parse_transactions("обед 400")

        assert result is not None
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_single_object_wrapped_in_list(self):
        mock_response = json.dumps(
            {"type": "expense", "category": "Такси", "description": "Такси", "amount": 300}
        )

        with patch("src.services.ai_analyzer.call_yandex_gpt", new_callable=AsyncMock, return_value=mock_response):
            with patch("src.services.ai_analyzer.YANDEX_GPT_API_KEY", "test"):
                with patch("src.services.ai_analyzer.YANDEX_GPT_FOLDER_ID", "test"):
                    result = await parse_transactions("такси 300")

        assert result is not None
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_invalid_json_returns_none(self):
        with patch("src.services.ai_analyzer.call_yandex_gpt", new_callable=AsyncMock, return_value="not json at all"):
            with patch("src.services.ai_analyzer.YANDEX_GPT_API_KEY", "test"):
                with patch("src.services.ai_analyzer.YANDEX_GPT_FOLDER_ID", "test"):
                    result = await parse_transactions("что-то")

        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_transactions(self):
        mock_response = json.dumps([
            {"type": "expense", "category": "Такси", "description": "Такси", "amount": 500},
            {"type": "expense", "category": "Еда", "description": "Кофе", "amount": 200},
        ])

        with patch("src.services.ai_analyzer.call_yandex_gpt", new_callable=AsyncMock, return_value=mock_response):
            with patch("src.services.ai_analyzer.YANDEX_GPT_API_KEY", "test"):
                with patch("src.services.ai_analyzer.YANDEX_GPT_FOLDER_ID", "test"):
                    result = await parse_transactions("такси 500 кофе 200")

        assert result is not None
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        with patch("src.services.ai_analyzer.YANDEX_GPT_API_KEY", ""):
            with patch("src.services.ai_analyzer.YANDEX_GPT_FOLDER_ID", "test"):
                result = await parse_transactions("такси 500")

        assert result is None
