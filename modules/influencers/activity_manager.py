import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
import random

from database.db_manager import db_manager
from database.models import Account, InfluencerSource, Activity
from core.browser_manager import browser_manager
from core.twitter_client import TwitterClient
from utils.twitter_helpers import calculate_sleep_schedule, generate_hashtags
from .content_generator import ContentGenerator


class InfluencerActivityManager:
    """Менеджер автоматической активности инфлюенсеров"""

    def __init__(self):
        self.is_running = False
        self.tasks = {}  # account_id -> asyncio.Task
        self.content_generator = ContentGenerator()

    async def start(self):
        """Запуск менеджера"""
        if self.is_running:
            logger.warning("Менеджер уже запущен")
            return

        self.is_running = True
        logger.info("🚀 Запуск менеджера инфлюенсеров")

        # Получаем всех инфлюенсеров
        influencers = await db_manager.get_accounts_by_type("influencer")

        # Запускаем задачу для каждого инфлюенсера
        for influencer in influencers:
            if influencer.status == "active":
                task = asyncio.create_task(self._run_influencer_loop(influencer))
                self.tasks[influencer.id] = task

        logger.info(f"✅ Запущено {len(self.tasks)} инфлюенсеров")

    async def stop(self):
        """Остановка менеджера"""
        self.is_running = False

        # Отменяем все задачи
        for task in self.tasks.values():
            task.cancel()

        # Ждем завершения
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()

        logger.info("🛑 Менеджер инфлюенсеров остановлен")

    async def _run_influencer_loop(self, account: Account):
        """Основной цикл работы инфлюенсера"""
        logger.info(f"▶️ Запуск цикла для @{account.username}")

        # Создаем контекст браузера
        context = await browser_manager.create_context(account)
        client = TwitterClient(account.__dict__, context)

        try:
            await client.initialize()

            # Логин
            if not await client.login():
                logger.error(f"❌ Не удалось войти @{account.username}")
                account.status = "suspended"
                await db_manager.update_account_status(account.id, "suspended")
                return

            # Основной цикл
            while self.is_running:
                try:
                    # Проверяем расписание сна
                    schedule = calculate_sleep_schedule(
                        work_hours=10,
                        sleep_hours=14
                    )

                    if not schedule['is_working']:
                        # Время спать
                        sleep_until = schedule['next_sleep']
                        sleep_duration = (sleep_until - datetime.now()).total_seconds()
                        logger.info(f"😴 @{account.username} спит до {sleep_until}")
                        await asyncio.sleep(sleep_duration)
                        continue

                    # Выполняем случайное действие
                    await self._perform_random_action(client, account)

                    # Случайная задержка между действиями
                    delay = random.randint(300, 900)  # 5-15 минут
                    await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"Ошибка в цикле @{account.username}: {e}")
                    await asyncio.sleep(60)

        finally:
            await client.close()
            await browser_manager.close_context(account.id)

    async def _perform_random_action(self, client: TwitterClient, account: Account):
        """Выполнить случайное действие"""
        actions = [
            ("post", 0.2),  # 20% - публикация поста
            ("comment", 0.4),  # 40% - комментирование
            ("like", 0.3),  # 30% - лайки
            ("quote", 0.1),  # 10% - цитирование
        ]

        # Выбираем действие по весам
        action = random.choices(
            [a[0] for a in actions],
            weights=[a[1] for a in actions]
        )[0]

        logger.info(f"🎯 @{account.username} выполняет: {action}")

        if action == "post":
            await self._create_post(client, account)
        elif action == "comment":
            await self._create_comment(client, account)
        elif action == "like":
            await self._like_posts(client, account)
        elif action == "quote":
            await self._quote_post(client, account)

    async def _create_post(self, client: TwitterClient, account: Account):
        """Создать пост на основе источников"""
        # Получаем источники
        sources = account.influencer_sources
        if not sources:
            logger.warning(f"У @{account.username} нет источников")
            return

        # Выбираем случайный источник с учетом важности
        source = self._select_source_by_importance(sources)

        # Генерируем контент
        content = await self.content_generator.generate_from_source(
            source.source_username
        )

        if content:
            # Добавляем хэштеги
            hashtags = await db_manager.get_random_hashtags(3)

            # Публикуем
            success = await client.tweet(content, hashtags)

            # Логируем активность
            await self._log_activity(
                account.id,
                "tweet",
                content=content,
                status="success" if success else "failed"
            )

    async def _create_comment(self, client: TwitterClient, account: Account):
        """Создать триггерный комментарий"""
        # Получаем список крупных аккаунтов
        target_accounts = [
            "binance", "coinbase", "solana", "ethereum",
            "VitalikButerin", "cz_binance", "SBF_FTX"
        ]

        # Генерируем комментарий
        from utils.twitter_helpers import generate_influencer_comment
        comment = generate_influencer_comment()

        # Комментируем
        commented = await client.find_and_comment_on_top_posts(
            target_accounts,
            comment,
            limit=1
        )

        # Логируем активность
        await self._log_activity(
            account.id,
            "comment",
            content=comment,
            status="success" if commented > 0 else "failed"
        )

    async def _like_posts(self, client: TwitterClient, account: Account):
        """Поставить лайки на посты"""
        # TODO: Реализовать логику лайков
        pass

    async def _quote_post(self, client: TwitterClient, account: Account):
        """Процитировать пост другого инфлюенсера"""
        # TODO: Реализовать логику цитирования
        pass

    def _select_source_by_importance(self, sources: List[InfluencerSource]) -> InfluencerSource:
        """Выбрать источник с учетом важности"""
        if not sources:
            return None

        # Выбираем с учетом веса importance_score
        weights = [s.importance_score for s in sources]
        return random.choices(sources, weights=weights)[0]

    async def _log_activity(self, account_id: int, action_type: str,
                            content: str = None, status: str = "success"):
        """Логировать активность в БД"""
        async with db_manager.get_async_session() as session:
            activity = Activity(
                account_id=account_id,
                action_type=action_type,
                content=content,
                status=status,
                created_at=datetime.utcnow()
            )
            session.add(activity)
            await session.commit()