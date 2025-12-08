import logging
import json
import asyncio
import aiohttp
from aiohttp.resolver import ThreadedResolver
from typing import Optional

from src.config import YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID
from src.models.category import TransactionType, EXPENSE_CATEGORIES, INCOME_CATEGORY

logger = logging.getLogger(__name__)

YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
MAX_RETRIES = 3


async def parse_transactions(text: str) -> list[dict] | None:
    """Парсит одну или несколько транзакций из текста с помощью YandexGPT."""
    if not YANDEX_GPT_API_KEY or not YANDEX_GPT_FOLDER_ID:
        logger.warning("YandexGPT not configured")
        return None

    categories_list = ", ".join([cat.name for cat in EXPENSE_CATEGORIES])

    prompt = f"""Извлеки из текста ВСЕ финансовые транзакции.

Текст: "{text}"

Категории расходов: {categories_list}
Категория дохода: Доход

ПРАВИЛА:
1. Каждая покупка — ОТДЕЛЬНАЯ транзакция со своей суммой и описанием
2. ОПИСАНИЕ должно содержать контекст именно этой покупки (куда, зачем, для кого), если он есть в тексте
3. Если контекста нет — просто название товара/услуги
4. Игнорируй команды бота: "добавь", "запиши", "в новые покупки"

Ответь ТОЛЬКО JSON-массивом:
[{{"type": "expense/income", "category": "категория", "description": "описание с контекстом", "amount": число}}]

Примеры:
- "такси до работы 500" -> [{{"type": "expense", "category": "Такси", "description": "До работы", "amount": 500}}]
- "такси 500" -> [{{"type": "expense", "category": "Такси", "description": "Такси", "amount": 500}}]
- "цветы жене 3500" -> [{{"type": "expense", "category": "Подарки", "description": "Цветы жене", "amount": 3500}}]
- "обед в столовой 400 кофе с коллегой 250" -> [{{"type": "expense", "category": "Еда", "description": "Обед в столовой", "amount": 400}}, {{"type": "expense", "category": "Еда", "description": "Кофе с коллегой", "amount": 250}}]
- "аптека от простуды 800" -> [{{"type": "expense", "category": "Здоровье", "description": "Лекарства от простуды", "amount": 800}}]
- "зарплата за ноябрь 100000" -> [{{"type": "income", "category": "Доход", "description": "Зарплата за ноябрь", "amount": 100000}}]"""

    try:
        result = await call_yandex_gpt(prompt)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(result)

        if not isinstance(data, list):
            data = [data]

        transactions = []
        for item in data:
            transactions.append({
                "type": TransactionType(item["type"]),
                "category": item["category"],
                "description": item["description"],
                "amount": float(item["amount"]),
            })
        return transactions if transactions else None
    except Exception as e:
        logger.error(f"YandexGPT parse failed: {e}")
        return None


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
    year: int,
    enriched_data: dict = None,
) -> str:
    """Генерирует ежемесячный финансовый отчёт через YandexGPT."""
    if not YANDEX_GPT_API_KEY or not YANDEX_GPT_FOLDER_ID:
        return generate_fallback_report(summary, previous_summary, month_name, year)

    period_name = f"{month_name} {year}"

    if enriched_data:
        prompt = _build_enriched_prompt(enriched_data, period_name)
    else:
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
    """Вызывает YandexGPT API с retry логикой."""
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

    timeout = aiohttp.ClientTimeout(total=60, connect=15, sock_read=30)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resolver = ThreadedResolver()
            connector = aiohttp.TCPConnector(resolver=resolver, force_close=True)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                logger.info(f"YandexGPT request attempt {attempt}/{MAX_RETRIES}")
                async with session.post(YANDEX_GPT_URL, headers=headers, json=body) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"YandexGPT API error: {response.status} - {error_text}")

                    data = await response.json()
                    return data["result"]["alternatives"][0]["message"]["text"]
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_error = e
            logger.warning(f"YandexGPT attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(1)

    raise RuntimeError(f"YandexGPT failed after {MAX_RETRIES} attempts: {last_error}")


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
    enriched_data: dict = None,
) -> str:
    """Генерирует AI-отчёт за произвольный период."""
    if not YANDEX_GPT_API_KEY or not YANDEX_GPT_FOLDER_ID:
        return generate_fallback_period_report(summary, period_name)

    if enriched_data:
        prompt = _build_enriched_prompt(enriched_data, period_name)
    else:
        prompt = _build_simple_prompt(summary, transactions_markdown, period_name)

    try:
        return await call_yandex_gpt(prompt)
    except Exception as e:
        logger.error(f"YandexGPT period report failed: {e}")
        return generate_fallback_period_report(summary, period_name)


