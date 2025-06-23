from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Account(Base):
    """Модель аккаунта Twitter"""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(255))
    email_password = Column(String(255))

    account_type = Column(String(20))  # 'influencer', 'shiller', 'memecoin'
    status = Column(String(20), default='active')  # 'active', 'suspended', 'banned'

    proxy_id = Column(Integer, ForeignKey('proxies.id'))
    proxy = relationship("Proxy", back_populates="accounts")

    # Статистика
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    tweets_count = Column(Integer, default=0)

    # Настройки активности
    posts_per_day = Column(Integer, default=2)
    comments_per_day = Column(Integer, default=20)
    likes_per_day = Column(Integer, default=50)

    # Cookies и session data
    cookies = Column(JSON)
    local_storage = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active = Column(DateTime)

    # Relationships
    influencer_sources = relationship("InfluencerSource", back_populates="influencer")
    shiller_rings = relationship("ShillerRing", secondary="shiller_ring_members", back_populates="members")
    activities = relationship("Activity", back_populates="account")


class Proxy(Base):
    """Модель прокси"""
    __tablename__ = 'proxies'

    id = Column(Integer, primary_key=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255))
    password = Column(String(255))
    protocol = Column(String(10), default='http')  # http, socks5
    geo = Column(String(10))  # Страна

    is_active = Column(Boolean, default=True)
    last_check = Column(DateTime)
    response_time = Column(Float)  # ms

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="proxy")


class InfluencerSource(Base):
    """Источники контента для инфлюенсеров"""
    __tablename__ = 'influencer_sources'

    id = Column(Integer, primary_key=True)
    influencer_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    source_username = Column(String(50), nullable=False)
    importance_score = Column(Float, default=1.0)  # NI первоисточника

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    influencer = relationship("Account", back_populates="influencer_sources")


class ShillerRing(Base):
    """Кольцо шиллеров"""
    __tablename__ = 'shiller_rings'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    size = Column(Integer, default=4)
    is_active = Column(Boolean, default=True)

    # Настройки
    targets_per_shiller = Column(Integer, default=10)
    comments_per_round = Column(Integer, default=10)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    members = relationship("Account", secondary="shiller_ring_members", back_populates="shiller_rings")
    targets = relationship("ShillerTarget", back_populates="ring")
    rotations = relationship("ShillerRotation", back_populates="ring")


class ShillerRingMember(Base):
    """Связь между шиллерами и кольцами"""
    __tablename__ = 'shiller_ring_members'

    ring_id = Column(Integer, ForeignKey('shiller_rings.id'), primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), primary_key=True)
    position = Column(Integer)  # Позиция в кольце (1-4)
    joined_at = Column(DateTime, default=datetime.utcnow)


class ShillerTarget(Base):
    """Целевые аккаунты для шиллинга"""
    __tablename__ = 'shiller_targets'

    id = Column(Integer, primary_key=True)
    ring_id = Column(Integer, ForeignKey('shiller_rings.id'), nullable=False)
    target_username = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ring = relationship("ShillerRing", back_populates="targets")


class ShillerRotation(Base):
    """История ротаций в кольцах"""
    __tablename__ = 'shiller_rotations'

    id = Column(Integer, primary_key=True)
    ring_id = Column(Integer, ForeignKey('shiller_rings.id'), nullable=False)
    round_number = Column(Integer, nullable=False)

    # Пары взаимодействий в формате JSON
    # Например: [{"from": "A1", "to": "A2"}, {"from": "A2", "to": "A3"}]
    interactions = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ring = relationship("ShillerRing", back_populates="rotations")


class Campaign(Base):
    """Кампания шиллинга"""
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    token_name = Column(String(50), nullable=False)
    token_address = Column(String(100), nullable=False)
    quote_link = Column(String(500))  # Ссылка на пост для цитирования

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)

    # Relationships
    activities = relationship("Activity", back_populates="campaign")


class Activity(Base):
    """Логирование активности"""
    __tablename__ = 'activities'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))

    action_type = Column(String(50))  # 'tweet', 'comment', 'like', 'retweet', 'quote'
    target_url = Column(String(500))
    content = Column(Text)

    status = Column(String(20), default='success')  # 'success', 'failed'
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="activities")
    campaign = relationship("Campaign", back_populates="activities")


class Hashtag(Base):
    """Хэштеги"""
    __tablename__ = 'hashtags'

    id = Column(Integer, primary_key=True)
    tag = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))  # 'crypto', 'memecoin', 'general'
    usage_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)