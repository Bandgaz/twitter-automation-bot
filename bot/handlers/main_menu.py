from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from ..keyboards.main_kb import get_main_menu_keyboard
from database.db_manager import db_manager


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"Пользователь {user.full_name} ({user.id}) запустил бота")

    welcome_message = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🤖 Это бот для автоматизации Twitter активности.\n\n"
        "Выберите раздел из меню ниже:"
    )

    # Получаем статистику
    stats = await db_manager.get_statistics()

    stats_message = (
        f"\n📊 Текущая статистика:\n"
        f"👥 Всего аккаунтов: {stats.get('total_accounts', 0)}\n"
        f"🌐 Активных прокси: {stats.get('active_proxies', 0)}\n"
        f"📢 Кампаний: {stats.get('total_campaigns', 0)}"
    )

    await update.message.reply_text(
        welcome_message + stats_message,
        reply_markup=get_main_menu_keyboard()
    )


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик возврата в главное меню"""
    query = update.callback_query
    await query.answer()

    # Получаем статистику
    stats = await db_manager.get_statistics()

    menu_message = (
        "🏠 Главное меню\n\n"
        f"📊 Текущая статистика:\n"
        f"👥 Всего аккаунтов: {stats.get('total_accounts', 0)}\n"
        f"🌐 Активных прокси: {stats.get('active_proxies', 0)}\n"
        f"📢 Кампаний: {stats.get('total_campaigns', 0)}\n\n"
        "Выберите раздел:"
    )

    await query.edit_message_text(
        menu_message,
        reply_markup=get_main_menu_keyboard()
    )