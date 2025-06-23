import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Создание директорий если не существуют
for directory in [DATA_DIR, LOGS_DIR, DATA_DIR / "accounts", DATA_DIR / "proxies",
                  DATA_DIR / "hashtags", DATA_DIR / "targets"]:
    directory.mkdir(parents=True, exist_ok=True)

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS = [int(uid) for uid in os.getenv("ALLOWED_USERS", "").split(",") if uid]

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/twitter_automation.db")

# OpenAI (для генерации контента)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Playwright настройки
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "False").lower() == "true"
BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")  # chromium, firefox, webkit
USER_DATA_DIR = BASE_DIR / "browser_data"
USER_DATA_DIR.mkdir(exist_ok=True)

# Twitter лимиты
TWITTER_LIMITS = {
    "likes_per_day": 1000,
    "tweets_per_day": 2400,
    "follows_per_day": 400,
    "comments_per_hour": 100,
    "min_delay_between_actions": 3,  # секунды
    "max_delay_between_actions": 15,  # секунды
}

# Настройки активности
ACTIVITY_CONFIG = {
    "influencers": {
        "posts_per_day_min": 1,
        "posts_per_day_max": 3,
        "comments_per_day": 20,
        "likes_per_day": 50,
        "work_hours": 10,
        "sleep_hours": 14,
    },
    "shillers": {
        "comments_per_round": 10,
        "likes_per_round": 40,
        "ring_size": 4,
        "targets_per_shiller": 10,
    }
}

# Настройки ротации
ROTATION_CONFIG = {
    "min_rounds_before_repeat": 3,
    "max_interactions_per_pair": 1,
}

# AI настройки для генерации контента
AI_CONFIG = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.8,
    "max_tokens": 280,  # Максимум для твита
    "content_uniqueness": 0.9,
}

# Логирование
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}"

# Прокси настройки
PROXY_ROTATION_ENABLED = True
PROXY_CHECK_TIMEOUT = 10  # секунды

# Антидетект настройки
ANTIDETECT_CONFIG = {
    "randomize_viewport": True,
    "randomize_user_agent": True,
    "randomize_timezone": True,
    "randomize_webgl": True,
    "randomize_canvas": True,
}