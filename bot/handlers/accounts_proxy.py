from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from loguru import logger
import asyncio
from typing import List

from ..keyboards.main_kb import get_accounts_proxy_keyboard, get_back_keyboard, get_cancel_keyboard
from database.db_manager import db_manager
from database.models import Account, Proxy, ShillerRing, Hashtag
from utils.validators import validate_proxy_format, validate_account_format

# Состояния для ConversationHandler
ACCOUNTS_INPUT = 1
PROXY_INPUT = 2
HASHTAGS_INPUT = 3
RING_SIZE_INPUT = 4
TARGETS_INPUT = 5


async def accounts_proxy_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню аккаунтов и прокси"""
    query = update.callback_query
    await query.answer()

    message = (
        "👥 Управление аккаунтами и прокси\n\n"
        "Здесь вы можете:\n"
        "• Добавить аккаунты инфлюенсеров и шиллеров\n"
        "• Настроить прокси для аккаунтов\n"
        "• Управлять хэштегами\n"
        "• Формировать кольца шиллеров\n\n"
        "Выберите действие:"
    )

    await query.edit_message_text(
        message,
        reply_markup=get_accounts_proxy_keyboard()
    )


async def add_influencer_accounts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление аккаунтов инфлюенсеров"""
    query = update.callback_query
    await query.answer()

    # Сохраняем откуда пришли
    context.user_data['previous_menu'] = 'accounts_proxy'

    message = (
        "➕ Добавление аккаунтов инфлюенсеров\n\n"
        "Отправьте список аккаунтов в формате:\n"
        "`username:password:email:email_password`\n\n"
        "По одному аккаунту на строку.\n"
        "Email и пароль от email опциональны.\n\n"
        "Пример:\n"
        "`john_doe:Pass123:john@mail.com:EmailPass123`\n"
        "`jane_smith:Pass456`"
    )

    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )

    # Сохраняем тип аккаунтов в контексте
    context.user_data['account_type'] = 'influencer'
    context.user_data['waiting_for'] = 'accounts_input'


async def add_shiller_accounts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление аккаунтов шиллеров"""
    query = update.callback_query
    await query.answer()

    # Сохраняем откуда пришли
    context.user_data['previous_menu'] = 'accounts_proxy'

    message = (
        "➕ Добавление аккаунтов шиллеров\n\n"
        "Отправьте список аккаунтов в формате:\n"
        "`username:password:email:email_password`\n\n"
        "По одному аккаунту на строку.\n"
        "Email и пароль от email опциональны.\n\n"
        "Пример:\n"
        "`shill_bot1:Pass123`\n"
        "`shill_bot2:Pass456`"
    )

    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )

    # Сохраняем тип аккаунтов в контексте
    context.user_data['account_type'] = 'shiller'
    context.user_data['waiting_for'] = 'accounts_input'


async def process_accounts_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенных аккаунтов"""
    if context.user_data.get('waiting_for') != 'accounts_input':
        return

    text = update.message.text
    account_type = context.user_data.get('account_type', 'influencer')

    # Парсим аккаунты
    lines = text.strip().split('\n')
    added_count = 0
    errors = []

    for line in lines:
        try:
            parts = line.strip().split(':')
            if len(parts) < 2:
                errors.append(f"Неверный формат: {line}")
                continue

            username = parts[0].strip()
            password = parts[1].strip()
            email = parts[2].strip() if len(parts) > 2 else None
            email_password = parts[3].strip() if len(parts) > 3 else None

            # Проверяем существует ли уже такой аккаунт
            async with db_manager.get_async_session() as session:
                from sqlalchemy import select
                existing = await session.execute(
                    select(Account).where(Account.username == username)
                )
                if existing.scalar():
                    errors.append(f"Аккаунт @{username} уже существует")
                    continue

            # Добавляем аккаунт в БД
            account = await db_manager.add_account(
                username=username,
                password=password,
                account_type=account_type,
                email=email,
                email_password=email_password
            )
            added_count += 1
            logger.info(f"Добавлен аккаунт: @{username} ({account_type})")

        except Exception as e:
            logger.error(f"Ошибка добавления аккаунта {line}: {e}")
            errors.append(f"Ошибка с {parts[0] if parts else line}: {str(e)}")

    # Формируем ответ
    response = f"✅ Добавлено аккаунтов: {added_count}\n"
    if errors:
        response += f"\n❌ Ошибки:\n" + "\n".join(errors[:5])
        if len(errors) > 5:
            response += f"\n... и еще {len(errors) - 5} ошибок"

    # Очищаем контекст
    context.user_data.clear()

    await update.message.reply_text(
        response,
        reply_markup=get_back_keyboard("accounts_proxy")
    )


