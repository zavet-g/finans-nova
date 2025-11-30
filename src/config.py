import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_GPT_API_KEY = os.getenv("YANDEX_GPT_API_KEY")
YANDEX_GPT_FOLDER_ID = os.getenv("YANDEX_GPT_FOLDER_ID")
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials/service_account.json")
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
]

WHISPER_MODEL = "medium"

EXPENSE_CATEGORIES = [
    ("food", "Еда"),
    ("housing", "Жильё и быт"),
    ("taxi", "Такси"),
    ("health", "Здоровье"),
    ("entertainment", "Развлечения"),
    ("clothes", "Одежда"),
    ("subscriptions", "Подписки"),
    ("gifts", "Подарки"),
    ("other", "Прочее"),
]

INCOME_CATEGORY = ("income", "Доход")

TEMP_AUDIO_DIR = BASE_DIR / "temp_audio"
TEMP_AUDIO_DIR.mkdir(exist_ok=True)
