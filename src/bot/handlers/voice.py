import logging
from pathlib import Path

from telegram import Update
from telegram.error import BadRequest, TimedOut
from telegram.ext import ContextTypes

from src.bot.handlers.menu import is_user_allowed
from src.bot.handlers.text import process_transaction_text
from src.config import TEMP_AUDIO_DIR
from src.utils.metrics_decorator import track_request

logger = logging.getLogger(__name__)


async def safe_reply(message, text: str, reply_markup=None):
    try:
        return await message.reply_text(text, reply_markup=reply_markup)
    except TimedOut:
        logger.warning("Reply timeout, retrying once...")
        try:
            return await message.reply_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Reply retry failed: {e}")
            return None
    except BadRequest as e:
        logger.warning(f"BadRequest in reply: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in reply: {e}", exc_info=True)
        return None


@track_request("voice", "yandex_stt")
async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from src.utils.rate_limiter import check_rate_limit

    user = update.effective_user
    if not is_user_allowed(user.id):
        return

    if not check_rate_limit(user.id):
        await safe_reply(
            update.message, "Слишком много запросов. Подожди немного и попробуй снова."
        )
        return

    voice = update.message.voice
    if not voice:
        return

    processing_msg = await safe_reply(update.message, "Распознаю голосовое сообщение...")
    if not processing_msg:
        return

    file = await context.bot.get_file(voice.file_id)
    ogg_path = TEMP_AUDIO_DIR / f"{voice.file_unique_id}.ogg"
    await file.download_to_drive(ogg_path)

    text = await transcribe_audio(ogg_path)

    ogg_path.unlink(missing_ok=True)

    if not text:
        try:
            await processing_msg.edit_text(
                "Не удалось распознать речь. Попробуй ещё раз или напиши текстом."
            )
        except Exception as e:
            logger.warning(f"Failed to edit processing message: {e}")
            await safe_reply(
                update.message, "Не удалось распознать речь. Попробуй ещё раз или напиши текстом."
            )
        return

    try:
        await processing_msg.edit_text(f"Распознано: «{text}»")
    except Exception as e:
        logger.warning(f"Failed to edit processing message: {e}")
        await safe_reply(update.message, f"Распознано: «{text}»")

    await process_transaction_text(update, context, text)


async def transcribe_audio(audio_path: Path) -> str | None:
    """Транскрибирует аудио в текст через Whisper."""
    try:
        from src.services.speech import transcribe

        return await transcribe(audio_path)
    except ImportError:
        logger.warning("Speech service not available, using stub")
        return None
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None