async def list_accounts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список аккаунтов"""
    query = update.callback_query
    await query.answer()

    try:
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select
            from database.models import Account

            result = await session.execute(select(Account))
            accounts = result.scalars().all()

            account_lines = []
            for acc in accounts[:20]:
                account_lines.append(
                    f"@{acc.username} — {acc.status or 'неизвестно'}"
                )

        message = (
            "👥 Список аккаунтов\n\n" +
            "\n".join(account_lines) +
            f"\n\nВсего: {len(accounts)}"
        )

        await query.edit_message_text(
            message,
            reply_markup=get_back_keyboard("accounts_proxy")
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка аккаунтов: {e}")
        await query.edit_message_text(
            "❌ Не удалось загрузить список аккаунтов",
            reply_markup=get_back_keyboard("accounts_proxy")
        )


async def add_proxy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление прокси"""
    query = update.callback_query
    await query.answer()

    # Сохраняем откуда пришли
    context.user_data['previous_menu'] = 'accounts_proxy'

    message = (
        "🛠 Добавление прокси\n\n"
        "Отправьте список прокси в формате:\n"
        "`protocol://username:password@host:port`\n"
        "или\n"
        "`host:port:username:password`\n\n"
        "Поддерживаемые протоколы: http, socks5\n\n"
        "Примеры:\n"
        "`http://user123:pass123@1.2.3.4:8080`\n"
        "`1.2.3.4:8080:user123:pass123`"
    )

    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )

    context.user_data['waiting_for'] = 'proxy_input'


