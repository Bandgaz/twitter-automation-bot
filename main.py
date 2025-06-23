#!/usr/bin/env python3
"""
Twitter Automation Bot
Главный файл запуска приложения
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from config import LOG_LEVEL, LOG_FORMAT, LOGS_DIR
from bot.handlers import setup_handlers
from database.db_manager import init_database
from core.browser_manager import BrowserManager
from telegram import Update
from telegram.ext import Application

# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    format=LOG_FORMAT,
    level=LOG_LEVEL,
    colorize=True
)
logger.add(
    LOGS_DIR / "twitter_automation.log",
    format=LOG_FORMAT,
    level=LOG_LEVEL,
    rotation="1 day",
    retention="30 days",
    compression="zip"
)


async def error_handler(update: Update, context):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")

    if update:
        # Определяем, откуда пришло обновление
        if update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Произошла ошибка. Пожалуйста, попробуйте позже."
                )
            except:
                pass


async def startup(application):
    """Инициализация при запуске"""
    logger.info("🚀 Запуск Twitter Automation Bot...")

    # Инициализация базы данных
    await init_database()
    logger.info("✅ База данных инициализирована")

    # Инициализация Playwright
    browser_manager = BrowserManager()
    await browser_manager.initialize()
    logger.info("✅ Playwright инициализирован")

    logger.info("✅ Бот готов к работе!")


async def shutdown(application):
    """Очистка при завершении"""
    logger.info("🛑 Завершение работы...")

    # Закрытие браузеров
    browser_manager = BrowserManager()
    await browser_manager.cleanup()

    logger.info("✅ Завершение работы выполнено")


def main():
    """Главная функция"""
    from config import TELEGRAM_BOT_TOKEN

    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не установлен в .env файле!")
        sys.exit(1)

    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


    # Настройка обработчиков
    setup_handlers(application)

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запуск startup функции перед началом polling
    application.post_init = startup

    # Запуск shutdown функции при остановке
    application.post_shutdown = shutdown

    # Запуск бота
    logger.info("🤖 Telegram бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"💥 Критическая ошибка: {e}")
        sys.exit(1)