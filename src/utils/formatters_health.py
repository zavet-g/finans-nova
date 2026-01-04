from datetime import datetime


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


def format_percentage(value: float) -> str:
    if value < 50:
        return f"{value:.1f}%"
    elif value < 80:
        return f"{value:.1f}% ⚠️"
    else:
        return f"{value:.1f}% 🔴"


def get_status_emoji(status: str) -> str:
    emoji_map = {
        "healthy": "✅",
        "degraded": "⚠️",
        "unhealthy": "❌"
    }
    return emoji_map.get(status.lower(), "❓")


def get_service_emoji(status: str) -> str:
    if status == "configured":
        return "✅"
    elif status == "missing":
        return "❌"
    else:
        return "❓"


def format_health_report(health_status: dict, external_services: dict) -> str:
    status = health_status.get("status", "unknown")
    status_emoji = get_status_emoji(status)

    uptime_formatted = format_uptime(health_status.get("uptime_seconds", 0))
    memory_formatted = format_memory(health_status.get("memory_mb", 0))
    memory_percent = health_status.get("memory_percent", 0)
    cpu_percent = health_status.get("cpu_percent", 0)

    requests_data = health_status.get("requests", {})
    total_requests = requests_data.get("total", 0)
    success_requests = requests_data.get("success", 0)
    error_requests = requests_data.get("errors", 0)
    error_rate = requests_data.get("error_rate", 0)

    success_rate = 100 - error_rate if total_requests > 0 else 0

    yandex_status = external_services.get("yandex_api", "unknown")
    sheets_status = external_services.get("google_sheets", "unknown")

    last_error = health_status.get("last_error")
    last_error_str = ""
    if last_error:
        try:
            error_time = datetime.fromisoformat(last_error)
            last_error_str = f"\n⏰ Последняя ошибка: {error_time.strftime('%d.%m.%Y %H:%M:%S')}"
        except:
            last_error_str = f"\n⏰ Последняя ошибка: {last_error}"

    degraded_note = ""
    from src.services.resource_monitor import get_resource_monitor
    if get_resource_monitor().should_throttle():
        degraded_note = "\n\n⚠️ РЕЖИМ ДЕГРАДАЦИИ АКТИВЕН\nБот работает с ограничениями из-за высокой нагрузки"

    report = f"""
{status_emoji} СОСТОЯНИЕ БОТА

━━━━━━━━━━━━━━━━━━━━━━━━
📊 ОБЩАЯ ИНФОРМАЦИЯ

Статус: {status.upper()}
Время работы: {uptime_formatted}

━━━━━━━━━━━━━━━━━━━━━━━━
💻 РЕСУРСЫ СЕРВЕРА

Память: {memory_formatted} ({format_percentage(memory_percent)})
CPU: {format_percentage(cpu_percent)}
Нагрузка: {'Высокая' if get_resource_monitor().should_throttle() else 'Нормальная'}

━━━━━━━━━━━━━━━━━━━━━━━━
📈 СТАТИСТИКА ЗАПРОСОВ

Всего запросов: {total_requests:,}
├─ Успешно: {success_requests:,} ({success_rate:.1f}%)
└─ Ошибок: {error_requests:,} ({error_rate:.1f}%)
{last_error_str}

━━━━━━━━━━━━━━━━━━━━━━━━
🔌 ВНЕШНИЕ СЕРВИСЫ

Yandex API: {get_service_emoji(yandex_status)} {yandex_status}
Google Sheets: {get_service_emoji(sheets_status)} {sheets_status}

━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
{degraded_note}
"""

    return report.strip().replace(",", " ")
