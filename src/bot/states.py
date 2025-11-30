from enum import IntEnum, auto


class ConversationState(IntEnum):
    """Состояния диалога с пользователем."""

    MAIN_MENU = auto()
    CONFIRM_TRANSACTION = auto()
    EDIT_TRANSACTION = auto()
    SELECT_CATEGORY = auto()
    ENTER_AMOUNT = auto()
    ENTER_DESCRIPTION = auto()
    SELECT_PERIOD = auto()
    ENTER_CUSTOM_DATE_START = auto()
    ENTER_CUSTOM_DATE_END = auto()
