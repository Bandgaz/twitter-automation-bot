from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger
from datetime import datetime

from ..keyboards.main_kb import get_shillers_keyboard, get_back_keyboard, get_cancel_keyboard
from database.db_manager import db_manager
from database.models import Account, ShillerRing, ShillerTarget, Campaign
from modules.shillers.shilling_engine import ShillingEngine
from utils.validators import validate_token_address, validate_twitter_url, parse_target_accounts

# Глобальный движок шиллинга
shilling_engine = None


async def shillers_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню шиллеров"""
    query = update.callback_query
    await query.answer()

    # Получаем статистику
    shillers = await db_manager.get_accounts_by_type("shiller")

    async with db_manager.get_async_session() as session:
        from sqlalchemy import select, func

        # Кольца
        rings_result = await session.execute(
            select(func.count(ShillerRing.id)).where(ShillerRing.is_active == True)
        )
        rings_count = rings_result.scalar()

        # Активная кампания
        campaign = await db_manager.get_active_campaign()

    # Статус движка
    engine_status = "🔴 Остановлен"
    if shilling_engine and shilling_engine.is_running:
        engine_status = "🟢 Работает"

    message = (
        "📣 Управление шиллерами\n\n"
        f"📊 Статистика:\n"
        f"• Всего шиллеров: {len(shillers)}\n"
        f"• Активных колец: {rings_count}\n"
        f"• Кампания: {'✅ Активна' if campaign else '❌ Нет'}\n"
        f"• Статус движка: {engine_status}\n\n"
    )

    if campaign:
        message += (
            f"💰 Текущий токен: ${campaign.token_name}\n"
            f"📍 Адрес: {campaign.token_address[:8]}...{campaign.token_address[-6:]}\n\n"
        )

    message += "Выберите действие:"

    await query.edit_message_text(
        message,
        reply_markup=get_shillers_keyboard()
    )


async def configure_targets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка целевых аккаунтов"""
    query = update.callback_query
    await query.answer()

    # Проверяем наличие колец
    async with db_manager.get_async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(ShillerRing))
        rings = result.scalars().all()

    if not rings:
        await query.edit_message_text(
            "❌ Сначала создайте кольца шиллеров!",
            reply_markup=get_back_keyboard("shillers")
        )
        return

    # Считаем необходимое количество мишеней
    total_targets_needed = sum(ring.size * ring.targets_per_shiller for ring in rings)

    message = (
        "🎯 Настройка мишеней шиллинга\n\n"
        f"Количество колец: {len(rings)}\n"
        f"Необходимо мишеней: {total_targets_needed}\n\n"
        "Отправьте список крупных Twitter аккаунтов.\n"
        "По одному на строку, можно с @ или без:\n\n"
        "```\n"
        "@binance\n"
        "coinbase\n"
        "@VitalikButerin\n"
        "solana\n"
        "```"
    )

    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )

    context.user_data['waiting_for'] = 'targets_input'
    context.user_data['total_targets_needed'] = total_targets_needed


async def process_targets_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенных целей"""
    if context.user_data.get('waiting_for') != 'targets_input':
        return

    text = update.message.text
    targets = parse_target_accounts(text)
    total_needed = context.user_data.get('total_targets_needed', 40)

    if len(targets) < total_needed:
        message = (
            f"⚠️ Введено мишеней: {len(targets)}\n"
            f"Необходимо минимум: {total_needed}\n\n"
            "Добавьте еще аккаунтов."
        )
        await update.message.reply_text(message)
        return

    # Распределяем мишени по кольцам
    async with db_manager.get_async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(ShillerRing).where(ShillerRing.is_active == True))
        rings = result.scalars().all()

        target_index = 0
        for ring in rings:
            targets_for_ring = ring.size * ring.targets_per_shiller
            ring_targets = targets[target_index:target_index + targets_for_ring]

            # Добавляем мишени для кольца
            for target in ring_targets:
                target_entry = ShillerTarget(
                    ring_id=ring.id,
                    target_username=target,
                    is_active=True
                )
                session.add(target_entry)

            target_index += targets_for_ring

        await session.commit()

    message = f"✅ Добавлено мишеней: {len(targets)}\n"
    message += f"📍 Распределено по {len(rings)} кольцам"

    context.user_data.clear()

    await update.message.reply_text(
        message,
        reply_markup=get_back_keyboard("shillers")
    )


async def set_token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка токена для шиллинга"""
    query = update.callback_query
    await query.answer()

    # Сохраняем откуда пришли
    context.user_data['previous_menu'] = 'shillers'

    message = (
        "💰 Указание токена для шиллинга\n\n"
        "Отправьте данные в формате:\n"
        "`Название токена`\n"
        "`Адрес токена`\n\n"
        "Пример:\n"
        "```\n"
        "BANDGAZ\n"
        "0x1234567890abcdef1234567890abcdef12345678\n"
        "```"
    )

    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )

    context.user_data['waiting_for'] = 'token_input'


