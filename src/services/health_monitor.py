import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

from src.config import (
    YANDEX_GPT_API_KEY,
    YANDEX_GPT_FOLDER_ID,
    GOOGLE_SHEETS_SPREADSHEET_ID,
    GOOGLE_SHEETS_CREDENTIALS_FILE,
    TELEGRAM_BOT_TOKEN
)

logger = logging.getLogger(__name__)


class HealthMonitor:
    def __init__(self):
        self._last_health_check: Optional[datetime] = None
        self._cached_health: Dict[str, Any] = {}
        self._cache_ttl = 30

    async def check_yandex_gpt(self) -> Dict[str, Any]:
        if not YANDEX_GPT_API_KEY or not YANDEX_GPT_FOLDER_ID:
            return {
                "status": "not_configured",
                "message": "API ключ или folder_id не настроены",
                "healthy": False
            }

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "modelUri": f"gpt://{YANDEX_GPT_FOLDER_ID}/yandexgpt-lite",
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.1,
                        "maxTokens": 10
                    },
                    "messages": [
                        {
                            "role": "user",
                            "text": "ping"
                        }
                    ]
                }

                start_time = asyncio.get_event_loop().time()
                async with session.post(
                    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                    json=payload,
                    headers=headers
                ) as response:
                    duration = asyncio.get_event_loop().time() - start_time

                    if response.status == 200:
                        return {
                            "status": "healthy",
                            "message": "API доступен",
                            "response_time": round(duration, 3),
                            "healthy": True
                        }
                    else:
                        text = await response.text()
                        return {
                            "status": "degraded",
                            "message": f"HTTP {response.status}: {text[:100]}",
                            "healthy": False
                        }

        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "message": "Превышено время ожидания",
                "healthy": False
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка: {str(e)[:100]}",
                "healthy": False
            }

    async def check_yandex_stt(self) -> Dict[str, Any]:
        if not YANDEX_GPT_API_KEY:
            return {
                "status": "not_configured",
                "message": "API ключ не настроен",
                "healthy": False
            }

        return {
            "status": "configured",
            "message": "API ключ настроен",
            "healthy": True
        }

    async def check_google_sheets(self) -> Dict[str, Any]:
        if not GOOGLE_SHEETS_SPREADSHEET_ID:
            return {
                "status": "not_configured",
                "message": "Spreadsheet ID не настроен",
                "healthy": False
            }

        try:
            from pathlib import Path
            from src.config import BASE_DIR

            creds_path = Path(GOOGLE_SHEETS_CREDENTIALS_FILE)
            if not creds_path.is_absolute():
                creds_path = BASE_DIR / creds_path

            if not creds_path.exists():
                return {
                    "status": "error",
                    "message": "Файл credentials не найден",
                    "healthy": False
                }

            from src.services.sheets import get_spreadsheet

            loop = asyncio.get_event_loop()
            start_time = loop.time()

            spreadsheet = await loop.run_in_executor(None, get_spreadsheet)
            worksheets = await loop.run_in_executor(None, lambda: spreadsheet.worksheets())

            duration = loop.time() - start_time

            return {
                "status": "healthy",
                "message": f"Подключено, листов: {len(worksheets)}",
                "response_time": round(duration, 3),
                "healthy": True
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка: {str(e)[:100]}",
                "healthy": False
            }

    async def check_telegram_api(self) -> Dict[str, Any]:
        if not TELEGRAM_BOT_TOKEN:
            return {
                "status": "not_configured",
                "message": "Bot token не настроен",
                "healthy": False
            }

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                start_time = asyncio.get_event_loop().time()
                async with session.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
                ) as response:
                    duration = asyncio.get_event_loop().time() - start_time

                    if response.status == 200:
                        data = await response.json()
                        bot_username = data.get("result", {}).get("username", "unknown")
                        return {
                            "status": "healthy",
                            "message": f"Бот: @{bot_username}",
                            "response_time": round(duration, 3),
                            "healthy": True
                        }
                    else:
                        return {
                            "status": "error",
                            "message": f"HTTP {response.status}",
                            "healthy": False
                        }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка: {str(e)[:100]}",
                "healthy": False
            }

    async def check_all_services(self, force: bool = False) -> Dict[str, Dict[str, Any]]:
        now = datetime.now()

        if not force and self._last_health_check:
            elapsed = (now - self._last_health_check).total_seconds()
            if elapsed < self._cache_ttl and self._cached_health:
                return self._cached_health

        logger.info("Performing health check on all external services")

        results = await asyncio.gather(
            self.check_telegram_api(),
            self.check_yandex_gpt(),
            self.check_yandex_stt(),
            self.check_google_sheets(),
            return_exceptions=True
        )

        health_status = {
            "telegram": results[0] if not isinstance(results[0], Exception) else {
                "status": "error",
                "message": str(results[0]),
                "healthy": False
            },
            "yandex_gpt": results[1] if not isinstance(results[1], Exception) else {
                "status": "error",
                "message": str(results[1]),
                "healthy": False
            },
            "yandex_stt": results[2] if not isinstance(results[2], Exception) else {
                "status": "error",
                "message": str(results[2]),
                "healthy": False
            },
            "google_sheets": results[3] if not isinstance(results[3], Exception) else {
                "status": "error",
                "message": str(results[3]),
                "healthy": False
            }
        }

        self._cached_health = health_status
        self._last_health_check = now

        return health_status


_health_monitor = HealthMonitor()


def get_health_monitor() -> HealthMonitor:
    return _health_monitor
