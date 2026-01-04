import logging
import asyncio
import psutil
import time
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self):
        self.start_time = time.time()
        self.last_error_time = None
        self.error_count = 0
        self.request_count = 0
        self.success_count = 0

    def get_uptime(self) -> float:
        return time.time() - self.start_time

    def record_request(self, success: bool = True):
        self.request_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            self.last_error_time = time.time()

    def get_health_status(self) -> Dict[str, Any]:
        uptime_seconds = self.get_uptime()
        memory = psutil.Process().memory_info()

        error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0

        status = {
            "status": "healthy" if error_rate < 5 else "degraded" if error_rate < 20 else "unhealthy",
            "uptime_seconds": int(uptime_seconds),
            "uptime_hours": round(uptime_seconds / 3600, 2),
            "memory_mb": round(memory.rss / 1024 / 1024, 2),
            "memory_percent": round(psutil.Process().memory_percent(), 2),
            "cpu_percent": round(psutil.Process().cpu_percent(interval=0.1), 2),
            "requests": {
                "total": self.request_count,
                "success": self.success_count,
                "errors": self.error_count,
                "error_rate": round(error_rate, 2)
            },
            "last_error": datetime.fromtimestamp(self.last_error_time).isoformat() if self.last_error_time else None,
            "timestamp": datetime.now().isoformat()
        }

        return status

    async def check_external_services(self) -> Dict[str, str]:
        results = {}

        try:
            from src.config import YANDEX_GPT_API_KEY, GOOGLE_SHEETS_SPREADSHEET_ID
            results["yandex_api"] = "configured" if YANDEX_GPT_API_KEY else "missing"
            results["google_sheets"] = "configured" if GOOGLE_SHEETS_SPREADSHEET_ID else "missing"
        except Exception as e:
            logger.error(f"Error checking external services: {e}")
            results["error"] = str(e)

        return results


_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    return _health_checker
