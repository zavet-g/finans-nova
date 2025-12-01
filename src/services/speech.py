import logging
import aiohttp
from pathlib import Path

from src.config import YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID
from src.utils.audio import convert_ogg_to_pcm

logger = logging.getLogger(__name__)

SPEECHKIT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"


async def transcribe(audio_path: Path) -> str | None:
    """Транскрибирует аудио через Yandex SpeechKit."""
    if not YANDEX_GPT_API_KEY or not YANDEX_GPT_FOLDER_ID:
        logger.error("Yandex credentials not configured")
        return None

    try:
        pcm_path = await convert_ogg_to_pcm(audio_path)

        with open(pcm_path, "rb") as f:
            audio_data = f.read()

        pcm_path.unlink(missing_ok=True)

        headers = {
            "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
        }

        params = {
            "folderId": YANDEX_GPT_FOLDER_ID,
            "lang": "ru-RU",
            "format": "lpcm",
            "sampleRateHertz": 16000,
        }

        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                SPEECHKIT_URL,
                headers=headers,
                params=params,
                data=audio_data,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"SpeechKit error: {response.status} - {error_text}")
                    return None

                result = await response.json()
                text = result.get("result", "").strip()
                logger.info(f"SpeechKit transcribed: {text[:100]}...")
                return text if text else None

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return None