async def process_proxy_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенных прокси"""
    if context.user_data.get('waiting_for') != 'proxy_input':
        return

    text = update.message.text
    lines = text.strip().split('\n')
    added_count = 0
    errors = []

    for line in lines:
        try:
            # Парсим прокси
            proxy_data = validate_proxy_format(line.strip())
            if proxy_data:
                # Проверяем существует ли уже такая прокси
                async with db_manager.get_async_session() as session:
                    from sqlalchemy import select
                    existing = await session.execute(
                        select(Proxy).where(
                            (Proxy.host == proxy_data['host']) &
                            (Proxy.port == proxy_data['port'])
                        )
                    )
                    if existing.scalar():
                        errors.append(f"Прокси {proxy_data['host']}:{proxy_data['port']} уже существует")
                        continue

                proxy = await db_manager.add_proxy(
                    host=proxy_data['host'],
                    port=proxy_data['port'],
                    username=proxy_data.get('username'),
                    password=proxy_data.get('password'),
                    protocol=proxy_data.get('protocol', 'http')
                )
                added_count += 1
                logger.info(f"Добавлена прокси: {proxy_data['host']}:{proxy_data['port']}")
            else:
                errors.append(f"Неверный формат: {line}")

        except Exception as e:
            logger.error(f"Ошибка добавления прокси {line}: {e}")
            errors.append(f"Ошибка с {line}: {str(e)}")

    # Формируем ответ
    response = f"✅ Добавлено прокси: {added_count}\n"
    if errors:
        response += f"\n❌ Ошибки:\n" + "\n".join(errors[:5])

    context.user_data.clear()

    await update.message.reply_text(
        response,
        reply_markup=get_back_keyboard("accounts_proxy")
    )


async def list_proxy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список прокси"""
    query = update.callback_query
    await query.answer()

    try:
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select
            from database.models import Proxy

            result = await session.execute(select(Proxy))
            proxies = result.scalars().all()

            proxy_lines = []
            for proxy in proxies[:20]:
                proxy_lines.append(
                    f"{proxy.host}:{proxy.port} — {proxy.protocol or 'http'}"
                )

        message = (
            "🧩 Список прокси\n\n" +
            "\n".join(proxy_lines) +
            f"\n\nВсего: {len(proxies)}"
        )

        await query.edit_message_text(
            message,
            reply_markup=get_back_keyboard("accounts_proxy")
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка прокси: {e}")
        await query.edit_message_text(
            "❌ Не удалось загрузить список прокси",
            reply_markup=get_back_keyboard("accounts_proxy")
        )


async def bind_proxy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Привязка прокси к аккаунту"""
    query = update.callback_query
    await query.answer()

    # Если это выбор конкретной прокси для аккаунта
    if query.data.startswith("bind_proxy_"):
        parts = query.data.split("_")
        if len(parts) == 4 and parts[2] == "to":
            # bind_proxy_ACCOUNT_ID_to_PROXY_ID
            account_id = int(parts[1])
            proxy_id = int(parts[3])

            await db_manager.update_account_proxy(account_id, proxy_id)

            await query.edit_message_text(
                "✅ Прокси успешно привязана к аккаунту!",
                reply_markup=get_back_keyboard("accounts_proxy")
            )
            return
        elif len(parts) == 3:
            # bind_proxy_ACCOUNT_ID - показываем список прокси
            account_id = int(parts[2])

            # Получаем свободные прокси
            async with db_manager.get_async_session() as session:
                from sqlalchemy import select
                result = await session.execute(select(Proxy).where(Proxy.is_active == True))
                proxies = result.scalars().all()

            if not proxies:
                await query.edit_message_text(
                    "❌ Нет доступных прокси. Сначала добавьте прокси.",
                    reply_markup=get_back_keyboard("accounts_proxy")
                )
                return

            keyboard = []
            for proxy in proxies[:20]:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{proxy.host}:{proxy.port}",
                        callback_data=f"bind_proxy_{account_id}_to_{proxy.id}"
                    )
                ])

            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="bind_proxy")])

            await query.edit_message_text(
                "🌐 Выберите прокси для привязки:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

    # Получаем аккаунты без прокси
    async with db_manager.get_async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Account).where(Account.proxy_id == None)
        )
        accounts_without_proxy = result.scalars().all()

    if not accounts_without_proxy:
        # Проверяем есть ли вообще аккаунты
        all_accounts = await db_manager.get_accounts_by_type("influencer")
        all_accounts.extend(await db_manager.get_accounts_by_type("shiller"))

        if not all_accounts:
            await query.edit_message_text(
                "❌ Нет аккаунтов. Сначала добавьте аккаунты.",
                reply_markup=get_back_keyboard("accounts_proxy")
            )
        else:
            await query.edit_message_text(
                "✅ Все аккаунты уже имеют прокси!",
                reply_markup=get_back_keyboard("accounts_proxy")
            )
        return

    # Создаем клавиатуру с аккаунтами
    keyboard = []
    for acc in accounts_without_proxy[:20]:  # Показываем первые 20
        emoji = "🧠" if acc.account_type == "influencer" else "📣"
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} @{acc.username}",
                callback_data=f"bind_proxy_{acc.id}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="accounts_proxy")])

    message = (
        "📌 Выберите аккаунт для привязки прокси:\n\n"
        "🧠 - Инфлюенсер\n"
        "📣 - Шиллер"
    )

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def add_hashtags_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление хэштегов"""
    query = update.callback_query
    await query.answer()

    # Сохраняем откуда пришли
    context.user_data['previous_menu'] = 'accounts_proxy'

    message = (
        "#️⃣ Добавление хэштегов\n\n"
        "Отправьте хэштеги, каждый с новой строки.\n"
        "Можно с # или без.\n\n"
        "Пример:\n"
        "#crypto\n"
        "#memecoin\n"
        "DeFi\n"
        "Web3"
    )

    await query.edit_message_text(
        message,
        reply_markup=get_cancel_keyboard()
    )

    context.user_data['waiting_for'] = 'hashtags_input'


async def process_hashtags_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенных хэштегов"""
    if context.user_data.get('waiting_for') != 'hashtags_input':
        return

    text = update.message.text
    lines = text.strip().split('\n')
    hashtags = []

    for line in lines:
        tag = line.strip()
        if tag:
            # Добавляем # если его нет
            if not tag.startswith('#'):
                tag = '#' + tag
            hashtags.append(tag)

    if hashtags:
        await db_manager.add_hashtags(hashtags)
        logger.info(f"Добавлено хэштегов: {len(hashtags)}")
        message = f"✅ Добавлено хэштегов: {len(hashtags)}"
    else:
        message = "❌ Не найдено хэштегов для добавления"

    context.user_data.clear()

    await update.message.reply_text(
        message,
        reply_markup=get_back_keyboard("accounts_proxy")
    )


async def list_hashtags_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список хэштегов"""
    query = update.callback_query
    await query.answer()

    try:
        # Получаем хэштеги из БД
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(Hashtag))
            hashtags = result.scalars().all()

        if not hashtags:
            message = "📑 Список хэштегов пуст"
        else:
            message = f"📑 Список хэштегов ({len(hashtags)} шт.):\n\n"
            # Группируем по категориям
            by_category = {}
            for tag in hashtags:
                category = tag.category or "general"
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(tag.tag)

            for category, tags in by_category.items():
                message += f"\n{category.upper()}:\n"
                message += " ".join(tags[:10])
                if len(tags) > 10:
                    message += f" ... +{len(tags) - 10}"
                message += "\n"

        await query.edit_message_text(
            message,
            reply_markup=get_back_keyboard("accounts_proxy")
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка хэштегов: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при получении списка хэштегов",
            reply_markup=get_back_keyboard("accounts_proxy")
        )


