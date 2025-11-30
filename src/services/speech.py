import logging
import asyncio
from pathlib import Path

from src.config import WHISPER_MODEL
from src.utils.audio import convert_ogg_to_wav

logger = logging.getLogger(__name__)

_model = None


def get_whisper_model():
    """Загружает модель Whisper (lazy loading)."""
    global _model
    if _model is None:
        import whisper
        logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
        _model = whisper.load_model(WHISPER_MODEL)
        logger.info("Whisper model loaded")
    return _model


async def transcribe(audio_path: Path) -> str | None:
    """Транскрибирует аудио файл в текст."""
    try:
        wav_path = await convert_ogg_to_wav(audio_path)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _transcribe_sync,
            wav_path
        )

        wav_path.unlink(missing_ok=True)

        return result

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return None


def _transcribe_sync(audio_path: Path) -> str | None:
    """Синхронная транскрипция для выполнения в executor."""
    try:
        model = get_whisper_model()

        result = model.transcribe(
            str(audio_path),
            language="ru",
            task="transcribe",
        )

        text = result.get("text", "").strip()
        logger.info(f"Transcribed: {text[:100]}...")
        return text if text else None

    except Exception as e:
        logger.error(f"Whisper transcription error: {e}")
        return None
