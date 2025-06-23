from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("👥 Аккаунты и Прокси", callback_data="accounts_proxy")],
        [InlineKeyboardButton("🧠 Инфлюенсеры", callback_data="influencers")],
        [InlineKeyboardButton("📣 Шиллеры", callback_data="shillers")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_accounts_proxy_keyboard():
    """Меню аккаунтов и прокси"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить аккаунты Инфлюенсеры", callback_data="add_influencer_accounts")],
        [InlineKeyboardButton("➕ Добавить аккаунты Шиллеры", callback_data="add_shiller_accounts")],
        [InlineKeyboardButton("➕ Сформировать кольца", callback_data="form_rings")],
        [InlineKeyboardButton("📋 Список аккаунтов", callback_data="list_accounts")],
        [InlineKeyboardButton("🛠 Добавить прокси", callback_data="add_proxy")],
        [InlineKeyboardButton("📃 Список прокси", callback_data="list_proxy")],
        [InlineKeyboardButton("📌 Закрепить прокси", callback_data="bind_proxy")],
        [InlineKeyboardButton("#️⃣ Загрузить хэштеги", callback_data="add_hashtags")],
        [InlineKeyboardButton("📑 Список хэштегов", callback_data="list_hashtags")],
        [InlineKeyboardButton("❌ Удалить аккаунт", callback_data="delete_account")],
        [InlineKeyboardButton("❌ Удалить прокси", callback_data="delete_proxy")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_influencers_keyboard():
    """Меню инфлюенсеров"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Настроить генерацию контента", callback_data="configure_content")],
        [InlineKeyboardButton("➕ Добавить аккаунты первоисточники", callback_data="add_source_accounts")],
        [InlineKeyboardButton("🔗 Присвоить первоисточник к инфлу", callback_data="assign_source")],
        [InlineKeyboardButton("📈 NI первоисточника", callback_data="set_ni")],
        [InlineKeyboardButton("📅 Частота суточных публикаций", callback_data="set_post_frequency")],
        [InlineKeyboardButton("🔧 Настроить активность", callback_data="configure_activity")],
        [InlineKeyboardButton("🚀 Запуск активности инфлюенсеров", callback_data="start_influencer_activity")],
        [InlineKeyboardButton("🗣 Режим цитирования", callback_data="quote_mode")],
        [InlineKeyboardButton("📊 Статистика по инфлюенсерам", callback_data="influencer_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_shillers_keyboard():
    """Меню шиллеров"""
    keyboard = [
        [InlineKeyboardButton("🎯 Настроить мишени шилинга", callback_data="configure_targets")],
        [InlineKeyboardButton("💰 Указать токен для шилинга", callback_data="set_token")],
        [InlineKeyboardButton("🔗 Добавить ссылку для цитаты", callback_data="add_quote_link")],
        [InlineKeyboardButton("🔧 Настроить активность шиллов", callback_data="configure_shiller_activity")],
        [InlineKeyboardButton("🚀 Запуск активности шиллеров", callback_data="start_shilling")],
        [InlineKeyboardButton("📊 Статистика шилинга", callback_data="shilling_stats")],
        [InlineKeyboardButton("🛑 Остановить шиллинг", callback_data="stop_shilling")],
        [InlineKeyboardButton("🧹 Очистить данные текущей кампании", callback_data="clear_campaign")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(callback_data: str = "main_menu"):
    """Клавиатура с кнопкой назад"""
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard():
    """Клавиатура подтверждения"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Нет", callback_data="confirm_no")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard():
    """Клавиатура отмены"""
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)