import asyncio
import gc
import logging
from typing import Optional

import psutil

logger = logging.getLogger(__name__)


class ResourceMonitor:
    def __init__(
        self,
        memory_threshold_mb: int = 500,
        cpu_threshold_percent: float = 80.0,
        check_interval: int = 300,
    ):
        self.memory_threshold_mb = memory_threshold_mb
        self.cpu_threshold_percent = cpu_threshold_percent
        self.check_interval = check_interval
        self.is_degraded = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start_monitoring(self):
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Resource monitoring started")

    async def stop_monitoring(self):
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("Resource monitoring stopped")

    async def _monitor_loop(self):
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_resources()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")

    async def _check_resources(self):
        loop = asyncio.get_event_loop()
        process = psutil.Process()

        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = await loop.run_in_executor(None, lambda: process.cpu_percent(interval=1.0))

        logger.info(f"Resource check: Memory={memory_mb:.1f}MB, CPU={cpu_percent:.1f}%")

        should_degrade = False

        if memory_mb > self.memory_threshold_mb:
            logger.warning(
                f"High memory usage detected: {memory_mb:.1f}MB > {self.memory_threshold_mb}MB"
            )
            should_degrade = True
            await self._trigger_gc()
        elif cpu_percent > self.cpu_threshold_percent:
            logger.warning(
                f"High CPU usage detected: {cpu_percent:.1f}% > {self.cpu_threshold_percent}%"
            )
            should_degrade = True

        if should_degrade and not self.is_degraded:
            from src.services.throttle import get_throttle_manager

            get_throttle_manager().enable_degraded_mode()
            self.is_degraded = True
        elif not should_degrade and self.is_degraded:
            from src.services.throttle import get_throttle_manager

            get_throttle_manager().disable_degraded_mode()
            logger.info("Resources back to normal, exiting degraded mode")
            self.is_degraded = False

    async def _trigger_gc(self):
        logger.info("Triggering garbage collection...")
        collected = gc.collect()
        logger.info(f"Garbage collection completed, collected {collected} objects")

        process = psutil.Process()
        new_memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"Memory after GC: {new_memory_mb:.1f}MB")

    def should_throttle(self) -> bool:
        return self.is_degraded


_resource_monitor = ResourceMonitor(memory_threshold_mb=400, cpu_threshold_percent=75.0)


def get_resource_monitor() -> ResourceMonitor:
    return _resource_monitor
