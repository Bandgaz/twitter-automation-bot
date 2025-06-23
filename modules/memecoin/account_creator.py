import asyncio
from typing import Dict, Optional
from loguru import logger

from core.browser_manager import browser_manager
from core.twitter_client import TwitterClient
from database.db_manager import db_manager
from utils.twitter_helpers import random_delay, human_like_typing


class MemecoinAccountCreator:
    """Класс для создания и настройки аккаунта под мемкоин"""

    def __init__(self, account_data: Dict):
        """
        account_data должен содержать:
        - username: имя аккаунта
        - password: пароль
        - email: email (опционально)
        - email_password: пароль от email (опционально)
        """
        self.account_data = account_data
        self.client = None
        self.context = None

    async def setup_account(self, token_name: str, token_address: str,
                            narrative: str, telegram_link: str = None) -> bool:
        """
        Полная настройка аккаунта под мемкоин

        Args:
            token_name: Название токена (например, BANDGAZ)
            token_address: Адрес токена
            narrative: Нарратив/история токена
            telegram_link: Ссылка на Telegram (опционально)

        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Создаем аккаунт в БД
            account = await db_manager.add_account(
                username=self.account_data['username'],
                password=self.account_data['password'],
                account_type='memecoin',
                email=self.account_data.get('email'),
                email_password=self.account_data.get('email_password')
            )

            # Создаем браузерный контекст
            self.context = await browser_manager.create_context(account)
            self.client = TwitterClient(account.__dict__, self.context)

            await self.client.initialize()

            # Логин
            if not await self.client.login():
                logger.error(f"Не удалось войти в аккаунт @{account.username}")
                return False

            # Настройка профиля
            await self._setup_profile(token_name, token_address, narrative, telegram_link)

            # Создание закрепленного твита
            await self._create_pinned_tweet(token_name, token_address, narrative)

            logger.info(f"✅ Аккаунт мемкоина @{account.username} настроен")
            return True

        except Exception as e:
            logger.error(f"Ошибка настройки аккаунта мемкоина: {e}")
            return False
        finally:
            if self.client:
                await self.client.close()
            if self.context:
                await browser_manager.close_context(self.account_data.get('id', 0))

    async def _setup_profile(self, token_name: str, token_address: str,
                             narrative: str, telegram_link: str = None):
        """Настройка профиля аккаунта"""
        logger.info("🎨 Настройка профиля мемкоина")

        # Переход в настройки профиля
        await self.client.page.goto("https://twitter.com/settings/profile", wait_until="networkidle")
        await random_delay(3, 5)

        # Изменение имени
        name_variations = [
            f"{token_name} Labs",
            f"Dr. {token_name}",
            f"{narrative} Technician",
            f"Mr{token_name}",
            f"{narrative}Miner22"
        ]

        import random
        new_name = random.choice(name_variations)

        # Находим поле имени
        name_input = await self.client.page.wait_for_selector('input[name="name"]', timeout=10000)
        await name_input.click()
        await name_input.clear()
        await human_like_typing(self.client.page, new_name)
        await random_delay(1, 2)

        # Изменение описания (bio)
        bio_templates = [
            f"🚨 Survivor of the {narrative} Lab Incident\n"
            f"R&D | ${token_name} Dev | Not financial advice\n"
            f"📍 Somewhere near the blast zone",

            f"⚡ {narrative} Research Division\n"
            f"${token_name} | Community-driven | DYOR\n"
            f"🔬 Experimenting with the future",

            f"💥 {narrative} Protocol Engineer\n"
            f"Building ${token_name} | No promises, just vibes\n"
            f"🌐 Decentralized chaos",
        ]

        bio = random.choice(bio_templates)

        # Находим поле bio
        bio_input = await self.client.page.wait_for_selector('textarea[name="description"]', timeout=10000)
        await bio_input.click()
        await bio_input.clear()
        await human_like_typing(self.client.page, bio)
        await random_delay(1, 2)

        # Добавление ссылки
        if telegram_link or token_address:
            url_input = await self.client.page.wait_for_selector('input[name="url"]', timeout=10000)
            await url_input.click()
            await url_input.clear()

            # Приоритет Telegram, если нет - то адрес токена
            link = telegram_link if telegram_link else f"https://solscan.io/token/{token_address}"
            await human_like_typing(self.client.page, link)
            await random_delay(1, 2)

        # Сохранение изменений
        save_button = await self.client.page.wait_for_selector('div[data-testid="Profile_Save_Button"]', timeout=10000)
        await save_button.click()
        await random_delay(3, 5)

        logger.info("✅ Профиль настроен")

    async def _create_pinned_tweet(self, token_name: str, token_address: str, narrative: str):
        """Создание и закрепление твита с нарративом"""
        logger.info("📌 Создание закрепленного твита")

        # Шаблоны для твита
        tweet_templates = [
            f"💥 That's what happens when {narrative} mining rigs go nuclear\n\n"
            f"${token_name} launched: {token_address}\n\n"
            f"#{narrative.lower()} #explosion #crypto",

            f"⚡ The {narrative} incident changed everything\n\n"
            f"${token_name} is our response: {token_address}\n\n"
            f"#{narrative.lower()} #{token_name.lower()} #defi",

            f"🚨 WARNING: {narrative} exposure detected\n\n"
            f"${token_name} protocol activated: {token_address}\n\n"
            f"#crypto #{narrative.lower()} #memecoin",
        ]

        import random
        tweet_text = random.choice(tweet_templates)

        # Публикуем твит
        success = await self.client.tweet(tweet_text)

        if success:
            await random_delay(5, 8)

            # Переходим на страницу профиля
            await self.client.page.goto(f"https://twitter.com/{self.account_data['username']}",
                                        wait_until="networkidle")
            await random_delay(3, 5)

            # Находим первый твит (только что опубликованный)
            first_tweet = await self.client.page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)

            # Клик на меню твита (три точки)
            menu_button = await first_tweet.query_selector('div[data-testid="caret"]')
            if menu_button:
                await menu_button.click()
                await random_delay(1, 2)

                # Находим опцию "Pin to profile"
                pin_option = await self.client.page.wait_for_selector('div[role="menuitem"]:has-text("Pin to")',
                                                                      timeout=5000)
                if pin_option:
                    await pin_option.click()
                    await random_delay(2, 3)

                    # Подтверждение
                    confirm_button = await self.client.page.wait_for_selector(
                        'div[data-testid="confirmationSheetConfirm"]', timeout=5000)
                    if confirm_button:
                        await confirm_button.click()
                        logger.info("✅ Твит закреплен")

    async def update_avatar(self, image_path: str):
        """Обновление аватара (требует путь к изображению)"""
        # TODO: Реализовать загрузку аватара
        pass

    async def update_header(self, image_path: str):
        """Обновление обложки (требует путь к изображению)"""
        # TODO: Реализовать загрузку обложки
        pass