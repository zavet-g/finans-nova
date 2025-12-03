<div align="center">

# Finans Nova

### Telegram-бот для учёта финансов с голосовым вводом и AI-категоризацией

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat)](LICENSE)

![GitHub last commit](https://img.shields.io/github/last-commit/zavet-g/finans-nova?style=flat)
![GitHub repo size](https://img.shields.io/github/repo-size/zavet-g/finans-nova?style=flat)

</div>

---

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

- **Голосовой ввод** через Whisper (модель medium, локально)
- **AI-категоризация** с контекстом через YandexGPT
- **Множественные транзакции** в одном сообщении
- **Интерактивное редактирование** перед сохранением
- **Графики и аналитика** с AI-отчётами
- **CSV-экспорт** и автоматические отчёты по расписанию

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

Автоматически создаются 2 листа:

- **Транзакции** — мастер-лог с автоматическим расчётом баланса
- **Сводка** — статистика текущего месяца, расходы по категориям, формулы SUMIFS

## Почему это работает

**Контекстная AI-категоризация** — YandexGPT понимает "такси до работы" как Такси с описанием "До работы", а не просто keyword matching.

**Локальный Whisper** — приватность данных, нет зависимости от внешних STT API.

**Множественные транзакции** — "обед 400, кофе 250, такси 500" → три отдельные записи с правильными категориями.

**Fallback-стратегия** — если YandexGPT недоступен, работает категоризация по ключевым словам.

## Тесты

```bash
pytest tests/ -v
```

## Лицензия

MIT

---

<div align="center">

Made with ❤️ for personal finance tracking

</div>
