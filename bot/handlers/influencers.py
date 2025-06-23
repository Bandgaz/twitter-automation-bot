from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger
from datetime import datetime, timedelta
import asyncio

from ..keyboards.main_kb import get_influencers_keyboard, get_back_keyboard, get_cancel_keyboard
from database.db_manager import db_manager
from database.models import Account, InfluencerSource, Activity
from modules.influencers.activity_manager import InfluencerActivityManager
from utils.validators import validate_twitter_url, parse_target_accounts
from utils.twitter_helpers import validate_twitter_username

# Глобальный менеджер активности инфлюенсеров (инициализируется при необходимости)
influencer_manager = None


async def influencers_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню инфлюенсеров"""
    query = update.callback_query
    await query.answer()

    try:
        # Получаем статистику безопасно внутри сессии
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Account).where(Account.account_type == "influencer")
            )
            influencers = result.scalars().all()
            active_count = sum(1 for acc in influencers if acc.status == "active")

        # Проверяем статус менеджера
        manager_status = "🔴 Остановлен"
        if influencer_manager is not None and hasattr(influencer_manager, 'is_running') and influencer_manager.is_running:
            manager_status = "🟢 Работает"

        message = (
            "🧠 Управление инфлюенсерами\n\n"
            f"📊 Статистика:\n"
            f"• Всего инфлюенсеров: {len(influencers)}\n"
            f"• Активных: {active_count}\n"
            f"• Статус менеджера: {manager_status}\n\n"
            "Выберите действие:"
        )

        await query.edit_message_text(
            message,
            reply_markup=get_influencers_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в меню инфлюенсеров: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при загрузке меню инфлюенсеров",
            reply_markup=get_back_keyboard("main_menu")
        )


async def configure_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка генерации контента"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("➕ Добавить первоисточники", callback_data="add_source_accounts")],
        [InlineKeyboardButton("🔗 Присвоить источники", callback_data="assign_source")],
        [InlineKeyboardButton("📈 Настроить NI", callback_data="set_ni")],
        [InlineKeyboardButton("📅 Частота публикаций", callback_data="set_post_frequency")],
        [InlineKeyboardButton("🔙 Назад", callback_data="influencers")]
    ]

    message = (
        "⚙️ Настройка генерации контента\n\n"
        "Здесь вы можете:\n"
        "• Добавить аккаунты-источники контента\n"
        "• Присвоить источники к инфлюенсерам\n"
        "• Настроить важность источников (NI)\n"
        "• Установить частоту публикаций"
    )

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def add_source_accounts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление аккаунтов-источников"""
    query = update.callback_query
    await query.answer()

    # Сохраняем откуда пришли
    context.user_data['previous_menu'] = 'configure_content'

    message = (
        "➕ Добавление аккаунтов-источников\n\n"
        "Отправьте список Twitter аккаунтов, которые будут использоваться "
        "как источники контента для перефразировки.\n\n"
        "По одному аккаунту на строку, можно с @ или без:\n"
        "```\n"
        "@elonmusk\n"
        "VitalikButerin\n"
        "@cz_binance\n"
        "```"
    )

    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )

    context.user_data['waiting_for'] = 'source_accounts_input'


