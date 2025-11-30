import logging
import json
import aiohttp
from typing import Optional

from src.config import YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID
from src.models.category import TransactionType, EXPENSE_CATEGORIES, INCOME_CATEGORY

logger = logging.getLogger(__name__)

YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


async def categorize_transaction(description: str, amount: float) -> dict:
    """Категоризирует транзакцию с помощью YandexGPT."""
    if not YANDEX_GPT_API_KEY or not YANDEX_GPT_FOLDER_ID:
        logger.warning("YandexGPT not configured, using fallback")
        return fallback_categorize(description)

    categories_list = ", ".join([cat.name for cat in EXPENSE_CATEGORIES])

    prompt = f"""Ты — личный финансовый аналитик. Проанализируй транзакцию и определи:
1. Тип: расход или доход
2. Категорию из списка: {categories_list}, Доход

Транзакция: "{description}", сумма: {amount} руб.

Ответь ТОЛЬКО в формате JSON без пояснений:
{{"type": "expense" или "income", "category": "название категории", "confidence": "high/medium/low"}}"""

    try:
        result = await call_yandex_gpt(prompt)
        data = json.loads(result)
        return {
            "type": TransactionType(data["type"]),
            "category": data["category"],
            "confidence": data.get("confidence", "medium"),
        }
    except Exception as e:
        logger.error(f"YandexGPT categorization failed: {e}")
        return fallback_categorize(description)


async def generate_monthly_report(
    summary: dict,
    previous_summary: dict,
    transactions_markdown: str,
    month_name: str,
    year: int
) -> str:
    """Генерирует ежемесячный финансовый отчёт через YandexGPT."""
    if not YANDEX_GPT_API_KEY or not YANDEX_GPT_FOLDER_ID:
        return generate_fallback_report(summary, previous_summary, month_name, year)

    prompt = f"""Ты — личный финансовый аналитик, который непредвзято оценивает траты
и даёт честные, объективные рекомендации. Без лишних слов.

СВОДКА ЗА ТЕКУЩИЙ МЕСЯЦ ({month_name} {year}):
Доходы: {summary.get('income', 0)} руб.
Расходы: {summary.get('expenses', 0)} руб.
Баланс месяца: {summary.get('balance', 0)} руб.

Расходы по категориям:
{format_categories_for_prompt(summary.get('by_category', {}))}

СВОДКА ЗА ПРОШЛЫЙ МЕСЯЦ:
Доходы: {previous_summary.get('income', 0)} руб.
Расходы: {previous_summary.get('expenses', 0)} руб.

Расходы по категориям:
{format_categories_for_prompt(previous_summary.get('by_category', {}))}

ДЕТАЛЬНЫЕ ТРАНЗАКЦИИ:
{transactions_markdown}

ЗАДАЧИ:
1. Проанализируй структуру расходов
2. Сравни с прошлым месяцем, укажи изменения в процентах
3. Выяви проблемные категории (рост > 20%)
4. Найди паттерны в транзакциях
5. Дай 3-5 конкретных рекомендаций на следующий месяц
6. Будь честен и прямолинеен

Формат ответа — структурированный текст без эмодзи."""

    try:
        return await call_yandex_gpt(prompt)
    except Exception as e:
        logger.error(f"YandexGPT report generation failed: {e}")
        return generate_fallback_report(summary, previous_summary, month_name, year)


async def call_yandex_gpt(prompt: str, temperature: float = 0.3) -> str:
    """Вызывает YandexGPT API."""
    headers = {
        "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "modelUri": f"gpt://{YANDEX_GPT_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": 2000,
        },
        "messages": [
            {"role": "user", "text": prompt}
        ],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(YANDEX_GPT_URL, headers=headers, json=body) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"YandexGPT API error: {response.status} - {error_text}")

            data = await response.json()
            return data["result"]["alternatives"][0]["message"]["text"]


def fallback_categorize(description: str) -> dict:
    """Простая категоризация по ключевым словам без AI."""
    description_lower = description.lower()

    income_keywords = ["зарплата", "получил", "доход", "заработал", "премия"]
    if any(kw in description_lower for kw in income_keywords):
        return {
            "type": TransactionType.INCOME,
            "category": INCOME_CATEGORY.name,
            "confidence": "medium",
        }

    for category in EXPENSE_CATEGORIES:
        for keyword in category.keywords:
            if keyword in description_lower:
                return {
                    "type": TransactionType.EXPENSE,
                    "category": category.name,
                    "confidence": "medium",
                }

    return {
        "type": TransactionType.EXPENSE,
        "category": "Прочее",
        "confidence": "low",
    }