async def process_token_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных токена"""
    if context.user_data.get('waiting_for') != 'token_input':
        return

    lines = update.message.text.strip().split('\n')

    if len(lines) < 2:
        await update.message.reply_text(
            "❌ Введите название и адрес токена на разных строках",
            reply_markup=get_cancel_keyboard()
        )
        return

    token_name = lines[0].strip()
    token_address = lines[1].strip()

    # Валидация адреса
    if not validate_token_address(token_address):
        await update.message.reply_text(
            "❌ Неверный формат адреса токена",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Сохраняем в контексте
    context.user_data['token_name'] = token_name
    context.user_data['token_address'] = token_address
    context.user_data['waiting_for'] = None

    message = (
        f"✅ Токен установлен:\n"
        f"💰 ${token_name}\n"
        f"📍 {token_address}\n\n"
        "Теперь добавьте ссылку на пост для цитирования."
    )

    await update.message.reply_text(
        message,
        reply_markup=get_back_keyboard("shillers")  # Изменено на shillers
    )


async def add_quote_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление ссылки для цитирования"""
    query = update.callback_query
    await query.answer()

    if not context.user_data.get('token_name'):
        await query.edit_message_text(
            "❌ Сначала укажите токен для шиллинга",
            reply_markup=get_back_keyboard("shillers")
        )
        return

    message = (
        "🔗 Добавление ссылки для цитирования\n\n"
        "Отправьте ссылку на пост Twitter, который будут "
        "цитировать шиллеры.\n\n"
        "Это должен быть пост от аккаунта мемкоина."
    )

    await query.edit_message_text(
        message,
        reply_markup=get_cancel_keyboard()
    )

    context.user_data['waiting_for'] = 'quote_link_input'


async def process_quote_link_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ссылки для цитирования"""
    if context.user_data.get('waiting_for') != 'quote_link_input':
        return

    link = update.message.text.strip()

    if not validate_twitter_url(link):
        await update.message.reply_text(
            "❌ Неверная ссылка на Twitter пост",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Создаем кампанию
    token_name = context.user_data.get('token_name')
    token_address = context.user_data.get('token_address')

    if token_name and token_address:
        campaign = await db_manager.create_campaign(
            name=f"Campaign {token_name}",
            token_name=token_name,
            token_address=token_address,
            quote_link=link
        )

        message = (
            f"✅ Кампания создана!\n\n"
            f"💰 Токен: ${token_name}\n"
            f"📍 Адрес: {token_address[:8]}...{token_address[-6:]}\n"
            f"🔗 Пост для цитирования добавлен\n\n"
            "Теперь можно запускать шиллинг!"
        )
    else:
        message = "❌ Ошибка создания кампании"

    context.user_data.clear()

    await update.message.reply_text(
        message,
        reply_markup=get_back_keyboard("shillers")
    )


async def configure_shiller_activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка активности шиллеров"""
    query = update.callback_query
    await query.answer()

    # Получаем текущие настройки
    async with db_manager.get_async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(ShillerRing).limit(1))
        ring = result.scalar()

    if ring:
        targets_per_shiller = ring.targets_per_shiller
        comments_per_round = ring.comments_per_round
    else:
        targets_per_shiller = 10
        comments_per_round = 10

    message = (
        "🔧 Настройка активности шиллеров\n\n"
        f"Текущие настройки:\n"
        f"🎯 Мишеней на шиллера: {targets_per_shiller}\n"
        f"💬 Комментов за круг: {comments_per_round}\n\n"
        "Эти настройки оптимальны для избежания банов.\n"
        "Изменять не рекомендуется."
    )

    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard("shillers")
    )