def _build_enriched_prompt(data: dict, period_name: str) -> str:
    """Строит промпт с обогащёнными данными."""
    totals = data.get("totals", {})
    categories = data.get("categories", [])
    patterns = data.get("patterns", {})
    comparison = data.get("comparison")

    categories_text = ""
    for cat in categories:
        trend_str = ""
        if cat.get("trend_vs_prev_period") is not None:
            trend_str = f", тренд: {cat['trend_vs_prev_period']:+.1f}%"

        weekend_note = ""
        if cat.get("weekend_amount", 0) > cat.get("weekday_amount", 0) * 0.5:
            weekend_note = f", выходные: {cat['weekend_amount']} руб"

        categories_text += f"""
- {cat['name']}: {cat['amount']} руб ({cat['percent']}%)
  Транзакций: {cat['transaction_count']}, средняя: {cat['avg_transaction']} руб{trend_str}{weekend_note}
  Макс: {cat['max_transaction']['amount']} руб ({cat['max_transaction']['description']})"""

    anomalies_text = ""
    if patterns.get("anomalies"):
        anomalies_text = "\n\nАНОМАЛЬНЫЕ ТРАТЫ (превышают среднее в 3+ раза):"
        for a in patterns["anomalies"]:
            anomalies_text += f"\n- {a['date']}: {a['description']} — {a['amount']} руб (x{a['times_avg']} от среднего)"

    top_spending_text = ""
    if patterns.get("top_descriptions"):
        top_spending_text = "\n\nТОП-5 СТАТЕЙ РАСХОДОВ:"
        for t in patterns["top_descriptions"]:
            top_spending_text += f"\n- {t['description']}: {t['total']} руб ({t['count']} раз)"

    time_patterns_text = ""
    tp = patterns.get("time_patterns", {})
    if tp:
        time_patterns_text = f"""

ВРЕМЕННЫЕ ПАТТЕРНЫ:
- Самый затратный день: {tp.get('most_expensive_day', 'н/д')} ({tp.get('most_expensive_day_amount', 0)} руб)
- Средние траты в будни: {tp.get('weekday_avg', 0)} руб/день
- Средние траты в выходные: {tp.get('weekend_avg', 0)} руб/день"""

    comparison_text = ""
    if comparison:
        expenses_change = comparison.get('expenses_change')
        prev_expenses = comparison.get('prev_expenses', 0)

        if expenses_change is not None:
            comparison_text = f"""

СРАВНЕНИЕ С ПРОШЛЫМ ПЕРИОДОМ:
- Расходы: {expenses_change:+.1f}% (было {prev_expenses} руб)"""
        elif prev_expenses == 0:
            comparison_text = "\n\nСРАВНЕНИЕ С ПРОШЛЫМ ПЕРИОДОМ:\n- Нет данных за прошлый период"

        if comparison.get("growing_categories"):
            comparison_text += "\n- Выросли:"
            for g in comparison["growing_categories"]:
                change_str = f"+{g['change']}%" if g.get('change') else "(новая)"
                comparison_text += f" {g['category']} {change_str},"
        if comparison.get("shrinking_categories"):
            comparison_text += "\n- Снизились:"
            for s in comparison["shrinking_categories"]:
                comparison_text += f" {s['category']} {s['change']}%,"

    return f"""Ты — персональный финансовый аналитик. Проанализируй данные и дай КОНКРЕТНЫЕ инсайты.

ПЕРИОД: {period_name.upper()}

ИТОГИ:
- Доходы: {totals.get('income', 0)} руб
- Расходы: {totals.get('expenses', 0)} руб ({totals.get('savings_rate', 0)}% сохранено)
- Всего транзакций: {totals.get('transaction_count', 0)}

КАТЕГОРИИ:{categories_text}{anomalies_text}{top_spending_text}{time_patterns_text}{comparison_text}

ИНСТРУКЦИИ:
Напиши анализ по следующей структуре:

1. КЛЮЧЕВЫЕ ВЫВОДЫ (2-3 пункта)
Что важного произошло в этот период? Укажи конкретные цифры.

2. ПАТТЕРНЫ ПОВЕДЕНИЯ
Какие привычки видны в данных? (частые траты, дни недели, аномалии)

3. СРАВНЕНИЕ (если есть данные)
Что изменилось по сравнению с прошлым периодом и почему это важно?

4. РЕКОМЕНДАЦИИ (2-3 штуки)
Формат каждой:
- Действие: [что конкретно сделать]
- Потенциальная экономия: [сумма] руб/месяц
- Сложность: легко/средне/сложно

ЗАПРЕТЫ:
- Не давай абстрактных советов типа "пересмотрите расходы" или "сравните цены"
- Не предлагай кардинальных изменений образа жизни
- Не повторяй очевидное из данных без добавления ценности

Формат: структурированный текст с заголовками. Без эмодзи. Кратко и по делу."""


def _build_simple_prompt(summary: dict, transactions_markdown: str, period_name: str) -> str:
    """Строит простой промпт без обогащённых данных (fallback)."""
    return f"""Ты — личный финансовый аналитик, который непредвзято оценивает траты
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
