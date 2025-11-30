import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


async def convert_ogg_to_wav(ogg_path: Path) -> Path:
    """Конвертирует OGG файл в WAV с помощью FFmpeg."""
    wav_path = ogg_path.with_suffix(".wav")

    cmd = [
        "ffmpeg",
        "-i", str(ogg_path),
        "-ar", "16000",
        "-ac", "1",
        "-y",
        str(wav_path)
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else "Unknown error"
        logger.error(f"FFmpeg conversion failed: {error_msg}")
        raise RuntimeError(f"FFmpeg conversion failed: {error_msg}")

    logger.info(f"Converted {ogg_path.name} to {wav_path.name}")
    return wav_path