async def start_shilling_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск шиллинга"""
    query = update.callback_query
    await query.answer()

    global shilling_engine

    # Проверяем готовность
    campaign = await db_manager.get_active_campaign()
    if not campaign:
        await query.edit_message_text(
            "❌ Нет активной кампании. Сначала укажите токен.",
            reply_markup=get_back_keyboard("shillers")
        )
        return

    # Проверяем кольца
    async with db_manager.get_async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(ShillerRing).where(ShillerRing.is_active == True)
        )
        rings = result.scalars().all()

    if not rings:
        await query.edit_message_text(
            "❌ Нет активных колец шиллеров",
            reply_markup=get_back_keyboard("shillers")
        )
        return

    # Проверяем мишени
    has_targets = all(len(ring.targets) > 0 for ring in rings)
    if not has_targets:
        await query.edit_message_text(
            "❌ Не все кольца имеют мишени",
            reply_markup=get_back_keyboard("shillers")
        )
        return

    # Запускаем движок
    if shilling_engine and shilling_engine.is_running:
        await query.edit_message_text(
            "⚠️ Шиллинг уже запущен!",
            reply_markup=get_back_keyboard("shillers")
        )
        return

    shilling_engine = ShillingEngine(campaign)
    await shilling_engine.start()

    message = (
        "🚀 Шиллинг запущен!\n\n"
        f"💰 Токен: ${campaign.token_name}\n"
        f"🔗 Колец активировано: {len(rings)}\n\n"
        "Кольца работают параллельно.\n"
        "Каждое кольцо выполняет:\n"
        "• Комментарии под мишенями\n"
        "• Лайки и ответы друг другу\n"
        "• Цитирование поста токена\n\n"
        "Для остановки используйте соответствующую кнопку."
    )

    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard("shillers")
    )


async def shilling_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика шиллинга"""
    query = update.callback_query
    await query.answer()

    # Получаем статистику
    campaign = await db_manager.get_active_campaign()

    if not campaign:
        await query.edit_message_text(
            "📊 Нет активной кампании",
            reply_markup=get_back_keyboard("shillers")
        )
        return

    async with db_manager.get_async_session() as session:
        from sqlalchemy import select, func
        from database.models import Activity

        # Статистика за сегодня
        today = datetime.now().date()

        result = await session.execute(
            select(
                Activity.action_type,
                func.count(Activity.id)
            )
            .where(
                Activity.campaign_id == campaign.id,
                func.date(Activity.created_at) == today
            )
            .group_by(Activity.action_type)
        )

        stats = dict(result.all())

    message = (
        f"📊 Статистика шиллинга за сегодня\n\n"
        f"💰 Кампания: ${campaign.token_name}\n"
        f"📅 Дата: {today}\n\n"
        f"💬 Комментариев: {stats.get('comment', 0)}\n"
        f"❤️ Лайков: {stats.get('like', 0)}\n"
        f"🔁 Цитат: {stats.get('quote', 0)}\n\n"
    )

    # Статистика по кольцам
    if shilling_engine and shilling_engine.is_running:
        message += "🟢 Движок активен\n"
        message += f"🔄 Обработано раундов: {shilling_engine.rounds_completed}\n"
    else:
        message += "🔴 Движок остановлен\n"

    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard("shillers")
    )


async def stop_shilling_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка шиллинга"""
    query = update.callback_query
    await query.answer()

    global shilling_engine

    if not shilling_engine or not shilling_engine.is_running:
        await query.edit_message_text(
            "⚠️ Шиллинг не запущен",
            reply_markup=get_back_keyboard("shillers")
        )
        return

    await shilling_engine.stop()

    message = "🛑 Шиллинг остановлен!"

    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard("shillers")
    )


async def clear_campaign_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистка данных кампании"""
    query = update.callback_query
    await query.answer()

    # Деактивируем текущую кампанию
    campaign = await db_manager.get_active_campaign()

    if campaign:
        async with db_manager.get_async_session() as session:
            campaign_db = await session.get(Campaign, campaign.id)
            campaign_db.is_active = False
            campaign_db.ended_at = datetime.utcnow()
            await session.commit()

        message = "🧹 Данные кампании очищены!"
    else:
        message = "ℹ️ Нет активной кампании для очистки"

    # Очищаем данные из контекста
    context.user_data.clear()

    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard("shillers")
    )