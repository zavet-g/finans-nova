from datetime import datetime
from pydantic import BaseModel, Field
from .category import TransactionType


class Transaction(BaseModel):
    """Модель финансовой транзакции."""

    tx_id: int | None = None
    date: datetime = Field(default_factory=datetime.now)
    type: TransactionType
    category: str
    description: str
    amount: float = Field(gt=0)
    confirmed: bool = False

    def to_sheets_row(self) -> list:
        """Конвертирует транзакцию в строку для Google Sheets."""
        return [
            self.date.strftime("%Y-%m-%d"),
            self.date.strftime("%H:%M"),
            self.tx_id or "",
            self.type.value,
            self.category,
            self.description,
            self.amount,
            "",
            self.date.year,
            self.date.month,
            "Да" if self.confirmed else "Нет",
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ]

    def format_for_user(self) -> str:
        """Форматирует транзакцию для отображения пользователю."""
        type_emoji = "📥" if self.type == TransactionType.INCOME else "📤"
        sign = "+" if self.type == TransactionType.INCOME else "-"
        return (
            f"{type_emoji} {self.description}\n"
            f"Категория: {self.category}\n"
            f"Сумма: {sign}{self.amount:,.0f} руб."
        )
