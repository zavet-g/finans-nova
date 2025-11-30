import logging
from io import BytesIO
from datetime import datetime
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')

logger = logging.getLogger(__name__)

CATEGORY_COLORS = {
    "Еда": "#FF6B6B",
    "Жильё и быт": "#4ECDC4",
    "Такси": "#45B7D1",
    "Здоровье": "#96CEB4",
    "Развлечения": "#FFEAA7",
    "Одежда": "#DDA0DD",
    "Подписки": "#98D8C8",
    "Подарки": "#F7DC6F",
    "Прочее": "#BDC3C7",
    "Доход": "#2ECC71",
}


def generate_pie_chart(data: dict, title: str = "Расходы по категориям") -> BytesIO:
    """Генерирует круговую диаграмму расходов."""
    if not data:
        return generate_empty_chart("Нет данных для отображения")

    categories = list(data.keys())
    amounts = list(data.values())

    total = sum(amounts)
    if total == 0:
        return generate_empty_chart("Нет расходов за период")

    colors = [CATEGORY_COLORS.get(cat, "#BDC3C7") for cat in categories]

    fig, ax = plt.subplots(figsize=(10, 8))

    wedges, texts, autotexts = ax.pie(
        amounts,
        labels=categories,
        autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100*total):,} руб.)'.replace(',', ' '),
        colors=colors,
        startangle=90,
        explode=[0.02] * len(categories),
    )

    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_weight('bold')

    for text in texts:
        text.set_fontsize(10)

    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()

    return buf


def generate_bar_chart(data: dict, title: str = "Расходы по категориям") -> BytesIO:
    """Генерирует столбчатую диаграмму."""
    if not data:
        return generate_empty_chart("Нет данных для отображения")

    sorted_data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
    categories = list(sorted_data.keys())
    amounts = list(sorted_data.values())

    colors = [CATEGORY_COLORS.get(cat, "#BDC3C7") for cat in categories]

    fig, ax = plt.subplots(figsize=(12, 6))

    bars = ax.barh(categories, amounts, color=colors)

    for bar, amount in zip(bars, amounts):
        ax.text(
            bar.get_width() + max(amounts) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f'{int(amount):,} руб.'.replace(',', ' '),
            va='center',
            fontsize=10
        )

    ax.set_xlabel('Сумма (руб.)', fontsize=11)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.invert_yaxis()

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()

    return buf


def generate_comparison_chart(current: dict, previous: dict, title: str = "Сравнение с прошлым месяцем") -> BytesIO:
    """Генерирует сравнительную диаграмму."""
    if not current and not previous:
        return generate_empty_chart("Нет данных для сравнения")

    all_categories = list(set(list(current.keys()) + list(previous.keys())))
    all_categories.sort()

    current_amounts = [current.get(cat, 0) for cat in all_categories]
    previous_amounts = [previous.get(cat, 0) for cat in all_categories]

    x = range(len(all_categories))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))

    bars1 = ax.bar([i - width/2 for i in x], previous_amounts, width, label='Прошлый месяц', color='#BDC3C7')
    bars2 = ax.bar([i + width/2 for i in x], current_amounts, width, label='Текущий месяц', color='#3498DB')

    ax.set_ylabel('Сумма (руб.)', fontsize=11)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(all_categories, rotation=45, ha='right')
    ax.legend()

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()

    return buf


def generate_balance_chart(transactions: list, title: str = "Динамика баланса") -> BytesIO:
    """Генерирует график изменения баланса."""
    if not transactions:
        return generate_empty_chart("Нет данных для отображения")

    dates = []
    balances = []

    for tx in transactions:
        try:
            date = datetime.strptime(tx.get("Date", tx.get("date", "")), "%Y-%m-%d")
            balance = float(tx.get("Balance", tx.get("balance", 0)))
            dates.append(date)
            balances.append(balance)
        except (ValueError, KeyError):
            continue

    if not dates:
        return generate_empty_chart("Нет данных для отображения")

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(dates, balances, color='#3498DB', linewidth=2, marker='o', markersize=4)
    ax.fill_between(dates, balances, alpha=0.3, color='#3498DB')

    ax.axhline(y=0, color='#E74C3C', linestyle='--', alpha=0.5)

    ax.set_xlabel('Дата', fontsize=11)
    ax.set_ylabel('Баланс (руб.)', fontsize=11)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.gcf().autofmt_xdate()
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()

    return buf


def generate_empty_chart(message: str) -> BytesIO:
    """Генерирует пустой график с сообщением."""
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=14, color='#7F8C8D')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()

    return buf


def generate_monthly_summary_chart(summary: dict, month_name: str, year: int) -> BytesIO:
    """Генерирует сводную диаграмму за месяц."""
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    balance = summary.get("balance", 0)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    ax1 = axes[0]
    categories = ['Доходы', 'Расходы']
    amounts = [income, expenses]
    colors = ['#2ECC71', '#E74C3C']

    bars = ax1.bar(categories, amounts, color=colors, width=0.5)

    for bar, amount in zip(bars, amounts):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(amounts) * 0.02,
            f'{int(amount):,} руб.'.replace(',', ' '),
            ha='center',
            fontsize=12,
            fontweight='bold'
        )

    balance_color = '#2ECC71' if balance >= 0 else '#E74C3C'
    ax1.axhline(y=0, color='#BDC3C7', linestyle='-', linewidth=0.5)
    ax1.set_title(f'Доходы и расходы\nБаланс: {int(balance):,} руб.'.replace(',', ' '),
                  fontsize=12, fontweight='bold', color=balance_color)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    ax2 = axes[1]
    by_category = summary.get("by_category", {})

    if by_category:
        sorted_cats = dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True))
        cat_names = list(sorted_cats.keys())
        cat_amounts = list(sorted_cats.values())
        cat_colors = [CATEGORY_COLORS.get(cat, "#BDC3C7") for cat in cat_names]

        if len(cat_names) > 5:
            other_sum = sum(cat_amounts[5:])
            cat_names = cat_names[:5] + ['Остальное']
            cat_amounts = cat_amounts[:5] + [other_sum]
            cat_colors = cat_colors[:5] + ['#BDC3C7']

        wedges, texts, autotexts = ax2.pie(
            cat_amounts,
            labels=cat_names,
            autopct='%1.1f%%',
            colors=cat_colors,
            startangle=90
        )
        ax2.set_title('Расходы по категориям', fontsize=12, fontweight='bold')
    else:
        ax2.text(0.5, 0.5, 'Нет расходов', ha='center', va='center', fontsize=12)
        ax2.axis('off')

    fig.suptitle(f'Финансовая сводка за {month_name} {year}', fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()

    return buf
