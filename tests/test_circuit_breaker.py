import pytest
import time
from unittest.mock import patch, AsyncMock

from src.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_yandex_circuit_breaker,
    get_sheets_circuit_breaker,
)


@pytest.fixture
def breaker():
    return CircuitBreaker(failure_threshold=3, recovery_timeout=10)


async def success_func():
    return "ok"


async def failing_func():
    raise Exception("service down")


class TestCircuitBreakerSuccess:
    @pytest.mark.asyncio
    async def test_success_keeps_closed(self, breaker):
        await breaker.call(success_func)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_success_returns_result(self, breaker):
        result = await breaker.call(success_func)
        assert result == "ok"


class TestCircuitBreakerFailures:
    @pytest.mark.asyncio
    async def test_failure_increments_count(self, breaker):
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        assert breaker.failure_count == 1
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failures_below_threshold_stay_closed(self, breaker):
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        assert breaker.failure_count == 2
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_threshold_failures_open_circuit(self, breaker):
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3


class TestCircuitBreakerOpen:
    @pytest.mark.asyncio
    async def test_open_blocks_calls(self, breaker):
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await breaker.call(success_func)

    @pytest.mark.asyncio
    async def test_open_transitions_to_half_open_after_timeout(self, breaker):
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        with patch("src.utils.circuit_breaker.time.time", return_value=time.time() + 11):
            result = await breaker.call(success_func)
            assert result == "ok"

        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerHalfOpen:
    @pytest.mark.asyncio
    async def test_success_in_half_open_closes(self, breaker):
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        breaker.state = CircuitState.HALF_OPEN
        await breaker.call(success_func)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failure_in_half_open_reopens(self, breaker):
        breaker.state = CircuitState.HALF_OPEN
        breaker.failure_count = 2

        with pytest.raises(Exception):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerRecovery:
    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, breaker):
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        assert breaker.failure_count == 2

        await breaker.call(success_func)
        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerExpectedException:
    @pytest.mark.asyncio
    async def test_unexpected_exception_not_counted(self):
        breaker = CircuitBreaker(failure_threshold=3, expected_exception=ValueError)

        async def raise_type_error():
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            await breaker.call(raise_type_error)

        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_expected_exception_counted(self):
        breaker = CircuitBreaker(failure_threshold=3, expected_exception=ValueError)

        async def raise_value_error():
            raise ValueError("bad value")

        with pytest.raises(ValueError):
            await breaker.call(raise_value_error)

        assert breaker.failure_count == 1


class TestGlobalBreakers:
    def test_yandex_breaker_has_lower_threshold_than_sheets(self):
        yandex = get_yandex_circuit_breaker()
        sheets = get_sheets_circuit_breaker()
        assert yandex.failure_threshold < sheets.failure_threshold

    def test_sheets_breaker_has_longer_recovery(self):
        yandex = get_yandex_circuit_breaker()
        sheets = get_sheets_circuit_breaker()
        assert sheets.recovery_timeout > yandex.recovery_timeout
