import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes

from src.config import TEMP_AUDIO_DIR
from src.bot.handlers.menu import is_user_allowed
from src.bot.handlers.text import process_transaction_text

logger = logging.getLogger(__name__)


async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик голосовых сообщений."""
    user = update.effective_user
    if not is_user_allowed(user.id):
        return

    voice = update.message.voice
    if not voice:
        return

    processing_msg = await update.message.reply_text("Распознаю голосовое сообщение...")

    try:
        file = await context.bot.get_file(voice.file_id)
        ogg_path = TEMP_AUDIO_DIR / f"{voice.file_unique_id}.ogg"
        await file.download_to_drive(ogg_path)

        text = await transcribe_audio(ogg_path)

        ogg_path.unlink(missing_ok=True)

        if not text:
            await processing_msg.edit_text(
                "Не удалось распознать речь. Попробуй ещё раз или напиши текстом."
            )
            return

        await processing_msg.edit_text(f"Распознано: «{text}»")

        await process_transaction_text(update, context, text)

    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await processing_msg.edit_text(
            "Произошла ошибка при обработке голосового сообщения. Попробуй позже."
        )


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
