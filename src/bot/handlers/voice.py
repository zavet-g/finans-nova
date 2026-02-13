import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.handlers.menu import is_user_allowed
from src.bot.handlers.text import process_transaction_text
from src.bot.message_manager import delete_user_message, update_main_message
from src.config import TEMP_AUDIO_DIR
from src.utils.metrics_decorator import track_request

logger = logging.getLogger(__name__)


@track_request("voice", "yandex_stt")
async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from src.utils.rate_limiter import check_rate_limit

    user = update.effective_user
    if not is_user_allowed(user.id):
        return

    chat_id = update.effective_chat.id
    await delete_user_message(update.message)

    if not check_rate_limit(user.id):
        await update_main_message(
            context, chat_id, text="Слишком много запросов. Подожди немного и попробуй снова."
        )
        return

    voice = update.message.voice
    if not voice:
        return

    await update_main_message(context, chat_id, text="Распознаю голосовое сообщение...")

    file = await context.bot.get_file(voice.file_id)
    ogg_path = TEMP_AUDIO_DIR / f"{voice.file_unique_id}.ogg"
    await file.download_to_drive(ogg_path)

    text = await transcribe_audio(ogg_path)
    ogg_path.unlink(missing_ok=True)

    if not text:
        await update_main_message(
            context,
            chat_id,
            text="Не удалось распознать речь. Попробуй ещё раз или напиши текстом.",
        )
        return

    await update_main_message(context, chat_id, text=f"Распознано: «{text}»\n\nАнализирую...")
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
