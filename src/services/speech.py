import logging
import asyncio
import aiohttp
from pathlib import Path

from src.config import YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID
from src.utils.audio import convert_ogg_to_pcm

logger = logging.getLogger(__name__)

SPEECHKIT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
MAX_RETRIES = 3

_speech_session: aiohttp.ClientSession | None = None


async def get_speech_session() -> aiohttp.ClientSession:
    global _speech_session
    if _speech_session is None or _speech_session.closed:
        timeout = aiohttp.ClientTimeout(
            total=120,
            connect=30,
            sock_read=60
        )
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            ttl_dns_cache=300,
            force_close=False,
            enable_cleanup_closed=True
        )
        _speech_session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            raise_for_status=False
        )
        logger.info("SpeechKit session created")
    return _speech_session


async def close_speech_session():
    global _speech_session
    if _speech_session and not _speech_session.closed:
        await _speech_session.close()
        _speech_session = None
        logger.info("SpeechKit session closed")


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

        logger.info(f"Audio size: {len(audio_data)} bytes")

        headers = {
            "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
        }

        params = {
            "folderId": YANDEX_GPT_FOLDER_ID,
            "lang": "ru-RU",
            "format": "lpcm",
            "sampleRateHertz": 16000,
        }

        session = await get_speech_session()

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"SpeechKit request attempt {attempt}/{MAX_RETRIES}")
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
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(f"SpeechKit attempt {attempt} failed: {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)

        logger.error(f"SpeechKit failed after {MAX_RETRIES} attempts: {last_error}")
        return None

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return None
