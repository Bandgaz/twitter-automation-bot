import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
import random

from database.db_manager import db_manager
from database.models import Campaign, ShillerRing, Account, Activity
from core.browser_manager import browser_manager
from core.twitter_client import TwitterClient
from utils.twitter_helpers import generate_comment_variation, generate_quote_text
from .ring_manager import RingManager


class ShillingEngine:
    """Движок для управления процессом шиллинга"""

    def __init__(self, campaign: Campaign):
        self.campaign = campaign
        self.is_running = False
        self.rounds_completed = 0
        self.ring_managers = {}  # ring_id -> RingManager
        self.tasks = []

    async def start(self):
        """Запуск движка шиллинга"""
        if self.is_running:
            logger.warning("Движок уже запущен")
            return

        self.is_running = True
        logger.info(f"🚀 Запуск шиллинга для ${self.campaign.token_name}")

        # Получаем активные кольца
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            result = await session.execute(
                select(ShillerRing)
                .where(ShillerRing.is_active == True)
                .options(
                    selectinload(ShillerRing.members),
                    selectinload(ShillerRing.targets)
                )
            )
            rings = result.scalars().all()

        # Создаем менеджеры для каждого кольца
        for ring in rings:
            manager = RingManager(ring, self.campaign)
            self.ring_managers[ring.id] = manager

            # Запускаем задачу для кольца
            task = asyncio.create_task(self._run_ring_loop(manager))
            self.tasks.append(task)

        logger.info(f"✅ Запущено {len(self.ring_managers)} колец")

    async def stop(self):
        """Остановка движка"""
        self.is_running = False

        # Останавливаем все менеджеры
        for manager in self.ring_managers.values():
            await manager.stop()

        # Отменяем все задачи
        for task in self.tasks:
            task.cancel()

        # Ждем завершения
        await asyncio.gather(*self.tasks, return_exceptions=True)

        self.tasks.clear()
        self.ring_managers.clear()

        logger.info("🛑 Движок шиллинга остановлен")

    async def _run_ring_loop(self, manager: RingManager):
        """Цикл работы одного кольца"""
        while self.is_running:
            try:
                # Выполняем один раунд кольца
                await manager.execute_round()
                self.rounds_completed += 1

                # Задержка между раундами (30-60 минут)
                delay = random.randint(1800, 3600)
                logger.info(f"⏱ Кольцо {manager.ring.id} завершило раунд. Пауза {delay // 60} минут")
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Ошибка в кольце {manager.ring.id}: {e}")
                await asyncio.sleep(300)  # 5 минут при ошибке


class RingManager:
    """Менеджер для управления одним кольцом шиллеров"""

    def __init__(self, ring: ShillerRing, campaign: Campaign):
        self.ring = ring
        self.campaign = campaign
        self.members = list(ring.members)
        self.targets = list(ring.targets)
        self.round_number = 0
        self.contexts = {}  # account_id -> BrowserContext

    async def stop(self):
        """Остановка менеджера"""
        # Закрываем все контексты
        for account_id, context in self.contexts.items():
            await browser_manager.close_context(account_id)
        self.contexts.clear()

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
                        continue

                # Выполняем действия участника
                await self._execute_member_actions(client, member, i, interactions)

            except Exception as e:
                logger.error(f"Ошибка участника @{member.username}: {e}")
            finally:
                await client.close()

            # Задержка между участниками
            await asyncio.sleep(random.randint(60, 120))

    async def _execute_member_actions(self, client: TwitterClient, member: Account,
                                      position: int, interactions: List[Dict]):
        """Выполнить действия одного участника"""
        logger.info(f"👤 @{member.username} начинает действия")

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

        # Логируем активность
        await self._log_activity(member.id, "comment", comment_text, commented)

        # 2. Лайк и цитата поста токена
        if self.campaign.quote_link:
            # Лайк
            await client.like_tweet(self.campaign.quote_link)
            await self._log_activity(member.id, "like", self.campaign.quote_link)

            # Цитата с хэштегами
            quote_text = generate_quote_text(self.campaign.token_name)
            hashtags = ["#Solana", "#Memecoin", f"#{self.campaign.token_name}"]

            await client.quote_tweet(
                self.campaign.quote_link,
                quote_text,
                hashtags
            )
            await self._log_activity(member.id, "quote", quote_text)

        # 3. Взаимодействие с предыдущими участниками
        if position > 0:
            await self._interact_with_previous_members(client, member, position)

        # 4. Кольцевой возврат для первого участника
        if position == 0 and self.round_number > 1:
            await self._ring_return(client, member)

    def _generate_rotation(self, round_num: int) -> List[Dict]:
        """Генерировать схему ротации для раунда"""
        # Простая ротация для примера
        # В реальности здесь должна быть сложная логика из ТЗ
        n = len(self.members)
        interactions = []

        for i in range(n):
            next_idx = (i + round_num) % n
            if i != next_idx:
                interactions.append({
                    "from": i,
                    "to": next_idx
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
        # TODO: Реализовать поиск комментариев предыдущих участников
        # и взаимодействие с ними (лайки, ответы)
        pass

    async def _ring_return(self, client: TwitterClient, member: Account):
        """Кольцевой возврат для первого участника"""
        # TODO: Реализовать поиск комментария последнего участника
        # и ответ на него
        pass

    async def _log_activity(self, account_id: int, action_type: str,
                            content: str, count: int = 1):
        """Логировать активность"""
        async with db_manager.get_async_session() as session:
            for _ in range(count):
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