import pytest

from src.services.throttle import ThrottleConfig, RateLimiter, ThrottleManager


@pytest.fixture
def manager():
    return ThrottleManager()


@pytest.fixture
def strict_config():
    return ThrottleConfig(max_requests_per_second=3.0, max_requests_per_minute=10.0, burst_size=2)


class TestThrottleManager:
    def test_initial_not_degraded(self, manager):
        assert manager.is_degraded is False

    def test_enable_degraded_mode(self, manager):
        manager.enable_degraded_mode()
        assert manager.is_degraded is True

    def test_enable_degraded_idempotent(self, manager):
        manager.enable_degraded_mode()
        manager.enable_degraded_mode()
        assert manager.is_degraded is True

    def test_disable_degraded_mode(self, manager):
        manager.enable_degraded_mode()
        manager.disable_degraded_mode()
        assert manager.is_degraded is False

    def test_disable_degraded_idempotent(self, manager):
        manager.disable_degraded_mode()
        assert manager.is_degraded is False

    def test_has_all_operation_types(self, manager):
        expected = {"voice", "text", "callback", "ai", "sheets"}
        assert set(manager.rate_limiters.keys()) == expected

    @pytest.mark.asyncio
    async def test_acquire_known_operation(self, manager):
        result = await manager.acquire("text", wait=False)
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_unknown_operation(self, manager):
        result = await manager.acquire("unknown_type", wait=False)
        assert result is True

    def test_degraded_reduces_limits(self, manager):
        normal_rate = manager.rate_limiters["text"].config.max_requests_per_second
        manager.enable_degraded_mode()
        degraded_rate = manager.rate_limiters["text"].config.max_requests_per_second
        assert degraded_rate < normal_rate

    def test_disable_restores_config(self, manager):
        normal_rate = manager.rate_limiters["text"].config.max_requests_per_second
        manager.enable_degraded_mode()
        manager.disable_degraded_mode()
        restored_rate = manager.rate_limiters["text"].config.max_requests_per_second
        assert restored_rate == normal_rate


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_allows_within_limit(self, strict_config):
        limiter = RateLimiter(strict_config)
        results = []
        for _ in range(3):
            results.append(await limiter.acquire(wait=False))
        assert all(results)

    @pytest.mark.asyncio
    async def test_blocks_over_per_second_limit(self, strict_config):
        limiter = RateLimiter(strict_config)
        for _ in range(3):
            await limiter.acquire(wait=False)
        result = await limiter.acquire(wait=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_blocks_over_per_minute_limit(self):
        config = ThrottleConfig(max_requests_per_second=100.0, max_requests_per_minute=5.0, burst_size=5)
        limiter = RateLimiter(config)

        for _ in range(5):
            await limiter.acquire(wait=False)

        result = await limiter.acquire(wait=False)
        assert result is False


