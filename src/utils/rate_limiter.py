import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.last_cleanup = time.time()

    def is_allowed(self, user_id: int) -> bool:
        current_time = time.time()

        if current_time - self.last_cleanup > 300:
            self._cleanup_old_entries()
            self.last_cleanup = current_time

        user_requests = self.requests[user_id]

        cutoff_time = current_time - self.window_seconds
        user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff_time]

        if len(user_requests) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}: {len(user_requests)} requests in {self.window_seconds}s")
            return False

        user_requests.append(current_time)
        return True

    def _cleanup_old_entries(self):
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        users_to_remove = []
        for user_id, requests in self.requests.items():
            requests[:] = [req_time for req_time in requests if req_time > cutoff_time]
            if not requests:
                users_to_remove.append(user_id)

        for user_id in users_to_remove:
            del self.requests[user_id]

        if users_to_remove:
            logger.debug(f"Cleaned up {len(users_to_remove)} inactive users from rate limiter")


_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)


def check_rate_limit(user_id: int) -> bool:
    return _rate_limiter.is_allowed(user_id)
