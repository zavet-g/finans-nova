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
    """Генерирует donut-диаграмму с легендой справа, отсортированной по убыванию."""
    if not data:
        return generate_empty_chart("Нет данных для отображения")

    total = sum(data.values())
    if total == 0:
        return generate_empty_chart("Нет расходов за период")

    sorted_data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
    categories = list(sorted_data.keys())
    amounts = list(sorted_data.values())

    colors = [CATEGORY_COLORS.get(cat, "#BDC3C7") for cat in categories]

    fig, (ax_pie, ax_legend) = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={'width_ratios': [1, 0.8]})

    wedges, texts, autotexts = ax_pie.pie(
        amounts,
        autopct=lambda pct: f'{pct:.1f}%' if pct > 5 else '',
        colors=colors,
        startangle=90,
        wedgeprops=dict(width=0.6, edgecolor='white', linewidth=2),
        pctdistance=0.75,
    )

    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_weight('bold')
        autotext.set_color('white')

    centre_circle = plt.Circle((0, 0), 0.35, fc='white')
    ax_pie.add_patch(centre_circle)

    ax_pie.text(0, 0, f'{int(total):,}\nруб.'.replace(',', ' '),
                ha='center', va='center', fontsize=14, fontweight='bold', color='#2C3E50')

    ax_pie.set_title(title, fontsize=14, fontweight='bold', pad=20)

    ax_legend.axis('off')

    legend_items = []
    for i, (cat, amount) in enumerate(zip(categories, amounts)):
        pct = (amount / total) * 100
        legend_items.append({
            'color': colors[i],
            'category': cat,
            'amount': amount,
            'pct': pct
        })

    y_start = 0.95
    y_step = 0.08
    for i, item in enumerate(legend_items):
        y_pos = y_start - i * y_step

        ax_legend.add_patch(plt.Rectangle((0.05, y_pos - 0.025), 0.08, 0.05,
                                           facecolor=item['color'], edgecolor='none',
                                           transform=ax_legend.transAxes))

        ax_legend.text(0.18, y_pos, item['category'],
                      fontsize=11, fontweight='bold', va='center',
                      transform=ax_legend.transAxes)

        ax_legend.text(0.95, y_pos, f"{int(item['amount']):,} руб. ({item['pct']:.1f}%)".replace(',', ' '),
                      fontsize=10, va='center', ha='right',
                      transform=ax_legend.transAxes, color='#7F8C8D')

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
    """Генерирует сводную диаграмму за месяц с donut-chart."""
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    balance = summary.get("balance", 0)

    fig = plt.figure(figsize=(16, 7))

    ax1 = fig.add_subplot(1, 3, 1)
    categories = ['Доходы', 'Расходы']
    amounts = [income, expenses]
    colors = ['#2ECC71', '#E74C3C']

    bars = ax1.bar(categories, amounts, color=colors, width=0.5)

    for bar, amount in zip(bars, amounts):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(amounts) * 0.02 if amounts else 0,
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

    ax2 = fig.add_subplot(1, 3, 2)
    by_category = summary.get("by_category", {})

    if by_category:
        sorted_cats = dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True))
        cat_names = list(sorted_cats.keys())
        cat_amounts = list(sorted_cats.values())
        cat_colors = [CATEGORY_COLORS.get(cat, "#BDC3C7") for cat in cat_names]

        if len(cat_names) > 6:
            other_sum = sum(cat_amounts[6:])
            cat_names = cat_names[:6] + ['Остальное']
            cat_amounts = cat_amounts[:6] + [other_sum]
            cat_colors = cat_colors[:6] + ['#BDC3C7']

        total_expenses = sum(cat_amounts)

        wedges, texts, autotexts = ax2.pie(
            cat_amounts,
            autopct=lambda pct: f'{pct:.0f}%' if pct > 8 else '',
            colors=cat_colors,
            startangle=90,
            wedgeprops=dict(width=0.55, edgecolor='white', linewidth=2),
            pctdistance=0.75,
        )

        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_weight('bold')
            autotext.set_color('white')

        centre_circle = plt.Circle((0, 0), 0.4, fc='white')
        ax2.add_patch(centre_circle)

        ax2.text(0, 0, f'{int(total_expenses):,}'.replace(',', ' '),
                 ha='center', va='center', fontsize=12, fontweight='bold', color='#2C3E50')

        ax2.set_title('Расходы', fontsize=12, fontweight='bold')

        ax3 = fig.add_subplot(1, 3, 3)
        ax3.axis('off')

        y_start = 0.9
        y_step = 0.12
        for i, (name, amount) in enumerate(zip(cat_names, cat_amounts)):
            y_pos = y_start - i * y_step
            pct = (amount / total_expenses) * 100 if total_expenses > 0 else 0

            ax3.add_patch(plt.Rectangle((0.05, y_pos - 0.03), 0.08, 0.06,
                                        facecolor=cat_colors[i], edgecolor='none',
                                        transform=ax3.transAxes))

            ax3.text(0.18, y_pos, name,
                    fontsize=10, fontweight='bold', va='center',
                    transform=ax3.transAxes)

            ax3.text(0.95, y_pos, f"{int(amount):,} ({pct:.1f}%)".replace(',', ' '),
                    fontsize=9, va='center', ha='right',
                    transform=ax3.transAxes, color='#7F8C8D')
    else:
        ax2.text(0.5, 0.5, 'Нет расходов', ha='center', va='center', fontsize=12)
        ax2.axis('off')

    fig.suptitle(f'Финансовая сводка за {month_name} {year}', fontsize=14, fontweight='bold', y=0.98)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close()

    return buf


