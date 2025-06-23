from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, List, Dict, Any
import asyncio
from loguru import logger
from sqlalchemy.orm import selectinload
from config import DATABASE_URL
from .models import Base, Account, Proxy, Campaign, ShillerRing, ShillerRingMember, Hashtag


class DatabaseManager:
    """Менеджер для работы с базой данных"""

    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None

    async def initialize(self):
        """Инициализация базы данных"""
        # Преобразование URL для async
        if DATABASE_URL.startswith("sqlite"):
            async_url = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        else:
            async_url = DATABASE_URL

        logger.info(f"Инициализация БД с URL: {async_url}")

        # Создание движков
        self.engine = create_engine(DATABASE_URL, echo=False)
        self.async_engine = create_async_engine(async_url, echo=False)

        # Создание фабрик сессий
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.AsyncSessionLocal = async_sessionmaker(bind=self.async_engine)

        # Создание таблиц
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Таблицы БД созданы")

        logger.info("База данных инициализирована успешно")

    @contextmanager
    def get_session(self) -> Session:
        """Получить синхронную сессию"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка в сессии БД: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncSession:
        """Получить асинхронную сессию"""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка в async сессии БД: {e}")
                raise
            finally:
                await session.close()

    # === Методы для работы с аккаунтами ===

    async def add_account(self, username: str, password: str,
                          account_type: str, **kwargs) -> Account:
        """Добавить новый аккаунт"""
        async with self.get_async_session() as session:
            account = Account(
                username=username,
                password=password,
                account_type=account_type,
                **kwargs
            )
            session.add(account)
            await session.commit()
            await session.refresh(account)
            return account

    async def get_account(self, account_id: int) -> Optional[Account]:
        """Получить аккаунт по ID"""
        async with self.get_async_session() as session:
            return await session.get(Account, account_id)

    async def get_accounts_by_type(self, account_type: str) -> List[Account]:
        async with self.get_async_session() as session:
            result = await session.execute(
                select(Account)
                .where(Account.account_type == account_type)
                .options(
                    selectinload(Account.influencer_sources),
                    selectinload(Account.activities),
                    selectinload(Account.proxy)
                )
            )
            return result.scalars().all()

    async def update_account_status(self, account_id: int, status: str):
        """Обновить статус аккаунта"""
        async with self.get_async_session() as session:
            account = await session.get(Account, account_id)
            if account:
                account.status = status
                await session.commit()

    async def update_account_proxy(self, account_id: int, proxy_id: int):
        async with self.get_async_session() as session:
            from sqlalchemy import select
            from sqlalchemy.exc import InvalidRequestError

            logger.debug(f"🔁 Привязка proxy_id={proxy_id} к account_id={account_id}")

            try:
                result = await session.execute(select(Account).where(Account.id == account_id))
                account = result.scalar_one_or_none()

                if not account:
                    logger.error(f"❌ Account с id={account_id} не найден")
                    return

                account.proxy_id = proxy_id
                await session.commit()

                logger.success(f"✅ Прокси успешно привязана к аккаунту {account.username}")
            except InvalidRequestError as e:
                logger.exception("SQLAlchemy session error (detached instance):")
            except Exception as e:
                logger.exception("Непредвиденная ошибка при обновлении прокси:")

    # === Методы для работы с прокси ===

    async def add_proxy(self, host: str, port: int, **kwargs) -> Proxy:
        """Добавить новую прокси"""
        async with self.get_async_session() as session:
            proxy = Proxy(host=host, port=port, **kwargs)
            session.add(proxy)
            await session.commit()
            await session.refresh(proxy)
            return proxy

    async def get_free_proxy(self) -> Optional[Proxy]:
        """Получить свободную прокси"""
        async with self.get_async_session() as session:
            # Прокси без привязанных аккаунтов
            result = await session.execute(
                select(Proxy)
                .where(Proxy.is_active == True)
                .where(~Proxy.accounts.any())
            )
            return result.scalars().first()

    # === Методы для работы с кольцами шиллеров ===

    async def create_shiller_ring(self, name: str, size: int = 4) -> ShillerRing:
        """Создать новое кольцо шиллеров"""
        async with self.get_async_session() as session:
            ring = ShillerRing(name=name, size=size)
            session.add(ring)
            await session.commit()
            await session.refresh(ring)
            return ring

    async def add_shiller_to_ring(self, ring_id: int, account_id: int, position: int):
        """Добавить шиллера в кольцо"""
        async with self.get_async_session() as session:
            # Проверяем, что аккаунт и кольцо существуют
            account = await session.get(Account, account_id)
            ring = await session.get(ShillerRing, ring_id)

            if account and ring:
                # Добавляем связь через таблицу-связку
                from sqlalchemy import insert
                stmt = insert(ShillerRingMember).values(
                    ring_id=ring_id,
                    account_id=account_id,
                    position=position
                )
                await session.execute(stmt)
                await session.commit()

    # === Методы для работы с кампаниями ===

    async def create_campaign(self, name: str, token_name: str,
                              token_address: str, quote_link: str = None) -> Campaign:
        """Создать новую кампанию"""
        async with self.get_async_session() as session:
            campaign = Campaign(
                name=name,
                token_name=token_name,
                token_address=token_address,
                quote_link=quote_link
            )
            session.add(campaign)
            await session.commit()
            await session.refresh(campaign)
            return campaign

    async def get_active_campaign(self) -> Optional[Campaign]:
        """Получить активную кампанию"""
        async with self.get_async_session() as session:
            result = await session.execute(
                select(Campaign).where(Campaign.is_active == True)
            )
            return result.scalars().first()

    # === Методы для работы с хэштегами ===

    async def add_hashtags(self, hashtags: List[str], category: str = None):
        """Добавить хэштеги"""
        async with self.get_async_session() as session:
            for tag in hashtags:
                # Проверяем, существует ли уже
                result = await session.execute(
                    select(Hashtag).where(Hashtag.tag == tag)
                )
                if not result.scalars().first():
                    hashtag = Hashtag(tag=tag, category=category)
                    session.add(hashtag)
            await session.commit()

    async def get_random_hashtags(self, count: int = 3) -> List[str]:
        """Получить случайные хэштеги"""
        async with self.get_async_session() as session:
            result = await session.execute(
                select(Hashtag).order_by(func.random()).limit(count)
            )
            hashtags = result.scalars().all()
            return [h.tag for h in hashtags]

    # === Статистика ===

    async def get_statistics(self, account_type: str = None) -> Dict[str, Any]:
        """Получить статистику"""
        async with self.get_async_session() as session:
            stats = {}

            # Общее количество аккаунтов
            if account_type:
                result = await session.execute(
                    select(func.count(Account.id)).where(Account.account_type == account_type)
                )
            else:
                result = await session.execute(select(func.count(Account.id)))
            stats['total_accounts'] = result.scalar()

            # Количество активных прокси
            result = await session.execute(
                select(func.count(Proxy.id)).where(Proxy.is_active == True)
            )
            stats['active_proxies'] = result.scalar()

            # Количество кампаний
            result = await session.execute(select(func.count(Campaign.id)))
            stats['total_campaigns'] = result.scalar()

            return stats


# Глобальный экземпляр менеджера
db_manager = DatabaseManager()


async def init_database():
    """Инициализация базы данных при запуске"""
    await db_manager.initialize()


# Удобные функции для импорта
get_session = db_manager.get_session
get_async_session = db_manager.get_async_session