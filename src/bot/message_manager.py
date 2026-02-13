import asyncio
import logging

from telegram import Message, ReplyKeyboardMarkup
from telegram.error import BadRequest, TimedOut

logger = logging.getLogger(__name__)

MAIN_MSG_KEY = "main_message_id"
MAIN_MSG_TYPE_KEY = "main_message_type"
REPLY_KB_READY_KEY = "reply_keyboard_ready"
REPLY_KEYBOARD_TEXT = "Главное меню"

EFFECT_CELEBRATE = "5046509860389126442"
EFFECT_THUMBS_UP = "5107584321108051014"
EFFECT_FIRE = "5104841245755180586"
EFFECT_HEART = "5159385139981059251"

_user_locks: dict[int, asyncio.Lock] = {}


def _get_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _user_locks:
        _user_locks[chat_id] = asyncio.Lock()
    return _user_locks[chat_id]


async def delete_user_message(message) -> None:
    """Удаляет сообщение пользователя из чата."""
    if not message:
        return
    try:
        await message.delete()
    except Exception:
        pass


async def setup_reply_keyboard(context, chat_id: int) -> None:
    """Устанавливает ReplyKeyboard внизу экрана.

    Отправляет временное сообщение с ReplyKeyboard, затем удаляет его.
    ReplyKeyboard сохраняется на клиенте после удаления сообщения.
    """
    if context.user_data.get(REPLY_KB_READY_KEY):
        return
    try:
        reply_kb = ReplyKeyboardMarkup(
            [[REPLY_KEYBOARD_TEXT]],
            resize_keyboard=True,
            input_field_placeholder="Расход или доход...",
        )
        msg = await context.bot.send_message(
            chat_id=chat_id, text="Настраиваю меню...", reply_markup=reply_kb
        )
        context.user_data[REPLY_KB_READY_KEY] = True
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Could not setup reply keyboard: {e}")


async def update_main_message(
    context,
    chat_id: int,
    text: str = None,
    reply_markup=None,
    photo=None,
    document=None,
    filename=None,
    caption=None,
    show_caption_above_media: bool = None,
    message_effect_id: str = None,
) -> Message | None:
    """Обновляет единственное сообщение бота в чате."""
    async with _get_lock(chat_id):
        return await _do_update(
            context,
            chat_id,
            text,
            reply_markup,
            photo,
            document,
            filename,
            caption,
            show_caption_above_media,
            message_effect_id,
        )


async def _do_update(
    context,
    chat_id,
    text,
    reply_markup,
    photo,
    document,
    filename,
    caption,
    show_caption_above_media=None,
    message_effect_id=None,
) -> Message | None:
    bot = context.bot
    user_data = context.user_data
    old_msg_id = user_data.get(MAIN_MSG_KEY)
    old_msg_type = user_data.get(MAIN_MSG_TYPE_KEY, "text")

    new_type = "text"
    if photo:
        new_type = "photo"
    elif document:
        new_type = "document"

    can_edit = old_msg_id and old_msg_type == new_type == "text" and not message_effect_id

    if can_edit:
        try:
            msg = await bot.edit_message_text(
                chat_id=chat_id,
                message_id=old_msg_id,
                text=text,
                reply_markup=reply_markup,
            )
            if isinstance(msg, Message):
                user_data[MAIN_MSG_KEY] = msg.message_id
            return msg
        except BadRequest as e:
            error_msg = str(e).lower()
            if "message is not modified" in error_msg:
                return None
            logger.warning(f"Cannot edit main message: {e}, resending")
        except TimedOut:
            logger.warning("Edit main message timeout, resending")
        except Exception as e:
            logger.warning(f"Edit main message failed: {e}, resending")

    msg = None
    try:
        if photo:
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                reply_markup=reply_markup,
                show_caption_above_media=show_caption_above_media,
                message_effect_id=message_effect_id,
            )
        elif document:
            msg = await bot.send_document(
                chat_id=chat_id,
                document=document,
                filename=filename,
                caption=caption,
                reply_markup=reply_markup,
                message_effect_id=message_effect_id,
            )
        else:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                message_effect_id=message_effect_id,
            )

        user_data[MAIN_MSG_KEY] = msg.message_id
        user_data[MAIN_MSG_TYPE_KEY] = new_type
    except Exception as e:
        logger.error(f"Failed to send main message: {e}")
        return None

    if old_msg_id and msg and old_msg_id != msg.message_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=old_msg_id)
        except Exception:
            pass

    return msg
