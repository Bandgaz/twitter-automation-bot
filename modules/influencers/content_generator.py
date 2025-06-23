import random
from typing import Optional, List
from loguru import logger

from config import AI_CONFIG, OPENAI_API_KEY
from utils.ai_helpers import paraphrase_text


class ContentGenerator:
    """Генератор контента для инфлюенсеров"""

    def __init__(self):
        self.use_ai = bool(OPENAI_API_KEY)

    async def generate_from_source(self, source_username: str) -> Optional[str]:
        """
        Генерировать контент на основе источника
        В реальной реализации здесь должен быть парсинг последних твитов источника
        """
        # Заглушка - примеры контента
        templates = [
            "The crypto market is showing interesting patterns today. What are your thoughts on the current trend? 🤔",
            "Just analyzed the latest DeFi protocols. The innovation in this space is mind-blowing! 🚀",
            "Remember: In crypto, patience and research are your best friends. DYOR! 📚",
            "The future of finance is being built right now. Are you paying attention? 👀",
            "Interesting developments in the {topic} space. This could be game-changing! 💡",
            "Market volatility is just noise if you're thinking long-term. Focus on fundamentals. 📊",
            "New project alert! Always exciting to see innovation in the blockchain space. 🔥",
            "The key to success in crypto? Education, patience, and risk management. 💎",
        ]

        # Выбираем случайный шаблон
        content = random.choice(templates)

        # Заменяем плейсхолдеры
        topics = ["DeFi", "NFT", "Layer 2", "Web3", "Metaverse", "GameFi"]
        content = content.replace("{topic}", random.choice(topics))

        # Если есть AI, перефразируем
        if self.use_ai:
            try:
                content = await paraphrase_text(content)
            except Exception as e:
                logger.error(f"Ошибка AI перефразировки: {e}")

        return content

    async def generate_comment(self, context: str = None) -> str:
        """Генерировать триггерный комментарий"""
        templates = [
            "This is exactly what I've been saying! 🎯",
            "Interesting perspective. Have you considered {aspect}?",
            "The implications of this are huge 🤯",
            "This deserves more attention 👀",
            "Finally someone said it! 💯",
            "Game changer if true 🚀",
            "This is why I love crypto Twitter 🙌",
            "Big if true! Following for more insights 🔔",
        ]

        comment = random.choice(templates)

        # Заменяем плейсхолдеры
        aspects = [
            "the regulatory implications",
            "the technical challenges",
            "the market dynamics",
            "the long-term vision",
            "the community aspect"
        ]
        comment = comment.replace("{aspect}", random.choice(aspects))

        return comment

    async def generate_quote_text(self, original_tweet: str = None) -> str:
        """Генерировать текст для цитирования"""
        templates = [
            "This! 👆 {addition}",
            "Adding to this great point: {addition}",
            "Couldn't agree more. {addition}",
            "Important thread 🧵 {addition}",
            "Everyone should read this. {addition}",
        ]

        additions = [
            "The future is being built now.",
            "This is why we're early.",
            "Knowledge is power in this space.",
            "DYOR but this is solid.",
            "The innovation continues!",
        ]

        template = random.choice(templates)
        addition = random.choice(additions)

        return template.replace("{addition}", addition)