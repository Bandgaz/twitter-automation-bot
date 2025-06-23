import re
from typing import Optional, Dict
from urllib.parse import urlparse


def validate_proxy_format(proxy_string: str) -> Optional[Dict]:
    """
    Валидация и парсинг прокси
    Поддерживаемые форматы:
    - protocol://username:password@host:port
    - host:port:username:password
    - host:port
    """
    proxy_data = {}

    # Формат с протоколом
    if '://' in proxy_string:
        try:
            parsed = urlparse(proxy_string)
            proxy_data['protocol'] = parsed.scheme
            proxy_data['host'] = parsed.hostname
            proxy_data['port'] = parsed.port

            if parsed.username:
                proxy_data['username'] = parsed.username
                proxy_data['password'] = parsed.password

            return proxy_data if proxy_data['host'] and proxy_data['port'] else None
        except:
            return None

    # Формат без протокола
    parts = proxy_string.split(':')

    if len(parts) == 2:
        # host:port
        proxy_data['host'] = parts[0]
        try:
            proxy_data['port'] = int(parts[1])
            proxy_data['protocol'] = 'http'
            return proxy_data
        except ValueError:
            return None

    elif len(parts) == 4:
        # host:port:username:password
        proxy_data['host'] = parts[0]
        try:
            proxy_data['port'] = int(parts[1])
            proxy_data['username'] = parts[2]
            proxy_data['password'] = parts[3]
            proxy_data['protocol'] = 'http'
            return proxy_data
        except ValueError:
            return None

    return None


def validate_account_format(account_string: str) -> Optional[Dict]:
    """
    Валидация формата аккаунта
    Формат: username:password:email:email_password
    """
    parts = account_string.strip().split(':')

    if len(parts) < 2:
        return None

    account_data = {
        'username': parts[0].strip(),
        'password': parts[1].strip()
    }

    # Валидация username (Twitter правила)
    if not re.match(r'^[a-zA-Z0-9_]{1,15}$', account_data['username']):
        return None

    # Опциональные поля
    if len(parts) > 2 and parts[2]:
        email = parts[2].strip()
        if validate_email(email):
            account_data['email'] = email

    if len(parts) > 3 and parts[3]:
        account_data['email_password'] = parts[3].strip()

    return account_data


def validate_email(email: str) -> bool:
    """Валидация email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_token_address(address: str) -> bool:
    """
    Валидация адреса токена
    Поддерживает Ethereum/BSC/Polygon адреса и Solana
    """
    # Ethereum-like адрес (0x...)
    if address.startswith('0x'):
        return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))

    # Solana адрес (base58, 32-44 символа)
    if len(address) >= 32 and len(address) <= 44:
        return bool(re.match(r'^[1-9A-HJ-NP-Za-km-z]+$', address))

    return False


def validate_twitter_url(url: str) -> bool:
    """Валидация URL Twitter"""
    patterns = [
        r'^https?://(?:www\.)?twitter\.com/\w+/status/\d+',
        r'^https?://(?:www\.)?x\.com/\w+/status/\d+',
        r'^https?://(?:www\.)?twitter\.com/\w+$',
        r'^https?://(?:www\.)?x\.com/\w+$',
    ]

    for pattern in patterns:
        if re.match(pattern, url):
            return True

    return False


def sanitize_hashtag(tag: str) -> str:
    """Очистка и форматирование хэштега"""
    # Удаляем пробелы
    tag = tag.strip()

    # Добавляем # если нет
    if not tag.startswith('#'):
        tag = '#' + tag

    # Удаляем недопустимые символы
    tag = re.sub(r'[^#\w]', '', tag)

    return tag


def validate_ring_size(size: int) -> bool:
    """Валидация размера кольца"""
    return 3 <= size <= 8


def parse_target_accounts(text: str) -> list:
    """Парсинг списка целевых аккаунтов"""
    accounts = []
    lines = text.strip().split('\n')

    for line in lines:
        # Убираем @ и пробелы
        account = line.strip().replace('@', '').replace(' ', '')

        # Валидация username
        if re.match(r'^[a-zA-Z0-9_]{1,15}$', account):
            accounts.append(account)

    return accounts