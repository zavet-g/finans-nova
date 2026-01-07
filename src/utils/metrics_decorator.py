import logging
import time
import functools
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes

from src.services.metrics import get_metrics
from src.services.throttle import get_throttle_manager

logger = logging.getLogger(__name__)


def track_request(request_type: str, service: str = None):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
            metrics = get_metrics()
            throttle = get_throttle_manager()

            await throttle.acquire(request_type)

            start_time = time.time()
            success = False
            error_msg = None

            try:
                result = await func(update, context, *args, **kwargs)
                success = True
                return result

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                raise

            finally:
                duration = time.time() - start_time

                metrics.record_request(request_type, duration, success)

                if service:
                    metrics.record_service_call(service, success, duration, error_msg)

        return wrapper
    return decorator


def track_service_call(service: str):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            metrics = get_metrics()

            start_time = time.time()
            success = False
            error_msg = None

            try:
                result = await func(*args, **kwargs)
                success = True
                return result

            except Exception as e:
                error_msg = str(e)
                raise

            finally:
                duration = time.time() - start_time
                metrics.record_service_call(service, success, duration, error_msg)

        return wrapper
    return decorator
