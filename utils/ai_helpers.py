import asyncio
from typing import Optional, List
from loguru import logger

from config import OPENAI_API_KEY, AI_CONFIG

# Проверяем доступность OpenAI
try:
    if OPENAI_API_KEY:
        import openai

        openai.api_key = OPENAI_API_KEY
        AI_AVAILABLE = True
    else:
        AI_AVAILABLE = False
except ImportError:
    AI_AVAILABLE = False
    logger.warning("OpenAI не установлен. AI функции недоступны.")


async def paraphrase_text(text: str, style: str = "casual") -> str:
    """
    Перефразировать текст с сохранением смысла

    Args:
        text: Исходный текст
        style: Стиль перефразировки (casual, professional, excited)

    Returns:
        Перефразированный текст
    """
    if not AI_AVAILABLE:
        # Простая замена без AI
        return simple_paraphrase(text)

    try:
        style_prompts = {
            "casual": "Rewrite this tweet in a casual, friendly tone:",
            "professional": "Rewrite this tweet in a professional tone:",
            "excited": "Rewrite this tweet in an excited, enthusiastic tone:"
        }

        prompt = style_prompts.get(style, style_prompts["casual"])

        response = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model=AI_CONFIG["model"],
            messages=[
                {"role": "system",
                 "content": "You are a crypto Twitter influencer. Rewrite tweets to sound natural and engaging."},
                {"role": "user", "content": f"{prompt}\n\n{text}"}
            ],
            temperature=AI_CONFIG["temperature"],
            max_tokens=AI_CONFIG["max_tokens"]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Ошибка OpenAI: {e}")
        return simple_paraphrase(text)


def simple_paraphrase(text: str) -> str:
    """Простая перефразировка без AI"""
    # Словарь замен
    replacements = {
        "interesting": ["fascinating", "intriguing", "compelling", "notable"],
        "important": ["crucial", "vital", "essential", "significant"],
        "think": ["believe", "consider", "feel", "reckon"],
        "good": ["great", "excellent", "solid", "strong"],
        "bad": ["poor", "weak", "concerning", "problematic"],
        "big": ["huge", "massive", "significant", "major"],
        "new": ["fresh", "latest", "recent", "novel"],
    }

    result = text
    for word, alternatives in replacements.items():
        if word in result.lower():
            import random
            replacement = random.choice(alternatives)
            result = result.replace(word, replacement)
            result = result.replace(word.capitalize(), replacement.capitalize())

    return result


async def generate_clickbait_comment(topic: str) -> str:
    """Генерировать кликбейт комментарий по теме"""
    if not AI_AVAILABLE:
        return generate_simple_clickbait(topic)

    try:
        response = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model=AI_CONFIG["model"],
            messages=[
                {"role": "system",
                 "content": "Generate intriguing crypto Twitter comments that make people want to check the profile. Be subtle, not spammy."},
                {"role": "user", "content": f"Create a clickbait comment about: {topic}"}
            ],
            temperature=0.9,
            max_tokens=60
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Ошибка генерации комментария: {e}")
        return generate_simple_clickbait(topic)


def generate_simple_clickbait(topic: str) -> str:
    """Простая генерация кликбейта без AI"""
    templates = [
        "This changes everything about {topic}... 🤯",
        "Not many people know this about {topic} yet 👀",
        "The {topic} alpha nobody's talking about...",
        "If you understand {topic}, you're already ahead 🎯",
        "The {topic} strategy that actually works 💡",
    ]

    import random
    template = random.choice(templates)
    return template.replace("{topic}", topic)


async def extract_key_points(text: str) -> List[str]:
    """Извлечь ключевые пункты из текста"""
    if not AI_AVAILABLE:
        # Простое разделение на предложения
        sentences = text.split('. ')
        return sentences[:3] if len(sentences) > 3 else sentences

    try:
        response = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model=AI_CONFIG["model"],
            messages=[
                {"role": "system", "content": "Extract 3 key points from the text. Return as a simple list."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=150
        )

        content = response.choices[0].message.content.strip()
        # Парсим ответ в список
        points = [line.strip('- •123. ') for line in content.split('\n') if line.strip()]
        return points[:3]

    except Exception as e:
        logger.error(f"Ошибка извлечения ключевых пунктов: {e}")
        sentences = text.split('. ')
        return sentences[:3] if len(sentences) > 3 else sentences


async def generate_thread(topic: str, points: int = 5) -> List[str]:
    """Генерировать тред (серию твитов) на тему"""
    if not AI_AVAILABLE:
        return generate_simple_thread(topic, points)

    try:
        response = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model=AI_CONFIG["model"],
            messages=[
                {"role": "system",
                 "content": "Create an engaging Twitter thread about crypto topics. Each tweet should be under 280 characters."},
                {"role": "user", "content": f"Create a {points}-tweet thread about: {topic}"}
            ],
            temperature=0.8,
            max_tokens=1000
        )

        content = response.choices[0].message.content.strip()
        # Разделяем на твиты
        tweets = [t.strip() for t in content.split('\n\n') if t.strip()]
        return tweets[:points]

    except Exception as e:
        logger.error(f"Ошибка генерации треда: {e}")
        return generate_simple_thread(topic, points)


def generate_simple_thread(topic: str, points: int) -> List[str]:
    """Простая генерация треда без AI"""
    thread_templates = [
        f"🧵 Let's talk about {topic} and why it matters (1/{points})",
        f"First, understanding the basics of {topic} is crucial for anyone in crypto (2/{points})",
        f"The technology behind {topic} is fascinating and here's why (3/{points})",
        f"What most people miss about {topic} is the long-term potential (4/{points})",
        f"In conclusion, {topic} represents a paradigm shift in how we think about finance ({points}/{points})"
    ]

    return thread_templates[:points]