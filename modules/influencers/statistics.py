from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select, func, and_
from loguru import logger

from database.db_manager import db_manager
from database.models import Account, Activity


class InfluencerStatistics:
    """Класс для сбора и анализа статистики инфлюенсеров"""

    @staticmethod
    async def get_daily_stats(account_id: int, date: datetime = None) -> Dict:
        """
        Получить статистику за день для конкретного инфлюенсера

        Args:
            account_id: ID аккаунта
            date: Дата (по умолчанию - сегодня)

        Returns:
            Словарь со статистикой
        """
        if not date:
            date = datetime.now().date()
        else:
            date = date.date()

        async with db_manager.get_async_session() as session:
            # Подсчет активностей по типам
            result = await session.execute(
                select(
                    Activity.action_type,
                    func.count(Activity.id).label('count')
                )
                .where(
                    and_(
                        Activity.account_id == account_id,
                        func.date(Activity.created_at) == date
                    )
                )
                .group_by(Activity.action_type)
            )

            activities = {row.action_type: row.count for row in result}

            # Получаем информацию об аккаунте
            account = await session.get(Account, account_id)

            return {
                "account_id": account_id,
                "username": account.username if account else "Unknown",
                "date": date.isoformat(),
                "posts": activities.get("tweet", 0),
                "comments": activities.get("comment", 0),
                "likes": activities.get("like", 0),
                "retweets": activities.get("retweet", 0),
                "quotes": activities.get("quote", 0),
                "total_actions": sum(activities.values()),
                "followers_count": account.followers_count if account else 0,
                "following_count": account.following_count if account else 0,
            }

    @staticmethod
    async def get_weekly_stats(account_id: int) -> Dict:
        """Получить статистику за неделю"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)

        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(
                    func.date(Activity.created_at).label('date'),
                    Activity.action_type,
                    func.count(Activity.id).label('count')
                )
                .where(
                    and_(
                        Activity.account_id == account_id,
                        func.date(Activity.created_at) >= start_date,
                        func.date(Activity.created_at) <= end_date
                    )
                )
                .group_by(func.date(Activity.created_at), Activity.action_type)
                .order_by(func.date(Activity.created_at))
            )

            # Группируем по дням
            daily_stats = {}
            for row in result:
                date_str = row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date)
                if date_str not in daily_stats:
                    daily_stats[date_str] = {
                        "posts": 0,
                        "comments": 0,
                        "likes": 0,
                        "quotes": 0,
                    }

                if row.action_type == "tweet":
                    daily_stats[date_str]["posts"] = row.count
                elif row.action_type == "comment":
                    daily_stats[date_str]["comments"] = row.count
                elif row.action_type == "like":
                    daily_stats[date_str]["likes"] = row.count
                elif row.action_type == "quote":
                    daily_stats[date_str]["quotes"] = row.count

            return {
                "account_id": account_id,
                "period": "week",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily_breakdown": daily_stats,
                "total_posts": sum(day["posts"] for day in daily_stats.values()),
                "total_comments": sum(day["comments"] for day in daily_stats.values()),
                "total_likes": sum(day["likes"] for day in daily_stats.values()),
                "total_quotes": sum(day["quotes"] for day in daily_stats.values()),
            }

    @staticmethod
    async def get_all_influencers_stats(date: datetime = None) -> List[Dict]:
        """Получить статистику всех инфлюенсеров за день"""
        if not date:
            date = datetime.now().date()
        else:
            date = date.date()

        # Получаем всех инфлюенсеров
        influencers = await db_manager.get_accounts_by_type("influencer")

        stats = []
        for influencer in influencers:
            daily_stats = await InfluencerStatistics.get_daily_stats(influencer.id,
                                                                     datetime.combine(date, datetime.min.time()))
            stats.append(daily_stats)

        # Сортируем по общему количеству действий
        stats.sort(key=lambda x: x["total_actions"], reverse=True)

        return stats

    @staticmethod
    async def get_engagement_rate(account_id: int, period_days: int = 7) -> float:
        """
        Рассчитать engagement rate за период

        Engagement Rate = (Likes + Comments + Retweets) / Posts / Followers * 100
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=period_days)

        async with db_manager.get_async_session() as session:
            # Получаем аккаунт
            account = await session.get(Account, account_id)
            if not account or account.followers_count == 0:
                return 0.0

            # Считаем активности
            result = await session.execute(
                select(
                    Activity.action_type,
                    func.count(Activity.id).label('count')
                )
                .where(
                    and_(
                        Activity.account_id == account_id,
                        func.date(Activity.created_at) >= start_date,
                        func.date(Activity.created_at) <= end_date,
                        Activity.action_type.in_(["tweet", "like", "comment", "retweet"])
                    )
                )
                .group_by(Activity.action_type)
            )

            activities = {row.action_type: row.count for row in result}

            posts = activities.get("tweet", 0)
            if posts == 0:
                return 0.0

            engagements = activities.get("like", 0) + activities.get("comment", 0) + activities.get("retweet", 0)

            # Рассчитываем engagement rate
            engagement_rate = (engagements / posts / account.followers_count) * 100

            return round(engagement_rate, 2)

    @staticmethod
    async def get_best_posting_times(account_id: int, period_days: int = 30) -> Dict:
        """Определить лучшее время для постинга на основе активности"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        async with db_manager.get_async_session() as session:
            # Получаем все посты за период
            result = await session.execute(
                select(
                    func.extract('hour', Activity.created_at).label('hour'),
                    func.count(Activity.id).label('count')
                )
                .where(
                    and_(
                        Activity.account_id == account_id,
                        Activity.created_at >= start_date,
                        Activity.created_at <= end_date,
                        Activity.action_type == "tweet"
                    )
                )
                .group_by(func.extract('hour', Activity.created_at))
                .order_by(func.count(Activity.id).desc())
            )

            hourly_distribution = {int(row.hour): row.count for row in result}

            # Находим топ-3 часа
            sorted_hours = sorted(hourly_distribution.items(), key=lambda x: x[1], reverse=True)
            best_hours = [hour for hour, count in sorted_hours[:3]]

            return {
                "best_hours": best_hours,
                "hourly_distribution": hourly_distribution,
                "recommendation": f"Лучшее время для постинга: {best_hours[0]}:00 - {best_hours[0] + 1}:00" if best_hours else "Недостаточно данных"
            }

    @staticmethod
    async def generate_report(account_id: int) -> str:
        """Генерировать текстовый отчет для инфлюенсера"""
        # Получаем различные статистики
        daily = await InfluencerStatistics.get_daily_stats(account_id)
        weekly = await InfluencerStatistics.get_weekly_stats(account_id)
        engagement = await InfluencerStatistics.get_engagement_rate(account_id)
        best_times = await InfluencerStatistics.get_best_posting_times(account_id)

        report = f"""
📊 ОТЧЕТ ИНФЛЮЕНСЕРА @{daily['username']}
{'=' * 40}

📅 Статистика за сегодня ({daily['date']}):
• Постов: {daily['posts']}
• Комментариев: {daily['comments']}
• Лайков: {daily['likes']}
• Цитат: {daily['quotes']}
• Всего действий: {daily['total_actions']}

📈 Статистика за неделю:
• Постов: {weekly['total_posts']}
• Комментариев: {weekly['total_comments']}
• Лайков: {weekly['total_likes']}
• Цитат: {weekly['total_quotes']}

💎 Показатели:
• Подписчиков: {daily['followers_count']}
• Подписок: {daily['following_count']}
• Engagement Rate: {engagement}%

⏰ Рекомендации:
{best_times['recommendation']}

{'=' * 40}
        """

        return report.strip()