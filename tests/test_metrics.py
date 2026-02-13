import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.services.metrics import ServiceStatus, RequestMetrics, MetricsCollector


class TestServiceStatus:
    def test_healthy_at_95_percent(self):
        status = ServiceStatus(total_calls=20, success_calls=19, failed_calls=1)
        assert status.is_healthy is True

    def test_unhealthy_below_95_percent(self):
        status = ServiceStatus(total_calls=20, success_calls=18, failed_calls=2)
        assert status.is_healthy is False

    def test_success_rate_mixed(self):
        status = ServiceStatus(total_calls=10, success_calls=8, failed_calls=2)
        assert status.success_rate == 80.0


class TestRequestMetrics:
    def test_avg_duration(self):
        m = RequestMetrics(count=4, total_duration=2.0)
        assert m.avg_duration == 0.5

    def test_success_rate(self):
        m = RequestMetrics(count=10, success=8, errors=2)
        assert m.success_rate == 80.0


class TestMetricsCollector:
    @pytest.fixture
    def collector(self):
        with patch("src.services.metrics.psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.memory_info.return_value.rss = 100 * 1024 * 1024
            mock_proc.memory_percent.return_value = 5.0
            mock_process.return_value = mock_proc
            return MetricsCollector()

    def test_initial_services(self, collector):
        assert "yandex_gpt" in collector.services
        assert "google_sheets" in collector.services
        assert "yandex_stt" in collector.services
        assert "telegram" in collector.services

    def test_record_request(self, collector):
        collector.record_request("text", 0.5, success=True)
        assert collector.request_types["text"].count == 1
        assert collector.request_types["text"].success == 1

    def test_record_failed_request(self, collector):
        collector.record_request("text", 0.5, success=False)
        assert collector.request_types["text"].errors == 1

    def test_record_service_call_success(self, collector):
        collector.record_service_call("yandex_gpt", True, 0.3)
        status = collector.services["yandex_gpt"]
        assert status.total_calls == 1
        assert status.success_calls == 1
        assert status.last_success is not None

    def test_record_service_call_failure(self, collector):
        collector.record_service_call("yandex_gpt", False, 0.5, error="timeout")
        status = collector.services["yandex_gpt"]
        assert status.failed_calls == 1
        assert status.last_error == "timeout"

    def test_record_unknown_service_ignored(self, collector):
        collector.record_service_call("unknown_service", True, 0.1)
        assert "unknown_service" not in collector.services

    def test_overall_health_all_healthy(self, collector):
        assert collector.get_overall_health() == "healthy"

    def test_overall_health_one_unhealthy_degraded(self, collector):
        collector.services["yandex_gpt"].total_calls = 10
        collector.services["yandex_gpt"].success_calls = 5
        assert collector.get_overall_health() == "degraded"

    def test_overall_health_two_unhealthy(self, collector):
        collector.services["yandex_gpt"].total_calls = 10
        collector.services["yandex_gpt"].success_calls = 5

        collector.services["google_sheets"].total_calls = 10
        collector.services["google_sheets"].success_calls = 5

        assert collector.get_overall_health() == "unhealthy"

    def test_response_time_percentiles_empty(self, collector):
        result = collector.get_response_time_percentiles()
        assert result == {"p50": 0.0, "p95": 0.0, "p99": 0.0}

    def test_response_time_percentiles_with_data(self, collector):
        for i in range(100):
            collector.response_times.append(float(i))
        result = collector.get_response_time_percentiles()
        assert result["p50"] == 50.0
        assert result["p95"] == 95.0

    def test_uptime_positive(self, collector):
        assert collector.get_uptime() > 0

    def test_avg_response_time_calculation(self, collector):
        collector.record_service_call("yandex_gpt", True, 1.0)
        collector.record_service_call("yandex_gpt", True, 3.0)
        assert collector.services["yandex_gpt"].avg_response_time == 2.0

    def test_metrics_summary_structure(self, collector):
        summary = collector.get_metrics_summary()
        assert "status" in summary
        assert "uptime_seconds" in summary
        assert "requests" in summary
        assert "response_times" in summary

    def test_services_status_structure(self, collector):
        status = collector.get_services_status()
        for name, data in status.items():
            assert "healthy" in data
            assert "total_calls" in data
            assert "success_rate" in data
