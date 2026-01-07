from datetime import datetime
from typing import Dict, Any


def format_uptime(uptime_seconds: float) -> str:
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    parts = []
    if days > 0:
        parts.append(f"{days} д")
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} мин")

    return " ".join(parts)


def format_memory(memory_mb: float) -> str:
    if memory_mb < 1024:
        return f"{memory_mb:.1f} МБ"
    else:
        return f"{memory_mb / 1024:.2f} ГБ"


def get_status_indicator(status: str) -> str:
    indicators = {
        "healthy": "✅",
        "degraded": "⚠️",
        "unhealthy": "❌",
        "not_configured": "⚪",
        "configured": "✅",
        "timeout": "⏱",
        "error": "❌"
    }
    return indicators.get(status.lower(), "❓")


def format_time_ago(dt: datetime) -> str:
    now = datetime.now()
    diff = now - dt

    if diff.total_seconds() < 60:
        return f"{int(diff.total_seconds())} сек назад"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)} мин назад"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)} ч назад"
    else:
        return f"{int(diff.total_seconds() / 86400)} д назад"


def format_health_report(
    metrics_summary: Dict[str, Any],
    services_status: Dict[str, Dict[str, Any]],
    request_types: Dict[str, Dict[str, Any]],
    health_checks: Dict[str, Dict[str, Any]]
) -> str:
    status = metrics_summary.get("status", "unknown")
    status_emoji = get_status_indicator(status)

    uptime_formatted = format_uptime(metrics_summary.get("uptime_seconds", 0))
    memory_formatted = format_memory(metrics_summary.get("memory_mb", 0))
    memory_percent = metrics_summary.get("memory_percent", 0)
    cpu_percent = metrics_summary.get("cpu_percent", 0)

    requests_data = metrics_summary.get("requests", {})
    total_requests = requests_data.get("total", 0)
    success_requests = requests_data.get("success", 0)
    error_requests = requests_data.get("errors", 0)
    success_rate = requests_data.get("success_rate", 100.0)

    response_times = metrics_summary.get("response_times", {})
    p50 = response_times.get("p50", 0.0)
    p95 = response_times.get("p95", 0.0)
    p99 = response_times.get("p99", 0.0)

    report_lines = [
        f"{status_emoji} СОСТОЯНИЕ БОТА",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📊 ОБЩАЯ ИНФОРМАЦИЯ",
        "",
        f"Статус: {status.upper()}",
        f"Время работы: {uptime_formatted}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "💻 РЕСУРСЫ СЕРВЕРА",
        "",
        f"Память: {memory_formatted} ({memory_percent:.1f}%)",
        f"CPU: {cpu_percent:.1f}%",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📈 СТАТИСТИКА ЗАПРОСОВ",
        "",
        f"Всего запросов: {total_requests}",
        f"├─ Успешно: {success_requests} ({success_rate:.1f}%)",
        f"└─ Ошибок: {error_requests} ({100 - success_rate:.1f}%)",
        "",
        "⏱ Время отклика:",
        f"├─ Медиана (P50): {p50*1000:.0f} мс",
        f"├─ P95: {p95*1000:.0f} мс",
        f"└─ P99: {p99*1000:.0f} мс",
    ]

    if request_types:
        report_lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "🎯 ОПЕРАЦИИ ПО ТИПАМ",
            ""
        ])

        for op_type, stats in sorted(request_types.items(), key=lambda x: x[1]["count"], reverse=True):
            type_emoji = {
                "voice": "🎤",
                "text": "💬",
                "callback": "🔘",
                "ai": "🤖",
                "sheets": "📊"
            }.get(op_type, "📌")

            count = stats["count"]
            avg_duration = stats["avg_duration"]
            type_success_rate = stats["success_rate"]

            report_lines.append(
                f"{type_emoji} {op_type.capitalize()}: {count} ({type_success_rate:.1f}%, ~{avg_duration*1000:.0f}мс)"
            )

    report_lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "🔌 ВНЕШНИЕ СЕРВИСЫ",
        ""
    ])

    service_order = ["telegram", "yandex_gpt", "yandex_stt", "google_sheets"]
    service_names = {
        "telegram": "Telegram API",
        "yandex_gpt": "Yandex GPT",
        "yandex_stt": "Yandex STT",
        "google_sheets": "Google Sheets"
    }

    for service_key in service_order:
        health = health_checks.get(service_key, {})
        stats = services_status.get(service_key, {})

        service_name = service_names.get(service_key, service_key)
        service_status = health.get("status", "unknown")
        status_emoji = get_status_indicator(service_status)

        message = health.get("message", "Нет данных")

        last_success = stats.get("last_success")
        last_failure = stats.get("last_failure")

        status_line = f"{status_emoji} {service_name}: {message}"
        report_lines.append(status_line)

        if last_success:
            last_success_dt = datetime.fromisoformat(last_success)
            report_lines.append(f"   └─ Последний успех: {format_time_ago(last_success_dt)}")

        if last_failure:
            last_failure_dt = datetime.fromisoformat(last_failure)
            last_error = stats.get("last_error", "")
            error_msg = f" ({last_error[:50]}...)" if last_error and len(last_error) > 50 else f" ({last_error})" if last_error else ""
            report_lines.append(f"   └─ Последняя ошибка: {format_time_ago(last_failure_dt)}{error_msg}")

    report_lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⏰ Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    ])

    return "\n".join(report_lines)


def format_short_health_status(metrics_summary: Dict[str, Any]) -> str:
    status = metrics_summary.get("status", "unknown")
    status_emoji = get_status_indicator(status)

    uptime_formatted = format_uptime(metrics_summary.get("uptime_seconds", 0))
    memory_mb = metrics_summary.get("memory_mb", 0)
    cpu_percent = metrics_summary.get("cpu_percent", 0)

    requests_data = metrics_summary.get("requests", {})
    total_requests = requests_data.get("total", 0)
    success_rate = requests_data.get("success_rate", 100.0)

    return (
        f"{status_emoji} Статус: {status.upper()}\n"
        f"⏱ Uptime: {uptime_formatted}\n"
        f"💾 Память: {memory_mb:.1f} МБ\n"
        f"🔋 CPU: {cpu_percent:.1f}%\n"
        f"📊 Запросов: {total_requests} ({success_rate:.1f}% успешных)"
    )
