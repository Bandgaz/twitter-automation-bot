import random
from typing import List, Optional, Dict
from loguru import logger

from utils.ai_helpers import generate_clickbait_comment


class CommentEngine:
    """Движок для генерации триггерных комментариев инфлюенсеров"""

    def __init__(self):
        self.comment_templates = self._load_templates()

    def _load_templates(self) -> Dict[str, List[str]]:
        """Загрузка шаблонов комментариев по категориям"""
        return {
            "crypto_general": [
                "это изменит всё, что вы знали о {topic}... 🤯",
                "пока вы спите, смарт-мани уже здесь 🐳",
                "те кто понял - уже в прибыли 📈",
                "не все готовы к тому, что будет дальше...",
                "включите уведомления, если не хотите пропустить 🔔",
            ],
            "technical": [
                "технически это прорыв, вот почему... 🔧",
                "код не врет, посмотрите сами 💻",
                "архитектура решает всё 🏗️",
                "это следующий уровень {topic} 🚀",
                "алгоритм гениален, признаю 🧠",
            ],
            "hype": [
                "это начало чего-то большого 🚀",
                "запомните этот момент 📸",
                "факты, которые изменят вашу стратегию ⚡",
                "то, о чем все будут говорить завтра 🔥",
                "альфа для тех, кто следит внимательно 👀",
            ],
            "analytical": [
                "цифры говорят сами за себя 📊",
                "тренд очевиден для тех, кто видит 📈",
                "метрики не врут, проверьте сами 📉",
                "данные подтверждают мою теорию 🎯",
                "статистика на моей стороне 💹",
            ],
            "philosophical": [
                "это больше чем просто {topic} 🌌",
                "парадигма меняется прямо сейчас 🔄",
                "будущее уже здесь, просто неравномерно распределено 🌐",
                "эволюция неизбежна 🧬",
                "мы свидетели истории 📜",
            ]
        }

    async def generate_comment(self, context: str = None, style: str = "random") -> str:
        """
        Генерировать триггерный комментарий

        Args:
            context: Контекст поста (о чем пост)
            style: Стиль комментария (crypto_general, technical, hype, analytical, philosophical, random)

        Returns:
            Сгенерированный комментарий
        """
        # Выбираем стиль
        if style == "random" or style not in self.comment_templates:
            style = random.choice(list(self.comment_templates.keys()))

        # Выбираем шаблон
        template = random.choice(self.comment_templates[style])

        # Определяем топик
        if context:
            # Извлекаем ключевые слова из контекста
            topic = self._extract_topic(context)
        else:
            # Случайный топик
            topics = ["DeFi", "NFT", "Layer 2", "Web3", "метавселенной", "DAO", "GameFi", "стейкинге"]
            topic = random.choice(topics)

        # Заменяем плейсхолдеры
        comment = template.replace("{topic}", topic)

        # Добавляем вариативность
        comment = self._add_variations(comment)

        # Если есть AI, улучшаем комментарий
        try:
            from utils.ai_helpers import generate_clickbait_comment
            ai_comment = await generate_clickbait_comment(topic)
            if ai_comment and len(ai_comment) < 280:
                return ai_comment
        except Exception as e:
            logger.debug(f"AI недоступен для комментария: {e}")

        return comment

    def generate_reply(self, original_comment: str = None) -> str:
        """
        Генерировать ответ на комментарий

        Args:
            original_comment: Оригинальный комментарий

        Returns:
            Ответ на комментарий
        """
        reply_templates = [
            "точно подмечено! {addition}",
            "согласен, {addition}",
            "это факт 💯 {addition}",
            "вы правы, {addition}",
            "+1 к этому, {addition}",
            "именно! {addition}",
            "в точку 🎯 {addition}",
        ]

        additions = [
            "особенно сейчас",
            "время покажет",
            "следим за развитием",
            "интересные времена",
            "всё только начинается",
            "будет жарко",
        ]

        template = random.choice(reply_templates)
        addition = random.choice(additions)

        return template.replace("{addition}", addition)

    def _extract_topic(self, context: str) -> str:
        """Извлечь топик из контекста"""
        # Простой поиск ключевых слов
        keywords = {
            "defi": "DeFi",
            "nft": "NFT",
            "layer": "Layer 2",
            "web3": "Web3",
            "dao": "DAO",
            "gamefi": "GameFi",
            "метавселен": "метавселенной",
            "стейк": "стейкинге",
            "ликвидност": "ликвидности",
            "yield": "yield farming",
        }

        context_lower = context.lower()
        for key, value in keywords.items():
            if key in context_lower:
                return value

        # Если не нашли, возвращаем общий термин
        return "крипте"

    def _add_variations(self, comment: str) -> str:
        """Добавить вариативность в комментарий"""
        # Случайные модификации
        variations = [
            ("...", "..."),
            ("...", "… "),
            ("🔔", "🔔"),
            ("🚀", "🚀"),
            ("📈", "📈"),
            ("👀", "👀"),
            ("", " 👇"),
            ("", " ☝️"),
        ]

        # Применяем случайную вариацию с вероятностью 30%
        if random.random() < 0.3:
            old, new = random.choice(variations)
            if old in comment:
                comment = comment.replace(old, new)
            elif old == "":
                comment += new

        return comment

    def generate_thread_hook(self) -> str:
        """Генерировать хук для треда (первый твит)"""
        hooks = [
            "Тред о том, почему {topic} изменит всё 🧵",
            "Непопулярное мнение о {topic} (тред) 👇",
            "То, что никто не говорит о {topic} 🤐",
            "Разбор {topic} для тех, кто в теме 🧵",
            "Почему я all-in в {topic} (личный опыт) 💎",
            "{topic}: полный гайд для начинающих 📚",
            "3 причины почему {topic} - это будущее 🚀",
        ]

        topics = ["DeFi 2.0", "новый L2", "этот протокол", "данный подход", "эта стратегия"]
        topic = random.choice(topics)
        hook = random.choice(hooks)

        return hook.replace("{topic}", topic)