async def delete_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление аккаунта"""
    query = update.callback_query
    await query.answer()

    try:
        # Если это выбор конкретного аккаунта для удаления
        if query.data.startswith("del_acc_"):
            account_id = int(query.data.split("_")[2])
            async with db_manager.get_async_session() as session:
                account = await session.get(Account, account_id)
                if account:
                    username = account.username
                    await session.delete(account)
                    await session.commit()
                    message = f"✅ Аккаунт @{username} удален"
                else:
                    message = "❌ Аккаунт не найден"

            await query.edit_message_text(
                message,
                reply_markup=get_back_keyboard("accounts_proxy")
            )
            return

        # Показываем список аккаунтов для удаления
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(Account))
            accounts = result.scalars().all()

        if not accounts:
            await query.edit_message_text(
                "❌ Нет аккаунтов для удаления",
                reply_markup=get_back_keyboard("accounts_proxy")
            )
            return

        keyboard = []
        for acc in accounts[:20]:
            emoji = "🧠" if acc.account_type == "influencer" else "📣"
            keyboard.append([
                InlineKeyboardButton(
                    f"{emoji} @{acc.username}",
                    callback_data=f"del_acc_{acc.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="accounts_proxy")])

        await query.edit_message_text(
            "❌ Выберите аккаунт для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Ошибка при удалении аккаунта: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при удалении аккаунта",
            reply_markup=get_back_keyboard("accounts_proxy")
        )


async def delete_proxy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление прокси"""
    query = update.callback_query
    await query.answer()

    try:
        # Если это выбор конкретной прокси для удаления
        if query.data.startswith("del_proxy_"):
            proxy_id = int(query.data.split("_")[2])
            async with db_manager.get_async_session() as session:
                proxy = await session.get(Proxy, proxy_id)
                if proxy:
                    host_port = f"{proxy.host}:{proxy.port}"
                    await session.delete(proxy)
                    await session.commit()
                    message = f"✅ Прокси {host_port} удалена"
                else:
                    message = "❌ Прокси не найдена"

            await query.edit_message_text(
                message,
                reply_markup=get_back_keyboard("accounts_proxy")
            )
            return

        # Показываем список прокси для удаления
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(Proxy))
            proxies = result.scalars().all()

        if not proxies:
            await query.edit_message_text(
                "❌ Нет прокси для удаления",
                reply_markup=get_back_keyboard("accounts_proxy")
            )
            return

        keyboard = []
        for proxy in proxies[:20]:
            keyboard.append([
                InlineKeyboardButton(
                    f"{proxy.host}:{proxy.port}",
                    callback_data=f"del_proxy_{proxy.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="accounts_proxy")])

        await query.edit_message_text(
            "❌ Выберите прокси для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Ошибка при удалении прокси: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при удалении прокси",
            reply_markup=get_back_keyboard("accounts_proxy")
        )


async def form_rings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Формирование колец шиллеров"""
    query = update.callback_query
    await query.answer()

    # Сохраняем откуда пришли
    context.user_data['previous_menu'] = 'accounts_proxy'

    message = (
        "🔗 Формирование колец шиллеров\n\n"
        "Укажите размер кольца (количество шиллеров в одном кольце).\n"
        "Рекомендуется: 4 шиллера на кольцо.\n\n"
        "Отправьте число от 3 до 8:"
    )

    await query.edit_message_text(
        message,
        reply_markup=get_cancel_keyboard()
    )

    context.user_data['waiting_for'] = 'ring_size_input'


async def set_ring_size_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка размера кольца"""
    if context.user_data.get('waiting_for') != 'ring_size_input':
        return

    try:
        ring_size = int(update.message.text.strip())
        if 3 <= ring_size <= 8:
            context.user_data['ring_size'] = ring_size
            context.user_data['waiting_for'] = 'ring_formation'

            # Получаем доступных шиллеров
            shillers = await db_manager.get_accounts_by_type("shiller")
            available_count = len(shillers)
            rings_possible = available_count // ring_size

            message = (
                f"✅ Размер кольца: {ring_size}\n\n"
                f"Доступно шиллеров: {available_count}\n"
                f"Можно создать колец: {rings_possible}\n\n"
            )

            if rings_possible > 0:
                message += "Создать кольца автоматически?"
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Да", callback_data="auto_form_rings"),
                        InlineKeyboardButton("❌ Нет", callback_data="accounts_proxy")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                message += "❌ Недостаточно шиллеров для создания колец"
                reply_markup = get_back_keyboard("accounts_proxy")

            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(
                "❌ Размер кольца должен быть от 3 до 8",
                reply_markup=get_cancel_keyboard()
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Введите число",
            reply_markup=get_cancel_keyboard()
        )


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки отмены"""
    query = update.callback_query
    await query.answer()

    # Определяем откуда пришел пользователь
    previous_menu = context.user_data.get('previous_menu', 'accounts_proxy')

    # Очищаем контекст пользователя
    context.user_data.clear()

    # Возвращаемся в соответствующее меню
    if previous_menu == 'influencers':
        from .influencers import influencers_menu_handler
        await influencers_menu_handler(update, context)
    elif previous_menu == 'shillers':
        from .shillers import shillers_menu_handler
        await shillers_menu_handler(update, context)
    elif previous_menu == 'configure_content':
        from .influencers import configure_content_handler
        await configure_content_handler(update, context)
    else:
        await accounts_proxy_menu_handler(update, context)