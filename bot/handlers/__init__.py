from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from .main_menu import start_handler, main_menu_handler
from .accounts_proxy import (
    accounts_proxy_menu_handler,
    add_influencer_accounts_handler,
    add_shiller_accounts_handler,
    list_accounts_handler,
    add_proxy_handler,
    list_proxy_handler,
    bind_proxy_handler,
    add_hashtags_handler,
    list_hashtags_handler,
    delete_account_handler,
    delete_proxy_handler,
    form_rings_handler,
    set_ring_size_handler,
    cancel_handler,
    process_accounts_input,
    process_proxy_input,
    process_hashtags_input
)
from .influencers import (
    influencers_menu_handler,
    configure_content_handler,
    add_source_accounts_handler,
    assign_source_handler,
    set_ni_handler,
    set_post_frequency_handler,
    configure_activity_handler,
    start_influencer_activity_handler,
    quote_mode_handler,
    influencer_stats_handler
)
from .shillers import (
    shillers_menu_handler,
    configure_targets_handler,
    set_token_handler,
    add_quote_link_handler,
    configure_shiller_activity_handler,
    start_shilling_handler,
    shilling_stats_handler,
    stop_shilling_handler,
    clear_campaign_handler
)

from config import ALLOWED_USERS


def setup_handlers(application: Application):
    """Настройка всех обработчиков бота"""

    # Фильтр для разрешенных пользователей
    user_filter = filters.User(ALLOWED_USERS) if ALLOWED_USERS else None

    # === Основные команды ===
    application.add_handler(CommandHandler("start", start_handler, filters=user_filter))

    # === Обработчики callback запросов ===

    # Главное меню
    application.add_handler(CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"))

    # Обработчик отмены
    application.add_handler(CallbackQueryHandler(cancel_handler, pattern="^cancel$"))

    # Меню аккаунтов и прокси
    application.add_handler(CallbackQueryHandler(accounts_proxy_menu_handler, pattern="^accounts_proxy$"))
    application.add_handler(CallbackQueryHandler(add_influencer_accounts_handler, pattern="^add_influencer_accounts$"))
    application.add_handler(CallbackQueryHandler(add_shiller_accounts_handler, pattern="^add_shiller_accounts$"))
    application.add_handler(CallbackQueryHandler(list_accounts_handler, pattern="^list_accounts$"))
    application.add_handler(CallbackQueryHandler(add_proxy_handler, pattern="^add_proxy$"))
    application.add_handler(CallbackQueryHandler(list_proxy_handler, pattern="^list_proxy$"))
    application.add_handler(CallbackQueryHandler(bind_proxy_handler, pattern="^bind_proxy$"))
    application.add_handler(CallbackQueryHandler(add_hashtags_handler, pattern="^add_hashtags$"))
    application.add_handler(CallbackQueryHandler(list_hashtags_handler, pattern="^list_hashtags$"))
    application.add_handler(CallbackQueryHandler(delete_account_handler, pattern="^delete_account$"))
    application.add_handler(CallbackQueryHandler(delete_proxy_handler, pattern="^delete_proxy$"))

    # Формирование колец
    application.add_handler(CallbackQueryHandler(form_rings_handler, pattern="^form_rings$"))
    application.add_handler(CallbackQueryHandler(set_ring_size_handler, pattern="^set_ring_size$"))

    # Меню инфлюенсеров
    application.add_handler(CallbackQueryHandler(influencers_menu_handler, pattern="^influencers$"))
    application.add_handler(CallbackQueryHandler(configure_content_handler, pattern="^configure_content$"))
    application.add_handler(CallbackQueryHandler(add_source_accounts_handler, pattern="^add_source_accounts$"))
    application.add_handler(CallbackQueryHandler(assign_source_handler, pattern="^assign_source$"))
    application.add_handler(CallbackQueryHandler(set_ni_handler, pattern="^set_ni$"))
    application.add_handler(CallbackQueryHandler(set_post_frequency_handler, pattern="^set_post_frequency$"))
    application.add_handler(CallbackQueryHandler(configure_activity_handler, pattern="^configure_activity$"))
    application.add_handler(
        CallbackQueryHandler(start_influencer_activity_handler, pattern="^start_influencer_activity$"))
    application.add_handler(CallbackQueryHandler(quote_mode_handler, pattern="^quote_mode$"))
    # Обработчики для режима цитирования инфлюенсеров
    application.add_handler(CallbackQueryHandler(quote_mode_handler, pattern="^set_memecoin_account$"))
    application.add_handler(CallbackQueryHandler(quote_mode_handler, pattern="^set_quote_post$"))
    application.add_handler(CallbackQueryHandler(quote_mode_handler, pattern="^start_mass_quote$"))

    # Меню шиллеров
    application.add_handler(CallbackQueryHandler(shillers_menu_handler, pattern="^shillers$"))
    application.add_handler(CallbackQueryHandler(configure_targets_handler, pattern="^configure_targets$"))
    application.add_handler(CallbackQueryHandler(set_token_handler, pattern="^set_token$"))
    application.add_handler(CallbackQueryHandler(add_quote_link_handler, pattern="^add_quote_link$"))
    application.add_handler(
        CallbackQueryHandler(configure_shiller_activity_handler, pattern="^configure_shiller_activity$"))
    application.add_handler(CallbackQueryHandler(start_shilling_handler, pattern="^start_shilling$"))
    application.add_handler(CallbackQueryHandler(shilling_stats_handler, pattern="^shilling_stats$"))
    application.add_handler(CallbackQueryHandler(stop_shilling_handler, pattern="^stop_shilling$"))
    application.add_handler(CallbackQueryHandler(clear_campaign_handler, pattern="^clear_campaign$"))

    # === Обработчики для конкретных действий с параметрами ===

    # Привязка прокси к аккаунту
    application.add_handler(CallbackQueryHandler(bind_proxy_handler, pattern="^bind_proxy_"))

    # Выбор аккаунта для присвоения источника
    application.add_handler(CallbackQueryHandler(assign_source_handler, pattern="^assign_source_"))

    # Удаление аккаунта/прокси
    application.add_handler(CallbackQueryHandler(delete_account_handler, pattern="^del_acc_"))
    application.add_handler(CallbackQueryHandler(delete_proxy_handler, pattern="^del_proxy_"))

    # === Обработчики текстовых сообщений для ввода данных ===

    # Обработчики для ввода данных
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, process_text_input))


