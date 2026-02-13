import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    total_calls: int = 0
    success_calls: int = 0
    failed_calls: int = 0
    avg_response_time: float = 0.0
    last_error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        if self.total_calls == 0:
            return True
        success_rate = self.success_calls / self.total_calls
        return success_rate >= 0.95

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 100.0
        return (self.success_calls / self.total_calls) * 100


@dataclass
class RequestMetrics:
    count: int = 0
    success: int = 0
    errors: int = 0
    total_duration: float = 0.0

    @property
    def avg_duration(self) -> float:
        return self.total_duration / self.count if self.count > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return (self.success / self.count * 100) if self.count > 0 else 100.0


class MetricsCollector:
    def __init__(self):
        self.start_time = time.time()

        self.services: Dict[str, ServiceStatus] = {
            "yandex_gpt": ServiceStatus(),
            "yandex_stt": ServiceStatus(),
            "google_sheets": ServiceStatus(),
            "telegram": ServiceStatus(),
        }

        self.request_types: Dict[str, RequestMetrics] = defaultdict(RequestMetrics)

        self.response_times: deque = deque(maxlen=1000)

        self.cpu_samples: deque = deque(maxlen=60)
        self.memory_samples: deque = deque(maxlen=60)

        self._cpu_monitor_task: Optional[asyncio.Task] = None
        self._process = psutil.Process()

    async def start(self):
        self._cpu_monitor_task = asyncio.create_task(self._monitor_resources())
        logger.info("Metrics collector started")

    async def stop(self):
        if self._cpu_monitor_task:
            self._cpu_monitor_task.cancel()
            try:
                await self._cpu_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collector stopped")

    async def _monitor_resources(self):
        while True:
            try:
                await asyncio.sleep(5)

                loop = asyncio.get_event_loop()
                cpu = await loop.run_in_executor(
                    None, lambda: self._process.cpu_percent(interval=1.0)
                )
                memory = self._process.memory_info().rss / 1024 / 1024

                self.cpu_samples.append(cpu)
                self.memory_samples.append(memory)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")

    def record_request(self, request_type: str, duration: float, success: bool = True):
        metrics = self.request_types[request_type]
        metrics.count += 1
        metrics.total_duration += duration

        if success:
            metrics.success += 1
        else:
            metrics.errors += 1

        self.response_times.append(duration)

    def record_service_call(
        self, service: str, success: bool, duration: float, error: Optional[str] = None
    ):
        if service not in self.services:
            logger.warning(f"Unknown service: {service}")
            return

        status = self.services[service]
        status.total_calls += 1

        if success:
            status.success_calls += 1
            status.last_success = datetime.now()
        else:
            status.failed_calls += 1
            status.last_failure = datetime.now()
            status.last_error = error

        if status.total_calls == 1:
            status.avg_response_time = duration
        else:
            status.avg_response_time = (
                status.avg_response_time * (status.total_calls - 1) + duration
            ) / status.total_calls

    def get_uptime(self) -> float:
        return time.time() - self.start_time

    def get_cpu_percent(self) -> float:
        if not self.cpu_samples:
            return 0.0
        return sum(self.cpu_samples) / len(self.cpu_samples)

    def get_memory_mb(self) -> float:
        if not self.memory_samples:
            return self._process.memory_info().rss / 1024 / 1024
        return sum(self.memory_samples) / len(self.memory_samples)

    def get_response_time_percentiles(self) -> Dict[str, float]:
        if not self.response_times:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        sorted_times = sorted(self.response_times)
        count = len(sorted_times)

        return {
            "p50": sorted_times[int(count * 0.50)] if count > 0 else 0.0,
            "p95": sorted_times[int(count * 0.95)] if count > 0 else 0.0,
            "p99": sorted_times[int(count * 0.99)] if count > 0 else 0.0,
        }

    def get_overall_health(self) -> str:
        unhealthy_services = [
            name
            for name, status in self.services.items()
            if not status.is_healthy and status.total_calls > 0
        ]

        if not unhealthy_services:
            return "healthy"

        if len(unhealthy_services) >= 2:
            return "unhealthy"

        return "degraded"

    def get_metrics_summary(self) -> Dict[str, Any]:
        uptime = self.get_uptime()

        total_requests = sum(m.count for m in self.request_types.values())
        total_success = sum(m.success for m in self.request_types.values())
        total_errors = sum(m.errors for m in self.request_types.values())

        return {
            "status": self.get_overall_health(),
            "uptime_seconds": int(uptime),
            "memory_mb": round(self.get_memory_mb(), 2),
            "memory_percent": round(self._process.memory_percent(), 2),
            "cpu_percent": round(self.get_cpu_percent(), 2),
            "requests": {
                "total": total_requests,
                "success": total_success,
                "errors": total_errors,
                "success_rate": round(
                    (total_success / total_requests * 100) if total_requests > 0 else 100.0, 2
                ),
            },
            "response_times": self.get_response_time_percentiles(),
            "timestamp": datetime.now().isoformat(),
        }

    def get_services_status(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "healthy": status.is_healthy,
                "total_calls": status.total_calls,
                "success_rate": round(status.success_rate, 2),
                "avg_response_time": round(status.avg_response_time, 3),
                "last_success": status.last_success.isoformat() if status.last_success else None,
                "last_failure": status.last_failure.isoformat() if status.last_failure else None,
                "last_error": status.last_error,
            }
            for name, status in self.services.items()
        }

    def get_request_types_stats(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "count": metrics.count,
                "success": metrics.success,
                "errors": metrics.errors,
                "avg_duration": round(metrics.avg_duration, 3),
                "success_rate": round(metrics.success_rate, 2),
            }
            for name, metrics in self.request_types.items()
            if metrics.count > 0
        }


_metrics_collector = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _metrics_collector