def format_categories_for_prompt(by_category: dict) -> str:
    """Форматирует категории для промпта."""
    lines = []
    for cat_name, amount in by_category.items():
        lines.append(f"- {cat_name}: {amount} руб.")
    return "\n".join(lines) if lines else "- Нет данных"


async def generate_period_report(
    summary: dict,
    transactions_markdown: str,
    period_name: str,
) -> str:
    """Генерирует AI-отчёт за произвольный период."""
    if not YANDEX_GPT_API_KEY or not YANDEX_GPT_FOLDER_ID:
        return generate_fallback_period_report(summary, period_name)

    prompt = f"""Ты — личный финансовый аналитик, который непредвзято оценивает траты
и даёт честные, объективные рекомендации. Без лишних слов.

СВОДКА ЗА {period_name.upper()}:
Доходы: {summary.get('income', 0)} руб.
Расходы: {summary.get('expenses', 0)} руб.
Баланс периода: {summary.get('balance', 0)} руб.

Расходы по категориям:
{format_categories_for_prompt(summary.get('by_category', {}))}

ДЕТАЛЬНЫЕ ТРАНЗАКЦИИ:
{transactions_markdown}

ЗАДАЧИ:
1. Проанализируй структуру расходов
2. Выяви самые крупные статьи расходов
3. Найди паттерны в транзакциях (частые мелкие траты, крупные разовые)
4. Дай 3-5 конкретных рекомендаций по оптимизации расходов
5. Будь честен и прямолинеен

Формат ответа — структурированный текст без эмодзи."""

    try:
        return await call_yandex_gpt(prompt)
    except Exception as e:
        logger.error(f"YandexGPT period report failed: {e}")
        return generate_fallback_period_report(summary, period_name)


def generate_fallback_period_report(summary: dict, period_name: str) -> str:
    """Генерирует простой отчёт за период без AI."""
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    balance = income - expenses

    report = f"""ФИНАНСОВЫЙ ОТЧЁТ ЗА {period_name.upper()}

ДОХОДЫ: {income:,.0f} руб.
РАСХОДЫ: {expenses:,.0f} руб.
БАЛАНС: {balance:+,.0f} руб.

РАСХОДЫ ПО КАТЕГОРИЯМ:"""

    sorted_cats = sorted(summary.get("by_category", {}).items(), key=lambda x: x[1], reverse=True)
    for cat_name, amount in sorted_cats:
        percent = (amount / expenses * 100) if expenses else 0
        report += f"\n- {cat_name}: {amount:,.0f} руб. ({percent:.1f}%)"

    if not sorted_cats:
        report += "\n- Нет расходов"

    return report


def generate_fallback_report(summary: dict, previous_summary: dict, month_name: str, year: int) -> str:
    """Генерирует простой отчёт без AI."""
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    balance = income - expenses

    prev_income = previous_summary.get("income", 0)
    prev_expenses = previous_summary.get("expenses", 0)

    income_change = ((income - prev_income) / prev_income * 100) if prev_income else 0
    expenses_change = ((expenses - prev_expenses) / prev_expenses * 100) if prev_expenses else 0

    report = f"""ФИНАНСОВЫЙ ОТЧЁТ ЗА {month_name.upper()} {year}

ДОХОДЫ: {income:,.0f} руб. ({income_change:+.1f}% к прошлому месяцу)
РАСХОДЫ: {expenses:,.0f} руб. ({expenses_change:+.1f}% к прошлому месяцу)
БАЛАНС: {balance:+,.0f} руб.

РАСХОДЫ ПО КАТЕГОРИЯМ:"""

    for cat_name, amount in summary.get("by_category", {}).items():
        prev_amount = previous_summary.get("by_category", {}).get(cat_name, 0)
        change = ((amount - prev_amount) / prev_amount * 100) if prev_amount else 0
        report += f"\n- {cat_name}: {amount:,.0f} руб. ({change:+.1f}%)"

    report += "\n\nДля AI-анализа настрой YandexGPT в .env"

    return report
