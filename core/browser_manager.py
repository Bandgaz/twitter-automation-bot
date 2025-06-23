import asyncio
import random
from typing import Dict, Optional, List
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext
from fake_useragent import UserAgent
from loguru import logger

from config import HEADLESS_MODE, BROWSER_TYPE, USER_DATA_DIR, ANTIDETECT_CONFIG
from database.models import Account, Proxy


class BrowserManager:
    """Менеджер для управления браузерами и контекстами"""

    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[int, BrowserContext] = {}  # account_id -> context
        self.ua = UserAgent()

    async def initialize(self):
        """Инициализация Playwright"""
        self.playwright = await async_playwright().start()
        logger.info("Playwright инициализирован")

    async def cleanup(self):
        """Очистка ресурсов"""
        # Закрытие всех контекстов
        for context in self.contexts.values():
            await context.close()
        self.contexts.clear()

        # Закрытие браузера
        if self.browser:
            await self.browser.close()

        # Остановка Playwright
        if self.playwright:
            await self.playwright.stop()

        logger.info("Браузеры закрыты")

    async def launch_browser(self):
        """Запуск браузера"""
        if self.browser:
            return self.browser

        browser_launch_options = {
            "headless": HEADLESS_MODE,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        }

        if BROWSER_TYPE == "chromium":
            self.browser = await self.playwright.chromium.launch(**browser_launch_options)
        elif BROWSER_TYPE == "firefox":
            self.browser = await self.playwright.firefox.launch(**browser_launch_options)
        elif BROWSER_TYPE == "webkit":
            self.browser = await self.playwright.webkit.launch(**browser_launch_options)
        else:
            raise ValueError(f"Неподдерживаемый тип браузера: {BROWSER_TYPE}")

        logger.info(f"Браузер {BROWSER_TYPE} запущен")
        return self.browser

    async def create_context(self, account: Account) -> BrowserContext:
        """Создать контекст браузера для аккаунта"""
        if not self.browser:
            await self.launch_browser()

        # Проверяем, есть ли уже контекст для этого аккаунта
        if account.id in self.contexts:
            return self.contexts[account.id]

        # Настройки контекста
        context_options = {
            "viewport": self._get_random_viewport(),
            "user_agent": self._get_user_agent(),
            "locale": "en-US",
            "timezone_id": self._get_random_timezone(),
            "permissions": ["geolocation"],
            "color_scheme": random.choice(["light", "dark"]),
            "storage_state": None,  # Будет загружено из БД если есть
        }

        # Настройка прокси если есть
        if account.proxy:
            context_options["proxy"] = {
                "server": f"{account.proxy.protocol}://{account.proxy.host}:{account.proxy.port}",
            }
            if account.proxy.username:
                context_options["proxy"]["username"] = account.proxy.username
                context_options["proxy"]["password"] = account.proxy.password

        # Создание контекста
        context = await self.browser.new_context(**context_options)

        # Антидетект настройки
        await self._apply_antidetect_measures(context)

        # Загрузка cookies если есть
        if account.cookies:
            await context.add_cookies(account.cookies)

        # Сохраняем контекст
        self.contexts[account.id] = context

        logger.info(f"Контекст создан для @{account.username}")
        return context

    async def close_context(self, account_id: int):
        """Закрыть контекст для аккаунта"""
        if account_id in self.contexts:
            context = self.contexts[account_id]
            await context.close()
            del self.contexts[account_id]
            logger.info(f"Контекст закрыт для аккаунта ID: {account_id}")

    def _get_random_viewport(self) -> Dict:
        """Получить случайный viewport"""
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1536, "height": 864},
            {"width": 1680, "height": 1050},
        ]

        if ANTIDETECT_CONFIG["randomize_viewport"]:
            viewport = random.choice(viewports)
            # Небольшая рандомизация
            viewport["width"] += random.randint(-50, 50)
            viewport["height"] += random.randint(-50, 50)
            return viewport
        else:
            return viewports[0]

    def _get_user_agent(self) -> str:
        """Получить user agent"""
        if ANTIDETECT_CONFIG["randomize_user_agent"]:
            return self.ua.random
        else:
            return self.ua.chrome

    def _get_random_timezone(self) -> str:
        """Получить случайную временную зону"""
        timezones = [
            "America/New_York",
            "America/Chicago",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]

        if ANTIDETECT_CONFIG["randomize_timezone"]:
            return random.choice(timezones)
        else:
            return "America/New_York"

    async def _apply_antidetect_measures(self, context: BrowserContext):
        """Применить антидетект меры"""
        # Добавляем скрипты для обхода детекта автоматизации
        await context.add_init_script("""
            // Удаление следов webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Маскировка плагинов
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ]
            });

            // Маскировка языков
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Добавление chrome в user agent
            if (!navigator.userAgent.includes('Chrome')) {
                Object.defineProperty(navigator, 'userAgent', {
                    get: () => navigator.userAgent + ' Chrome/91.0.4472.124'
                });
            }

            // WebGL рандомизация
            if (%s) {
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.apply(this, arguments);
                };
            }

            // Canvas рандомизация
            if (%s) {
                const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function() {
                    const imageData = originalGetImageData.apply(this, arguments);
                    for (let i = 0; i < imageData.data.length; i++) {
                        imageData.data[i] += Math.random() * 0.1;
                    }
                    return imageData;
                };
            }
        """ % (
            str(ANTIDETECT_CONFIG["randomize_webgl"]).lower(),
            str(ANTIDETECT_CONFIG["randomize_canvas"]).lower()
        ))

    async def get_context_for_account(self, account: Account) -> BrowserContext:
        """Получить или создать контекст для аккаунта"""
        if account.id not in self.contexts:
            await self.create_context(account)
        return self.contexts[account.id]

    async def save_storage_state(self, account_id: int) -> Dict:
        """Сохранить состояние хранилища контекста"""
        if account_id in self.contexts:
            context = self.contexts[account_id]
            storage_state = await context.storage_state()
            return storage_state
        return {}

    async def parallel_contexts(self, accounts: List[Account], max_parallel: int = 3):
        """Создать контексты для нескольких аккаунтов параллельно"""
        semaphore = asyncio.Semaphore(max_parallel)

        async def create_with_limit(account):
            async with semaphore:
                return await self.create_context(account)

        tasks = [create_with_limit(account) for account in accounts]
        contexts = await asyncio.gather(*tasks)
        return contexts


# Глобальный экземпляр менеджера
browser_manager = BrowserManager()