async def process_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общий обработчик текстовых сообщений"""
    waiting_for = context.user_data.get('waiting_for')

    if waiting_for == 'accounts_input':
        await process_accounts_input(update, context)
    elif waiting_for == 'proxy_input':
        await process_proxy_input(update, context)
    elif waiting_for == 'hashtags_input':
        await process_hashtags_input(update, context)
    elif waiting_for == 'source_accounts_input':
        from .influencers import process_source_accounts_input
        await process_source_accounts_input(update, context)
    elif waiting_for == 'post_frequency_input':
        from .influencers import process_post_frequency_input
        await process_post_frequency_input(update, context)
    elif waiting_for == 'memecoin_account_input':
        from .influencers import process_memecoin_account_input
        await process_memecoin_account_input(update, context)
    elif waiting_for == 'quote_post_input':
        from .influencers import process_quote_post_input
        await process_quote_post_input(update, context)
    elif waiting_for == 'ring_size_input':
        await set_ring_size_handler(update, context)
    elif waiting_for == 'targets_input':
        from .shillers import process_targets_input
        await process_targets_input(update, context)
    elif waiting_for == 'token_input':
        from .shillers import process_token_input
        await process_token_input(update, context)
    elif waiting_for == 'quote_link_input':
        from .shillers import process_quote_link_input
        await process_quote_link_input(update, context)