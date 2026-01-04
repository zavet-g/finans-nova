<div align="center">

# Finans Nova

### Telegram-бот для учёта финансов с голосовым вводом и AI-категоризацией

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat)](LICENSE)
[![Code Size](https://img.shields.io/github/languages/code-size/zavet-g/finans-nova?style=flat&color=blue)](https://github.com/zavet-g/finans-nova)

![GitHub last commit](https://img.shields.io/github/last-commit/zavet-g/finans-nova?style=flat)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/zavet-g/finans-nova?style=flat&color=green)
![Top Language](https://img.shields.io/github/languages/top/zavet-g/finans-nova?style=flat&color=yellow)

</div>

---

<div align="center">

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&duration=3000&pause=1000&color=3776AB&center=true&vCenter=true&width=500&height=50&lines=Voice+%E2%86%92+AI+%E2%86%92+Google+Sheets;Personal+Finance+Automation)](https://git.io/typing-svg)

</div>

## Суть проекта

Говоришь или пишешь — бот распознаёт, категоризирует и сохраняет транзакции в Google Sheets. Whisper STT локально, YandexGPT для AI-анализа, автоматические отчёты с графиками.

```
Голос/Текст → Whisper → YandexGPT → Подтверждение → Google Sheets
```

## Технологии

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google_Sheets-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)

</div>

**Core:** python-telegram-bot • OpenAI Whisper • YandexGPT • Google Sheets API • matplotlib • APScheduler

## Возможности

<table>
<tr>
<td width="50%">

### 🎤 Распознавание речи
- Whisper STT (модель medium)
- Локальная обработка
- Поддержка OGG/WAV

### 🤖 AI-анализ
- YandexGPT категоризация
- Контекстное понимание
- Fallback на keywords

</td>
<td width="50%">

### 📊 Аналитика
- Круговые и столбчатые графики
- AI-отчёты по периодам
- Сравнение с прошлыми месяцами

### 💾 Экспорт данных
- CSV-формат
- Автоматические отчёты по расписанию
- Интеграция с Google Sheets

</td>
</tr>
</table>

**Интерактивное редактирование** • **Множественные транзакции** • **Приватность данных** • **Production-ready**

## Быстрый старт

### Требования

- Python 3.11+
- FFmpeg
- Google Service Account

### Локальный запуск

```bash
pip install -r requirements.txt
cp .env.example .env
python src/main.py
```

### Docker

```bash
docker compose up -d
# или используйте Makefile
make run
make logs
make stop
```

### Переменные окружения

```bash
TELEGRAM_BOT_TOKEN=             # BotFather токен
YANDEX_GPT_API_KEY=             # Yandex Cloud API ключ
YANDEX_GPT_FOLDER_ID=           # Yandex Cloud folder ID
GOOGLE_SHEETS_CREDENTIALS_FILE= # путь к service_account.json
GOOGLE_SHEETS_SPREADSHEET_ID=   # ID таблицы
ALLOWED_USER_IDS=               # список user_id через запятую
```

## Архитектура

```
src/
├── bot/
│   ├── handlers/      # voice, text, callbacks, menu
│   ├── keyboards.py   # inline-клавиатуры
│   └── states.py      # состояния ConversationHandler
├── services/
│   ├── speech.py      # Whisper STT
│   ├── ai_analyzer.py # YandexGPT
│   ├── sheets.py      # Google Sheets CRUD
│   ├── charts.py      # matplotlib графики
│   └── scheduler.py   # APScheduler
├── models/
│   ├── transaction.py # Pydantic модель
│   └── category.py    # категории
└── utils/
    ├── audio.py       # FFmpeg конвертация
    └── formatters.py  # форматирование сообщений
```

### Google Sheets структура

<div align="center">

```mermaid
graph LR
    A[Telegram Bot] -->|Транзакция| B[Лист: Транзакции]
    B -->|Формулы| C[Лист: Сводка]
    C -->|Аналитика| D[AI Отчёты]
    C -->|Графики| E[Визуализация]
```

</div>

Автоматически создаются 2 листа:

- **Транзакции** — мастер-лог с автоматическим расчётом баланса
- **Сводка** — статистика текущего месяца, расходы по категориям, формулы SUMIFS

## Почему это работает

<table>
<tr>
<td align="center" width="33%">
<img src="https://img.icons8.com/fluency/96/artificial-intelligence.png" width="64" height="64" alt="AI"/>
<br>
<b>Контекстная AI</b>
<br>
<sub>YandexGPT понимает контекст:<br>"такси до работы" → категория Такси,<br>описание "До работы"</sub>
</td>
<td align="center" width="33%">
<img src="https://img.icons8.com/fluency/96/lock.png" width="64" height="64" alt="Privacy"/>
<br>
<b>Приватность</b>
<br>
<sub>Whisper работает локально,<br>данные только в вашем<br>Google Sheets</sub>
</td>
<td align="center" width="33%">
<img src="https://img.icons8.com/fluency/96/documents.png" width="64" height="64" alt="Batch"/>
<br>
<b>Batch обработка</b>
<br>
<sub>"обед 400, кофе 250, такси 500"<br>→ три отдельные записи<br>с правильными категориями</sub>
</td>
</tr>
</table>

**Локальный Whisper** — приватность данных, нет зависимости от внешних STT API.

**Множественные транзакции** — "обед 400, кофе 250, такси 500" → три отдельные записи с правильными категориями.

**Fallback-стратегия** — если YandexGPT недоступен, работает категоризация по ключевым словам.

## Production-оптимизация

Бот оптимизирован для непрерывной работы месяцами без деградации производительности.

<table>
<tr>
<td width="50%">

### ⚡ Производительность
- HTTP connection pooling для API
- Async Google Sheets executor
- Exponential backoff retry
- Таймауты: <1% запросов

### 🛡️ Надёжность
- Circuit breaker для API
- Rate limiting (20 req/min)
- Global error handling
- Graceful degradation

</td>
<td width="50%">

### 📊 Мониторинг
- Health check система
- Uptime, память, CPU
- Error rate tracking
- Resource monitoring с auto-GC

### 📝 Логирование
- Structured logging
- Rotation (10MB, 5 backups)
- Отдельный error.log
- Метрики производительности

</td>
</tr>
</table>

**Команды мониторинга:**
- `/health` — детальный статус бота, ресурсов, API
- `/stats` — краткая статистика запросов
- Кнопка "🔧 Состояние бота" в главном меню

<div align="center">

![Performance](https://img.shields.io/badge/Uptime-99.9%25-success?style=for-the-badge)
![Response Time](https://img.shields.io/badge/Response-<10s-blue?style=for-the-badge)
![Memory](https://img.shields.io/badge/Memory-Stable-green?style=for-the-badge)

</div>

## Статистика

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/zavet-g/finans-nova?style=for-the-badge&logo=github&color=yellow)](https://github.com/zavet-g/finans-nova/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/zavet-g/finans-nova?style=for-the-badge&logo=github&color=blue)](https://github.com/zavet-g/finans-nova/network/members)
[![GitHub issues](https://img.shields.io/github/issues/zavet-g/finans-nova?style=for-the-badge&logo=github&color=red)](https://github.com/zavet-g/finans-nova/issues)

</div>