async def process_source_accounts_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенных аккаунтов-источников"""
    if context.user_data.get('waiting_for') != 'source_accounts_input':
        return

    text = update.message.text
    accounts = parse_target_accounts(text)

    if accounts:
        # Сохраняем в контексте для дальнейшего использования
        context.user_data['source_accounts'] = accounts
        message = f"✅ Добавлено источников: {len(accounts)}\n\n"
        message += "Теперь нужно присвоить эти источники к инфлюенсерам."
    else:
        message = "❌ Не найдено валидных аккаунтов"

    context.user_data['waiting_for'] = None

    await update.message.reply_text(
        message,
        reply_markup=get_back_keyboard("configure_content")
    )


async def assign_source_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Присвоение источников к инфлюенсерам"""
    query = update.callback_query
    await query.answer()

    # Если это выбор конкретного инфлюенсера
    if query.data.startswith("assign_source_"):
        influencer_id = int(query.data.split("_")[2])
        context.user_data['selected_influencer'] = influencer_id

        # Показываем доступные источники
        source_accounts = context.user_data.get('source_accounts', [])
        if not source_accounts:
            await query.edit_message_text(
                "❌ Сначала добавьте аккаунты-источники",
                reply_markup=get_back_keyboard("configure_content")
            )
            return

        keyboard = []
        for source in source_accounts[:20]:
            keyboard.append([
                InlineKeyboardButton(
                    f"@{source}",
                    callback_data=f"select_source_{source}"
                )
            ])

        keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="configure_content")])

        message = "🔗 Выберите источники для инфлюенсера (можно несколько):"

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Если это выбор источника
    if query.data.startswith("select_source_"):
        source = query.data.split("select_source_")[1]
        influencer_id = context.user_data.get('selected_influencer')

        if influencer_id:
            # Добавляем источник к инфлюенсеру
            async with db_manager.get_async_session() as session:
                source_entry = InfluencerSource(
                    influencer_id=influencer_id,
                    source_username=source,
                    importance_score=1.0
                )
                session.add(source_entry)
                await session.commit()

            await query.answer(f"✅ Источник @{source} добавлен")
        return

    # Показываем список инфлюенсеров для выбора
    influencers = await db_manager.get_accounts_by_type("influencer")

    if not influencers:
        await query.edit_message_text(
            "❌ Нет инфлюенсеров для присвоения источников",
            reply_markup=get_back_keyboard("configure_content")
        )
        return

    keyboard = []
    for inf in influencers[:20]:
        # Получаем количество источников
        source_count = len(inf.influencer_sources) if inf.influencer_sources else 0
        keyboard.append([
            InlineKeyboardButton(
                f"@{inf.username} (источников: {source_count})",
                callback_data=f"assign_source_{inf.id}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="configure_content")])

    message = "🔗 Выберите инфлюенсера для присвоения источников:"

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def set_ni_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка NI (важности) источников"""
    query = update.callback_query
    await query.answer()

    message = (
        "📈 Настройка NI (важности) источников\n\n"
        "NI определяет приоритет источника при выборе контента.\n"
        "Чем выше значение, тем чаще будет использоваться источник.\n\n"
        "Значение от 0.1 до 5.0\n"
        "По умолчанию: 1.0\n\n"
        "Эта функция будет доступна в следующей версии."
    )

    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard("configure_content")
    )


async def set_post_frequency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка частоты публикаций"""
    query = update.callback_query
    await query.answer()

    # Сохраняем откуда пришли
    context.user_data['previous_menu'] = 'configure_content'

    message = (
        "📅 Частота суточных публикаций\n\n"
        "Укажите количество постов в сутки для каждого инфлюенсера.\n"
        "Рекомендуется: 1-3 поста в сутки.\n\n"
        "Отправьте число:"
    )

    await query.edit_message_text(
        message,
        reply_markup=get_cancel_keyboard()
    )

    context.user_data['waiting_for'] = 'post_frequency_input'


async def process_post_frequency_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка частоты публикаций"""
    if context.user_data.get('waiting_for') != 'post_frequency_input':
        return

    try:
        frequency = int(update.message.text.strip())
        if 1 <= frequency <= 10:
            # Обновляем всех инфлюенсеров
            async with db_manager.get_async_session() as session:
                from sqlalchemy import update
                await session.execute(
                    update(Account)
                    .where(Account.account_type == "influencer")
                    .values(posts_per_day=frequency)
                )
                await session.commit()

            message = f"✅ Установлена частота: {frequency} постов в сутки"
        else:
            message = "❌ Частота должна быть от 1 до 10"
    except ValueError:
        message = "❌ Введите число"

    context.user_data['waiting_for'] = None

    await update.message.reply_text(
        message,
        reply_markup=get_back_keyboard("configure_content")
    )


async def configure_activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка активности инфлюенсеров"""
    query = update.callback_query
    await query.answer()

    # Получаем текущие настройки
    influencers = await db_manager.get_accounts_by_type("influencer")
    if influencers:
        avg_comments = sum(acc.comments_per_day for acc in influencers) / len(influencers)
        avg_likes = sum(acc.likes_per_day for acc in influencers) / len(influencers)
    else:
        avg_comments = 20
        avg_likes = 50

    message = (
        "🔧 Настройка активности инфлюенсеров\n\n"
        f"Текущие настройки (среднее):\n"
        f"💬 Комментариев в сутки: {avg_comments:.0f}\n"
        f"❤️ Лайков в сутки: {avg_likes:.0f}\n\n"
        "Для изменения настроек используйте команды:\n"
        "/set_comments <число> - комментарии в сутки\n"
        "/set_likes <число> - лайки в сутки\n"
        "/set_sleep <часы_работы> <часы_сна> - режим сна"
    )

    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard("influencers")
    )


async def start_influencer_activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск активности инфлюенсеров"""
    query = update.callback_query
    await query.answer()

    global influencer_manager

    try:
        # Проверяем, не запущен ли уже
        if influencer_manager is not None and hasattr(influencer_manager,
                                                      'is_running') and influencer_manager.is_running:
            await query.edit_message_text(
                "⚠️ Менеджер инфлюенсеров уже запущен!",
                reply_markup=get_back_keyboard("influencers")
            )
            return

        # Проверяем наличие инфлюенсеров
        influencers = await db_manager.get_accounts_by_type("influencer")
        if not influencers:
            await query.edit_message_text(
                "❌ Нет инфлюенсеров для запуска",
                reply_markup=get_back_keyboard("influencers")
            )
            return

        # Проверяем наличие источников
        has_sources = False
        for inf in influencers:
            if inf.influencer_sources:
                has_sources = True
                break

        if not has_sources:
            await query.edit_message_text(
                "❌ Ни у одного инфлюенсера нет источников контента",
                reply_markup=get_back_keyboard("influencers")
            )
            return

        # Создаем и запускаем менеджер
        from modules.influencers.activity_manager import InfluencerActivityManager
        influencer_manager = InfluencerActivityManager()
        await influencer_manager.start()

        message = (
            "🚀 Активность инфлюенсеров запущена!\n\n"
            "Бот начал работу в автономном режиме 24/7.\n"
            "Каждый инфлюенсер будет:\n"
            "• Публиковать посты на основе источников\n"
            "• Комментировать под крупными аккаунтами\n"
            "• Ставить лайки\n"
            "• Делать перекрестные цитаты\n\n"
            "Для остановки вернитесь в меню инфлюенсеров."
        )

        await query.edit_message_text(
            message,
            reply_markup=get_back_keyboard("influencers")
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске активности инфлюенсеров: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при запуске активности",
            reply_markup=get_back_keyboard("influencers")
        )


async def quote_mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Режим цитирования"""
    query = update.callback_query
    await query.answer()

    # Если это выбор действия
    if query.data == "set_memecoin_account":
        message = (
            "👤 Укажите аккаунт создателя мемкоина\n\n"
            "Отправьте username аккаунта (с @ или без):"
        )
        context.user_data['waiting_for'] = 'memecoin_account_input'
        await query.edit_message_text(
            message,
            reply_markup=get_cancel_keyboard()
        )
        return

    elif query.data == "set_quote_post":
        if not context.user_data.get('memecoin_account'):
            await query.answer("❌ Сначала укажите аккаунт мемкоина", show_alert=True)
            return

        message = (
            "🔗 Добавление ссылки для цитирования\n\n"
            "Отправьте ссылку на пост Twitter:"
        )
        context.user_data['waiting_for'] = 'quote_post_input'
        await query.edit_message_text(
            message,
            reply_markup=get_cancel_keyboard()
        )
        return

    elif query.data == "start_mass_quote":
        memecoin_account = context.user_data.get('memecoin_account')
        quote_post = context.user_data.get('quote_post')

        if not memecoin_account:
            await query.answer("❌ Не указан аккаунт мемкоина", show_alert=True)
            return

        if not quote_post:
            await query.answer("❌ Не указана ссылка на пост", show_alert=True)
            return

        # Запускаем массовое цитирование
        await query.edit_message_text(
            f"🚀 Запуск массового цитирования!\n\n"
            f"👤 Аккаунт: @{memecoin_account}\n"
            f"🔗 Пост: {quote_post}\n\n"
            f"Все инфлюенсеры начнут цитировать этот пост.",
            reply_markup=get_back_keyboard("influencers")
        )

        # TODO: Реализовать запуск через менеджер
        return

    # Основное меню режима цитирования
    keyboard = []

    memecoin_account = context.user_data.get('memecoin_account')
    quote_post = context.user_data.get('quote_post')

    # Кнопка аккаунта
    account_text = f"✅ Аккаунт: @{memecoin_account}" if memecoin_account else "❌ Указать аккаунт мемкоина"
    keyboard.append([InlineKeyboardButton(account_text, callback_data="set_memecoin_account")])

    # Кнопка ссылки
    post_text = "✅ Ссылка добавлена" if quote_post else "❌ Добавить ссылку на пост"
    keyboard.append([InlineKeyboardButton(post_text, callback_data="set_quote_post")])

    # Кнопка запуска
    keyboard.append([InlineKeyboardButton("🚀 Запустить массовое цитирование", callback_data="start_mass_quote")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="influencers")])

    message = (
        "🗣 Режим цитирования\n\n"
        "Эта функция позволяет всем инфлюенсерам "
        "процитировать пост создателя мемкоина.\n\n"
        "Шаги:\n"
        "1️⃣ Укажите аккаунт создателя\n"
        "2️⃣ Добавьте ссылку на пост\n"
        "3️⃣ Запустите цитирование\n\n"
    )

    if memecoin_account:
        message += f"👤 Аккаунт: @{memecoin_account}\n"
    if quote_post:
        message += f"🔗 Пост: готов к цитированию\n"

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def process_memecoin_account_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода аккаунта мемкоина"""
    if context.user_data.get('waiting_for') != 'memecoin_account_input':
        return

    account = update.message.text.strip().replace('@', '')

    if validate_twitter_username(account):
        context.user_data['memecoin_account'] = account
        message = f"✅ Аккаунт мемкоина установлен: @{account}"
    else:
        message = "❌ Неверный формат username"

    context.user_data['waiting_for'] = None

    # Возвращаемся в меню режима цитирования
    await update.message.reply_text(message)
    await asyncio.sleep(1)

    # Показываем меню режима цитирования
    query_update = Update(update.update_id, callback_query=update.callback_query)
    query_update.callback_query.data = "quote_mode"
    await quote_mode_handler(query_update, context)


async def process_quote_post_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода ссылки на пост"""
    if context.user_data.get('waiting_for') != 'quote_post_input':
        return

    link = update.message.text.strip()

    if validate_twitter_url(link):
        context.user_data['quote_post'] = link
        message = "✅ Ссылка на пост добавлена"
    else:
        message = "❌ Неверная ссылка на Twitter пост"

    context.user_data['waiting_for'] = None

    # Возвращаемся в меню режима цитирования
    await update.message.reply_text(message)
    await asyncio.sleep(1)

    # Показываем меню режима цитирования
    query_update = Update(update.update_id, callback_query=update.callback_query)
    query_update.callback_query.data = "quote_mode"
    await quote_mode_handler(query_update, context)


async def influencer_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика по инфлюенсерам"""
    query = update.callback_query
    await query.answer()

    # Получаем инфлюенсеров
    influencers = await db_manager.get_accounts_by_type("influencer")

    if not influencers:
        await query.edit_message_text(
            "📊 Нет инфлюенсеров для отображения статистики",
            reply_markup=get_back_keyboard("influencers")
        )
        return

    # Получаем статистику за сегодня
    today = datetime.now().date()

    async with db_manager.get_async_session() as session:
        from sqlalchemy import select, func, and_

        stats_message = "📊 Статистика инфлюенсеров за сегодня:\n\n"

        for inf in influencers[:10]:  # Показываем первых 10
            # Считаем активности за сегодня
            result = await session.execute(
                select(
                    Activity.action_type,
                    func.count(Activity.id)
                )
                .where(
                    and_(
                        Activity.account_id == inf.id,
                        func.date(Activity.created_at) == today
                    )
                )
                .group_by(Activity.action_type)
            )

            activities = dict(result.all())

            posts = activities.get('tweet', 0)
            comments = activities.get('comment', 0)
            likes = activities.get('like', 0)
            quotes = activities.get('quote', 0)

            stats_message += (
                f"@{inf.username}:\n"
                f"📝 Постов: {posts}\n"
                f"💬 Комментариев: {comments}\n"
                f"❤️ Лайков: {likes}\n"
                f"🔁 Цитат: {quotes}\n"
                f"👥 Подписчиков: {inf.followers_count}\n\n"
            )

        if len(influencers) > 10:
            stats_message += f"... и еще {len(influencers) - 10} инфлюенсеров"

    await query.edit_message_text(
        stats_message,
        reply_markup=get_back_keyboard("influencers")
    )