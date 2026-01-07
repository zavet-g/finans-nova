import logging
import asyncio
import time
from typing import Dict, Optional
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ThrottleConfig:
    max_requests_per_second: float = 10.0
    max_requests_per_minute: float = 100.0
    burst_size: int = 5


class RateLimiter:
    def __init__(self, config: ThrottleConfig):
        self.config = config
        self.requests_last_second: deque = deque(maxlen=int(config.max_requests_per_second * 2))
        self.requests_last_minute: deque = deque(maxlen=int(config.max_requests_per_minute * 2))
        self._lock = asyncio.Lock()

    async def acquire(self, wait: bool = True) -> bool:
        async with self._lock:
            now = time.time()

            self._cleanup_old_requests(now)

            second_count = sum(1 for t in self.requests_last_second if now - t < 1.0)
            minute_count = sum(1 for t in self.requests_last_minute if now - t < 60.0)

            if second_count >= self.config.max_requests_per_second:
                if not wait:
                    return False

                wait_time = 1.0 - (now - self.requests_last_second[0])
                logger.warning(f"Rate limit hit (per second), waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                return await self.acquire(wait=False)

            if minute_count >= self.config.max_requests_per_minute:
                if not wait:
                    return False

                wait_time = 60.0 - (now - self.requests_last_minute[0])
                logger.warning(f"Rate limit hit (per minute), waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                return await self.acquire(wait=False)

            self.requests_last_second.append(now)
            self.requests_last_minute.append(now)
            return True

    def _cleanup_old_requests(self, now: float):
        cutoff_second = now - 1.0
        while self.requests_last_second and self.requests_last_second[0] < cutoff_second:
            self.requests_last_second.popleft()

        cutoff_minute = now - 60.0
        while self.requests_last_minute and self.requests_last_minute[0] < cutoff_minute:
            self.requests_last_minute.popleft()


class ThrottleManager:
    def __init__(self):
        self.is_degraded = False
        self._normal_config = ThrottleConfig(
            max_requests_per_second=10.0,
            max_requests_per_minute=100.0,
            burst_size=5
        )
        self._degraded_config = ThrottleConfig(
            max_requests_per_second=2.0,
            max_requests_per_minute=30.0,
            burst_size=2
        )

        self.rate_limiters: Dict[str, RateLimiter] = {
            'voice': RateLimiter(self._normal_config),
            'text': RateLimiter(self._normal_config),
            'callback': RateLimiter(self._normal_config),
            'ai': RateLimiter(self._normal_config),
            'sheets': RateLimiter(self._normal_config),
        }

    def enable_degraded_mode(self):
        if self.is_degraded:
            return

        logger.warning("Enabling degraded mode - applying rate limits")
        self.is_degraded = True

        for operation_type in self.rate_limiters:
            self.rate_limiters[operation_type] = RateLimiter(self._degraded_config)

    def disable_degraded_mode(self):
        if not self.is_degraded:
            return

        logger.info("Disabling degraded mode - removing rate limits")
        self.is_degraded = False

        for operation_type in self.rate_limiters:
            self.rate_limiters[operation_type] = RateLimiter(self._normal_config)

    async def acquire(self, operation_type: str, wait: bool = True) -> bool:
        if operation_type not in self.rate_limiters:
            logger.warning(f"Unknown operation type: {operation_type}")
            return True

        limiter = self.rate_limiters[operation_type]
        return await limiter.acquire(wait=wait)


_throttle_manager = ThrottleManager()


def get_throttle_manager() -> ThrottleManager:
    return _throttle_manager