def generate_yearly_income_chart(monthly_data: dict, year: int) -> BytesIO:
    """Генерирует столбчатую диаграмму доходов по месяцам за год."""
    from src.utils.formatters import MONTHS_RU_SHORT

    months = list(range(1, 13))
    amounts = [monthly_data.get(m, 0) for m in months]
    labels = [MONTHS_RU_SHORT[m] for m in months]

    total = sum(amounts)
    if total == 0:
        return generate_empty_chart("Нет данных о доходах за год")

    non_zero = [a for a in amounts if a > 0]
    avg = total / len(non_zero) if non_zero else 0
    max_val = max(amounts)

    fig, ax = plt.subplots(figsize=(14, 7))

    bars = ax.bar(
        labels, amounts,
        color="#2ECC71",
        width=0.65,
        edgecolor="white",
        linewidth=0.8,
        zorder=3,
    )

    for bar, amount in zip(bars, amounts):
        if amount > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_val * 0.02,
                f"{int(amount):,}".replace(",", " "),
                ha="center", va="bottom",
                fontsize=9, fontweight="bold", color="#2C3E50",
            )

    ax.axhline(
        y=avg, color="#27AE60", linestyle="--",
        linewidth=1.5, alpha=0.7, zorder=2,
        label=f"Среднее: {int(avg):,} руб.".replace(",", " "),
    )

    ax.set_title(
        f"Доходы по месяцам за {year} год",
        fontsize=16, fontweight="bold", color="#2C3E50", pad=20,
    )
    ax.text(
        0.5, 1.02,
        f"Итого за год: {int(total):,} руб.".replace(",", " "),
        transform=ax.transAxes, ha="center",
        fontsize=12, color="#7F8C8D",
    )

    ax.set_ylabel("Сумма (руб.)", fontsize=12, color="#2C3E50")

    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", " "))
    )

    ax.grid(axis="y", alpha=0.3, linestyle="-", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#BDC3C7")
    ax.spines["bottom"].set_color("#BDC3C7")

    ax.tick_params(axis="x", labelsize=11, colors="#2C3E50")
    ax.tick_params(axis="y", labelsize=10, colors="#7F8C8D")

    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    plt.close()

    return buf


def generate_yearly_expense_chart(monthly_data: dict, year: int) -> BytesIO:
    """Генерирует столбчатую диаграмму расходов по месяцам за год."""
    from src.utils.formatters import MONTHS_RU_SHORT

    months = list(range(1, 13))
    amounts = [monthly_data.get(m, 0) for m in months]
    labels = [MONTHS_RU_SHORT[m] for m in months]

    total = sum(amounts)
    if total == 0:
        return generate_empty_chart("Нет данных о расходах за год")

    non_zero = [a for a in amounts if a > 0]
    avg = total / len(non_zero) if non_zero else 0
    max_val = max(amounts)

    fig, ax = plt.subplots(figsize=(14, 7))

    bars = ax.bar(
        labels, amounts,
        color="#E74C3C",
        width=0.65,
        edgecolor="white",
        linewidth=0.8,
        zorder=3,
    )

    for bar, amount in zip(bars, amounts):
        if amount > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_val * 0.02,
                f"{int(amount):,}".replace(",", " "),
                ha="center", va="bottom",
                fontsize=9, fontweight="bold", color="#2C3E50",
            )

    ax.axhline(
        y=avg, color="#C0392B", linestyle="--",
        linewidth=1.5, alpha=0.7, zorder=2,
        label=f"Среднее: {int(avg):,} руб.".replace(",", " "),
    )

    ax.set_title(
        f"Расходы по месяцам за {year} год",
        fontsize=16, fontweight="bold", color="#2C3E50", pad=20,
    )
    ax.text(
        0.5, 1.02,
        f"Итого за год: {int(total):,} руб.".replace(",", " "),
        transform=ax.transAxes, ha="center",
        fontsize=12, color="#7F8C8D",
    )

    ax.set_ylabel("Сумма (руб.)", fontsize=12, color="#2C3E50")

    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", " "))
    )

    ax.grid(axis="y", alpha=0.3, linestyle="-", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#BDC3C7")
    ax.spines["bottom"].set_color("#BDC3C7")

    ax.tick_params(axis="x", labelsize=11, colors="#2C3E50")
    ax.tick_params(axis="y", labelsize=10, colors="#7F8C8D")

    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    plt.close()

    return buf
