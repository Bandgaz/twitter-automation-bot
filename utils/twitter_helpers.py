import asyncio
import random
import re
from typing import List, Optional
from datetime import datetime, timedelta
from playwright.async_api import Page

from config import TWITTER_LIMITS


async def random_delay(min_seconds: float = 1, max_seconds: float = 3):
    """Случайная задержка между действиями"""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


async def human_like_typing(page: Page, text: str, wpm: int = 40):
    """Имитация человеческого набора текста"""
    # Расчет задержки между символами на основе WPM (слов в минуту)
    avg_word_length = 5
    chars_per_minute = wpm * avg_word_length
    base_delay = 60.0 / chars_per_minute

    for char in text:
        await page.keyboard.type(char)

        # Вариация задержки
        delay = base_delay * random.uniform(0.5, 1.5)

        # Дополнительная задержка после знаков препинания
        if char in ".!?,;:":
            delay *= random.uniform(2, 4)

        # Случайные паузы (имитация размышления)
        if random.random() < 0.1:
            delay *= random.uniform(3, 6)

        await asyncio.sleep(delay)


def generate_comment_variation(template: str, token_name: str, token_address: str) -> str:
    """Генерация вариации комментария"""
    variations = [
        f"снова сезон $SOL? кто-то уже нырнул в ${token_name}? вайб от $WIF... {token_address[-8:]}",
        f"пока все спят, ${token_name} делает иксы 🚀 CA: {token_address[-8:]}",
        f"${token_name} следующий $PEPE? адрес для умных: {token_address[-8:]}",
        f"те кто в ${token_name} уже в плюсе... {token_address[-8:]}",
        f"${token_name} > все остальное сейчас, факт. {token_address[-8:]}",
        f"зашел в ${token_name} и не жалею, мун близко 🌙 {token_address[-8:]}",
        f"${token_name} это новая мета, запомните адрес {token_address[-8:]}",
        f"все обсуждают ${token_name}, а ты еще думаешь? {token_address[-8:]}",
    ]

    # Замена плейсхолдеров в шаблоне
    if template:
        comment = template.replace("{token_name}", token_name)
        comment = comment.replace("{token_address}", token_address[-8:])
        return comment

    return random.choice(variations)


def generate_quote_text(token_name: str) -> str:
    """Генерация текста для цитирования"""
    quotes = [
        f"💥 That's what happens when {token_name} mining rigs go nuclear",
        f"🚀 ${token_name} is not just a token, it's a movement",
        f"⚡ The future is ${token_name}. Are you ready?",
        f"🔥 ${token_name} explosion incoming. Don't say I didn't warn you",
        f"💎 Diamond hands only for ${token_name}. This is the way",
        f"🌙 ${token_name} to the moon? More like to Mars!",
        f"⚠️ Warning: ${token_name} may cause extreme gains",
        f"🎯 Smart money is flowing into ${token_name}. Follow the whales",
    ]

    return random.choice(quotes)


def validate_twitter_username(username: str) -> bool:
    """Валидация username Twitter"""
    # Twitter username может содержать только буквы, цифры и подчеркивания
    # Длина от 1 до 15 символов
    pattern = r'^[a-zA-Z0-9_]{1,15}$'
    return bool(re.match(pattern, username))


def clean_twitter_username(username: str) -> str:
    """Очистка username от @ и пробелов"""
    return username.strip().replace("@", "")


def is_within_rate_limit(action_type: str, actions_today: int) -> bool:
    """Проверка лимитов Twitter"""
    limits = {
        "tweet": TWITTER_LIMITS["tweets_per_day"],
        "like": TWITTER_LIMITS["likes_per_day"],
        "follow": TWITTER_LIMITS["follows_per_day"],
        "comment": TWITTER_LIMITS["comments_per_hour"] * 24,
    }

    limit = limits.get(action_type, float('inf'))
    return actions_today < limit


def calculate_sleep_schedule(work_hours: int = 10, sleep_hours: int = 14) -> dict:
    """Расчет расписания сна/работы"""
    current_hour = datetime.now().hour

    # Простое расписание: работа с 8:00 до 18:00
    work_start = 8
    work_end = work_start + work_hours

    is_working_hours = work_start <= current_hour < work_end

    if is_working_hours:
        next_sleep = datetime.now().replace(hour=work_end, minute=0, second=0)
        if next_sleep < datetime.now():
            next_sleep += timedelta(days=1)
    else:
        next_wake = datetime.now().replace(hour=work_start, minute=0, second=0)
        if next_wake < datetime.now():
            next_wake += timedelta(days=1)
        next_sleep = next_wake

    return {
        "is_working": is_working_hours,
        "next_sleep": next_sleep,
        "work_hours": work_hours,
        "sleep_hours": sleep_hours
    }


def generate_hashtags(base_tags: List[str], count: int = 3) -> List[str]:
    """Генерация хэштегов"""
    crypto_tags = [
        "#crypto", "#DeFi", "#Web3", "#blockchain", "#Solana", "#memecoin",
        "#altcoin", "#cryptocurrency", "#SOL", "#trading", "#hodl", "#moon",
        "#bullrun", "#gem", "#100x", "#pumpit", "#LFG", "#WAGMI"
    ]

    # Объединяем базовые и общие теги
    all_tags = list(set(base_tags + crypto_tags))

    # Выбираем случайные
    selected = random.sample(all_tags, min(count, len(all_tags)))

    return selected


def extract_tweet_id_from_url(url: str) -> Optional[str]:
    """Извлечь ID твита из URL"""
    # Паттерн для URL твита
    pattern = r'twitter\.com/\w+/status/(\d+)'
    match = re.search(pattern, url)

    if match:
        return match.group(1)
    return None


def generate_influencer_comment() -> str:
    """Генерация триггерного комментария для инфлюенсера"""
    templates = [
        "это изменит всё, что вы знали о {topic}... 🤯",
        "пока вы спите, смарт-мани уже здесь 🐳",
        "те кто понял - уже в прибыли 📈",
        "не все готовы к тому, что будет дальше...",
        "включите уведомления, если не хотите пропустить 🔔",
        "это начало чего-то большого 🚀",
        "запомните этот момент 📸",
        "факты, которые изменят вашу стратегию ⚡",
        "то, о чем все будут говорить завтра 🔥",
        "альфа для тех, кто следит внимательно 👀",
    ]

    return random.choice(templates)


class ActionThrottler:
    """Класс для контроля частоты действий"""

    def __init__(self):
        self.last_actions = {}

    async def wait_if_needed(self, account_id: int, action_type: str):
        """Ожидание если необходимо между действиями"""
        key = f"{account_id}_{action_type}"

        if key in self.last_actions:
            elapsed = (datetime.now() - self.last_actions[key]).total_seconds()
            min_delay = TWITTER_LIMITS["min_delay_between_actions"]

            if elapsed < min_delay:
                await asyncio.sleep(min_delay - elapsed)

        self.last_actions[key] = datetime.now()


# Глобальный throttler
action_throttler = ActionThrottler()


async def safe_twitter_action(func, *args, **kwargs):
    """Безопасное выполнение действия с повторными попытками"""
    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            else:
                raise e