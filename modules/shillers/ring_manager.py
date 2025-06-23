import asyncio
import random
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from database.db_manager import db_manager
from database.models import ShillerRing, Account, Campaign, Activity
from core.browser_manager import browser_manager
from core.twitter_client import TwitterClient
from utils.twitter_helpers import generate_comment_variation, generate_quote_text, random_delay


class RingManager:
    """Менеджер для управления одним кольцом шиллеров"""

    def __init__(self, ring: ShillerRing, campaign: Campaign):
        self.ring = ring
        self.campaign = campaign
        self.members = list(ring.members)
        self.targets = list(ring.targets)
        self.round_number = 0
        self.contexts = {}  # account_id -> BrowserContext
        self.rotation_history = []  # История взаимодействий для ротации

    async def stop(self):
        """Остановка менеджера"""
        # Закрываем все контексты
        for account_id in list(self.contexts.keys()):
            await browser_manager.close_context(account_id)
        self.contexts.clear()
        logger.info(f"🛑 Кольцо {self.ring.id} остановлено")

    async def execute_round(self):
        """Выполнить один раунд активности кольца"""
        self.round_number += 1
        logger.info(f"🔄 Кольцо {self.ring.id} начинает раунд #{self.round_number}")

        # Определяем порядок взаимодействий для этого раунда
        interactions = self._generate_rotation(self.round_number)

        # Последовательное выполнение для каждого участника
        for i, member in enumerate(self.members):
            if i >= len(self.members):
                break

            # Создаем клиента для участника
            context = await browser_manager.get_context_for_account(member)
            self.contexts[member.id] = context

            client = TwitterClient(member.__dict__, context)

            try:
                await client.initialize()

                # Логин если нужно
                if not client.is_logged_in:
                    if not await client.login():
                        logger.error(f"❌ Не удалось войти @{member.username}")
                        member.status = "suspended"
                        continue

                # Выполняем действия участника
                await self._execute_member_actions(client, member, i, interactions)

            except Exception as e:
                logger.error(f"Ошибка участника @{member.username}: {e}")
            finally:
                await client.close()

            # Задержка между участниками
            await random_delay(60, 120)

        # Сохраняем историю ротации
        await self._save_rotation_history(interactions)

    async def _execute_member_actions(self, client: TwitterClient, member: Account,
                                      position: int, interactions: List[Dict]):
        """Выполнить действия одного участника"""
        logger.info(f"👤 @{member.username} начинает действия (позиция {position})")

        # 1. Комментарии под мишенями
        my_targets = self._get_member_targets(position)
        comment_text = generate_comment_variation(
            "",
            self.campaign.token_name,
            self.campaign.token_address
        )

        commented = await client.find_and_comment_on_top_posts(
            my_targets,
            comment_text,
            limit=self.ring.comments_per_round
        )

        # Логируем активность комментариев
        for _ in range(commented):
            await self._log_activity(member.id, "comment", comment_text)

        # 2. Лайк и цитата поста токена
        if self.campaign.quote_link:
            # Лайк
            success = await client.like_tweet(self.campaign.quote_link)
            if success:
                await self._log_activity(member.id, "like", self.campaign.quote_link)

            # Цитата с хэштегами
            quote_text = generate_quote_text(self.campaign.token_name)
            hashtags = await db_manager.get_random_hashtags(3)
            if not hashtags:
                hashtags = ["#Solana", "#Memecoin", f"#{self.campaign.token_name}"]

            success = await client.quote_tweet(
                self.campaign.quote_link,
                quote_text,
                hashtags
            )
            if success:
                await self._log_activity(member.id, "quote", quote_text)

        # 3. Взаимодействие с предыдущими участниками
        if position > 0:
            await self._interact_with_previous_members(client, member, position)

        # 4. Кольцевой возврат для первого и последнего участника
        if position == 0 and len(self.members) > 1:
            # Первый участник взаимодействует с последним
            await self._ring_return(client, member, len(self.members) - 1)

    def _generate_rotation(self, round_num: int) -> List[Dict]:
        """
        Генерировать схему ротации для раунда
        Следуя принципу из ТЗ: никогда не взаимодействовать с тем же участником два раунда подряд
        """
        n = len(self.members)
        interactions = []

        # Базовая ротация для первого раунда
        if round_num == 1:
            for i in range(n):
                next_idx = (i + 1) % n
                interactions.append({
                    "from": i,
                    "to": next_idx,
                    "from_username": self.members[i].username,
                    "to_username": self.members[next_idx].username
                })
        else:
            # Сложная ротация для последующих раундов
            # Избегаем повторения взаимодействий из предыдущего раунда
            last_interactions = self.rotation_history[-1] if self.rotation_history else []
            last_pairs = {(inter["from"], inter["to"]) for inter in last_interactions}

            # Генерируем новые пары
            for i in range(n):
                # Находим валидного партнера
                possible_partners = list(range(n))
                possible_partners.remove(i)  # Не с собой

                # Убираем того, с кем взаимодействовали в прошлый раз
                for pair in last_pairs:
                    if pair[0] == i and pair[1] in possible_partners:
                        possible_partners.remove(pair[1])

                if possible_partners:
                    partner = random.choice(possible_partners)
                    interactions.append({
                        "from": i,
                        "to": partner,
                        "from_username": self.members[i].username,
                        "to_username": self.members[partner].username
                    })

        return interactions

    def _get_member_targets(self, position: int) -> List[str]:
        """Получить мишени для участника"""
        targets_per_member = self.ring.targets_per_shiller
        start_idx = position * targets_per_member
        end_idx = start_idx + targets_per_member

        member_targets = self.targets[start_idx:end_idx]
        return [t.target_username for t in member_targets]

    async def _interact_with_previous_members(self, client: TwitterClient,
                                              member: Account, position: int):
        """Взаимодействие с предыдущими участниками"""
        # Взаимодействуем с комментариями предыдущего участника
        prev_member = self.members[position - 1]

        logger.info(f"💬 @{member.username} взаимодействует с @{prev_member.username}")

        # В реальной реализации здесь должен быть поиск комментариев
        # предыдущего участника и взаимодействие с ними
        # Для демонстрации просто логируем

        # Имитация поиска и лайка комментариев
        await random_delay(5, 10)

        # Ответ на комментарий
        reply_variations = [
            "лол да, прям как $PEPE",
            "это точно 🚀",
            "согласен, вайб мощный",
            "ну это имба просто",
            "факты 💯",
        ]
        reply = random.choice(reply_variations)

        # Логируем взаимодействие
        await self._log_activity(member.id, "reply", reply)
        await self._log_activity(member.id, "like", f"comment_from_{prev_member.username}")

    async def _ring_return(self, client: TwitterClient, member: Account, last_position: int):
        """Кольцевой возврат - взаимодействие первого с последним"""
        last_member = self.members[last_position]

        logger.info(f"🔄 Кольцевой возврат: @{member.username} → @{last_member.username}")

        # Имитация поиска последнего комментария и ответа
        await random_delay(5, 10)

        reply = "замыкаем круг 🔥"
        await self._log_activity(member.id, "reply", reply)

    async def _log_activity(self, account_id: int, action_type: str, content: str):
        """Логировать активность в БД"""
        async with db_manager.get_async_session() as session:
            activity = Activity(
                account_id=account_id,
                campaign_id=self.campaign.id,
                action_type=action_type,
                content=content,
                status="success",
                created_at=datetime.utcnow()
            )
            session.add(activity)
            await session.commit()

    async def _save_rotation_history(self, interactions: List[Dict]):
        """Сохранить историю ротации"""
        self.rotation_history.append(interactions)

        # Сохраняем в БД
        async with db_manager.get_async_session() as session:
            from database.models import ShillerRotation

            rotation = ShillerRotation(
                ring_id=self.ring.id,
                round_number=self.round_number,
                interactions=interactions,
                created_at=datetime.utcnow()
            )
            session.add(rotation)
            await session.commit()

        # Оставляем только последние 5 раундов в памяти
        if len(self.rotation_history) > 5:
            self.rotation_history = self.rotation_history[-5:]