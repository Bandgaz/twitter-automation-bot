from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Account:
    """Датакласс для работы с аккаунтом Twitter"""

    # Основные данные
    id: int
    username: str
    password: str
    account_type: str  # 'influencer', 'shiller', 'memecoin'

    # Опциональные данные
    email: Optional[str] = None
    email_password: Optional[str] = None
    status: str = 'active'  # 'active', 'suspended', 'banned'

    # Прокси
    proxy_id: Optional[int] = None
    proxy: Optional[Dict] = None

    # Статистика
    followers_count: int = 0
    following_count: int = 0
    tweets_count: int = 0

    # Настройки активности
    posts_per_day: int = 2
    comments_per_day: int = 20
    likes_per_day: int = 50

    # Сессионные данные
    cookies: Optional[List[Dict]] = None
    local_storage: Optional[Dict] = None

    # Временные метки
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None

    def __post_init__(self):
        """Валидация после инициализации"""
        if self.account_type not in ['influencer', 'shiller', 'memecoin']:
            raise ValueError(f"Invalid account type: {self.account_type}")

        if self.status not in ['active', 'suspended', 'banned']:
            raise ValueError(f"Invalid status: {self.status}")

    def to_dict(self) -> Dict:
        """Преобразовать в словарь"""
        return {
            'id': self.id,
            'username': self.username,
            'password': self.password,
            'account_type': self.account_type,
            'email': self.email,
            'email_password': self.email_password,
            'status': self.status,
            'proxy_id': self.proxy_id,
            'proxy': self.proxy,
            'followers_count': self.followers_count,
            'following_count': self.following_count,
            'tweets_count': self.tweets_count,
            'posts_per_day': self.posts_per_day,
            'comments_per_day': self.comments_per_day,
            'likes_per_day': self.likes_per_day,
            'cookies': self.cookies,
            'local_storage': self.local_storage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Account':
        """Создать из словаря"""
        # Преобразуем строковые даты обратно в datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if isinstance(data.get('last_active'), str):
            data['last_active'] = datetime.fromisoformat(data['last_active'])

        return cls(**data)

    @property
    def is_active(self) -> bool:
        """Проверка активности аккаунта"""
        return self.status == 'active'

    @property
    def is_suspended(self) -> bool:
        """Проверка приостановки аккаунта"""
        return self.status == 'suspended'

    @property
    def is_banned(self) -> bool:
        """Проверка бана аккаунта"""
        return self.status == 'banned'

    @property
    def has_proxy(self) -> bool:
        """Проверка наличия прокси"""
        return self.proxy_id is not None

    @property
    def has_email(self) -> bool:
        """Проверка наличия email"""
        return self.email is not None

    def update_stats(self, followers: int = None, following: int = None, tweets: int = None):
        """Обновить статистику"""
        if followers is not None:
            self.followers_count = followers
        if following is not None:
            self.following_count = following
        if tweets is not None:
            self.tweets_count = tweets
        self.updated_at = datetime.utcnow()

    def update_last_active(self):
        """Обновить время последней активности"""
        self.last_active = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def __str__(self) -> str:
        """Строковое представление"""
        return f"Account(@{self.username}, {self.account_type}, {self.status})"

    def __repr__(self) -> str:
        """Представление для отладки"""
        return f"Account(id={self.id}, username='{self.username}', type='{self.account_type}')"