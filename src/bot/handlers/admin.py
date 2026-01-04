import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.handlers.menu import is_user_allowed
from src.services.health_check import get_health_checker
from src.services.resource_monitor import get_resource_monitor

logger = logging.getLogger(__name__)


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_user_allowed(user.id):
        return

    health_checker = get_health_checker()
    resource_monitor = get_resource_monitor()

    health_status = health_checker.get_health_status()
    external_services = await health_checker.check_external_services()

    status_emoji = {
        "healthy": "✅",
        "degraded": "⚠️",
        "unhealthy": "❌"
    }

    emoji = status_emoji.get(health_status["status"], "❓")

    report = f"""
{emoji} HEALTH CHECK

Статус: {health_status['status'].upper()}
Время работы: {health_status['uptime_hours']} часов

📊 Ресурсы:
• Память: {health_status['memory_mb']} MB ({health_status['memory_percent']}%)
• CPU: {health_status['cpu_percent']}%
• Деградация: {'Да' if resource_monitor.should_throttle() else 'Нет'}

📈 Запросы:
• Всего: {health_status['requests']['total']}
• Успешных: {health_status['requests']['success']}
• Ошибок: {health_status['requests']['errors']} ({health_status['requests']['error_rate']}%)

🔌 Внешние сервисы:
• Yandex API: {external_services.get('yandex_api', 'unknown')}
• Google Sheets: {external_services.get('google_sheets', 'unknown')}

⏰ Обновлено: {health_status['timestamp']}
"""

    await update.message.reply_text(report.strip())


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_user_allowed(user.id):
        return

    health_status = get_health_checker().get_health_status()

    stats = f"""
📊 СТАТИСТИКА БОТА

⏱ Uptime: {health_status['uptime_hours']} ч
📊 Запросов: {health_status['requests']['total']}
✅ Успешно: {health_status['requests']['success']}
❌ Ошибок: {health_status['requests']['errors']}
📈 Success rate: {100 - health_status['requests']['error_rate']:.1f}%

💾 Память: {health_status['memory_mb']} MB
🔋 CPU: {health_status['cpu_percent']}%
"""

    await update.message.reply_text(stats.strip())
