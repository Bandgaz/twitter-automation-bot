import asyncio
import random
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from playwright.async_api import Page, Browser, BrowserContext
from loguru import logger

from config import TWITTER_LIMITS, USER_DATA_DIR
from utils.twitter_helpers import random_delay, human_like_typing


class TwitterClient:
    """Базовый клиент для работы с Twitter через Playwright"""

    def __init__(self, account_data: Dict[str, Any], context: BrowserContext):
        self.account_data = account_data
        self.username = account_data['username']
        self.password = account_data['password']
        self.context = context
        self.page: Optional[Page] = None
        self.is_logged_in = False

    async def initialize(self):
        """Инициализация клиента"""
        self.page = await self.context.new_page()

        # Установка viewport для имитации реального устройства
        await self.page.set_viewport_size({
            "width": random.randint(1366, 1920),
            "height": random.randint(768, 1080)
        })

        # Загрузка cookies если есть
        if self.account_data.get('cookies'):
            await self.context.add_cookies(self.account_data['cookies'])

    async def close(self):
        """Закрытие страницы"""
        if self.page:
            await self.page.close()

    async def login(self) -> bool:
        """Авторизация в Twitter"""
        try:
            logger.info(f"Попытка входа для @{self.username}")

            # Переход на страницу входа
            await self.page.goto("https://twitter.com/login", wait_until="networkidle")
            await random_delay(2, 4)

            # Проверка, может уже авторизованы
            if await self.check_logged_in():
                logger.info(f"@{self.username} уже авторизован")
                self.is_logged_in = True
                return True

            # Ввод username/email
            username_input = await self.page.wait_for_selector(
                'input[autocomplete="username"]',
                timeout=10000
            )
            await username_input.click()
            await human_like_typing(self.page, self.username)
            await random_delay(1, 2)

            # Кнопка далее
            await self.page.click('div[role="button"]:has-text("Next")')
            await random_delay(2, 3)

            # Проверка на дополнительную верификацию (email/phone)
            try:
                verification_input = await self.page.wait_for_selector(
                    'input[data-testid="ocfEnterTextTextInput"]',
                    timeout=5000
                )
                if verification_input and self.account_data.get('email'):
                    await verification_input.click()
                    await human_like_typing(self.page, self.account_data['email'])
                    await self.page.click('div[role="button"]:has-text("Next")')
                    await random_delay(2, 3)
            except:
                # Если нет дополнительной верификации, продолжаем
                pass

            # Ввод пароля
            password_input = await self.page.wait_for_selector(
                'input[type="password"]',
                timeout=10000
            )
            await password_input.click()
            await human_like_typing(self.page, self.password)
            await random_delay(1, 2)

            # Вход
            await self.page.click('div[role="button"]:has-text("Log in")')
            await random_delay(3, 5)

            # Проверка успешного входа
            if await self.check_logged_in():
                logger.info(f"✅ Успешный вход для @{self.username}")
                self.is_logged_in = True

                # Сохранение cookies
                cookies = await self.context.cookies()
                self.account_data['cookies'] = cookies

                return True
            else:
                logger.error(f"❌ Не удалось войти для @{self.username}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при входе @{self.username}: {str(e)}")
            return False

    async def check_logged_in(self) -> bool:
        """Проверка авторизации"""
        try:
            # Проверяем наличие кнопки твита или профиля
            await self.page.wait_for_selector(
                'a[data-testid="AppTabBar_Profile_Link"], a[href="/compose/tweet"]',
                timeout=5000
            )
            return True
        except:
            return False

    async def navigate_to_home(self):
        """Переход на главную"""
        await self.page.goto("https://twitter.com/home", wait_until="networkidle")
        await random_delay(2, 3)

    async def tweet(self, text: str, hashtags: List[str] = None) -> bool:
        """Опубликовать твит"""
        try:
            logger.info(f"@{self.username} публикует твит")

            # Переход на главную
            await self.navigate_to_home()

            # Клик на кнопку создания твита
            tweet_button = await self.page.wait_for_selector(
                'a[href="/compose/tweet"], div[data-testid="tweetButtonInline"]',
                timeout=10000
            )
            await tweet_button.click()
            await random_delay(2, 3)

            # Ввод текста
            tweet_input = await self.page.wait_for_selector(
                'div[data-testid="tweetTextarea_0"]',
                timeout=10000
            )
            await tweet_input.click()

            # Добавляем хэштеги если есть
            full_text = text
            if hashtags:
                full_text += "\n\n" + " ".join(hashtags)

            await human_like_typing(self.page, full_text)
            await random_delay(2, 3)

            # Публикация
            post_button = await self.page.wait_for_selector(
                'div[data-testid="tweetButtonInline"]',
                timeout=5000
            )
            await post_button.click()

            await random_delay(3, 5)
            logger.info(f"✅ Твит опубликован @{self.username}")
            return True

        except Exception as e:
            logger.error(f"Ошибка публикации твита @{self.username}: {str(e)}")
            return False

    async def like_tweet(self, tweet_url: str) -> bool:
        """Поставить лайк твиту"""
        try:
            await self.page.goto(tweet_url, wait_until="networkidle")
            await random_delay(2, 3)

            # Найти кнопку лайка
            like_button = await self.page.wait_for_selector(
                'div[data-testid="like"]',
                timeout=10000
            )
            await like_button.click()

            await random_delay(1, 2)
            logger.info(f"✅ Лайк поставлен @{self.username}")
            return True

        except Exception as e:
            logger.error(f"Ошибка лайка @{self.username}: {str(e)}")
            return False

    async def comment_on_tweet(self, tweet_url: str, comment_text: str) -> bool:
        """Оставить комментарий под твитом"""
        try:
            await self.page.goto(tweet_url, wait_until="networkidle")
            await random_delay(2, 3)

            # Найти поле для комментария
            reply_input = await self.page.wait_for_selector(
                'div[data-testid="tweetTextarea_0"]',
                timeout=10000
            )
            await reply_input.click()
            await human_like_typing(self.page, comment_text)
            await random_delay(2, 3)

            # Отправить комментарий
            reply_button = await self.page.wait_for_selector(
                'div[data-testid="tweetButtonInline"]',
                timeout=5000
            )
            await reply_button.click()

            await random_delay(2, 4)
            logger.info(f"✅ Комментарий оставлен @{self.username}")
            return True

        except Exception as e:
            logger.error(f"Ошибка комментария @{self.username}: {str(e)}")
            return False

    async def quote_tweet(self, tweet_url: str, quote_text: str, hashtags: List[str] = None) -> bool:
        """Процитировать твит"""
        try:
            await self.page.goto(tweet_url, wait_until="networkidle")
            await random_delay(2, 3)

            # Найти кнопку ретвита
            retweet_button = await self.page.wait_for_selector(
                'div[data-testid="retweet"]',
                timeout=10000
            )
            await retweet_button.click()
            await random_delay(1, 2)

            # Выбрать "Quote Tweet"
            quote_option = await self.page.wait_for_selector(
                'div[role="menuitem"]:has-text("Quote Tweet")',
                timeout=5000
            )
            await quote_option.click()
            await random_delay(2, 3)

            # Ввести текст цитаты
            quote_input = await self.page.wait_for_selector(
                'div[data-testid="tweetTextarea_0"]',
                timeout=10000
            )
            await quote_input.click()

            full_text = quote_text
            if hashtags:
                full_text += "\n\n" + " ".join(hashtags)

            await human_like_typing(self.page, full_text)
            await random_delay(2, 3)

            # Опубликовать
            post_button = await self.page.wait_for_selector(
                'div[data-testid="tweetButton"]',
                timeout=5000
            )
            await post_button.click()

            await random_delay(3, 5)
            logger.info(f"✅ Цитата опубликована @{self.username}")
            return True

        except Exception as e:
            logger.error(f"Ошибка цитирования @{self.username}: {str(e)}")
            return False

    async def find_and_comment_on_top_posts(self, target_accounts: List[str],
                                            comment_text: str, limit: int = 10) -> int:
        """Найти и прокомментировать топовые посты"""
        commented_count = 0

        for target in target_accounts[:limit]:
            if commented_count >= limit:
                break

            try:
                # Переход на профиль
                profile_url = f"https://twitter.com/{target.replace('@', '')}"
                await self.page.goto(profile_url, wait_until="networkidle")
                await random_delay(2, 3)

                # Найти первый пост
                first_post = await self.page.query_selector('article[data-testid="tweet"]')
                if first_post:
                    # Клик на пост
                    await first_post.click()
                    await random_delay(2, 3)

                    # Найти топ комментарий
                    comments = await self.page.query_selector_all('article[data-testid="tweet"]')
                    if len(comments) > 1:  # Первый - это сам пост
                        # Кликнуть "Reply" под топ комментарием
                        top_comment = comments[1]
                        reply_button = await top_comment.query_selector('div[data-testid="reply"]')
                        if reply_button:
                            await reply_button.click()
                            await random_delay(2, 3)

                            # Написать комментарий
                            reply_input = await self.page.wait_for_selector(
                                'div[data-testid="tweetTextarea_0"]',
                                timeout=5000
                            )
                            await reply_input.click()
                            await human_like_typing(self.page, comment_text)
                            await random_delay(2, 3)

                            # Отправить
                            send_button = await self.page.wait_for_selector(
                                'div[data-testid="tweetButtonInline"]',
                                timeout=5000
                            )
                            await send_button.click()

                            commented_count += 1
                            await random_delay(3, 5)
                            logger.info(f"✅ Комментарий оставлен под @{target}")

            except Exception as e:
                logger.error(f"Ошибка комментирования @{target}: {str(e)}")
                continue

            # Задержка между аккаунтами
            await random_delay(5, 10)

        return commented_count