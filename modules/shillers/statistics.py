from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select, func, and_
from loguru import logger

from database.db_manager import db_manager
from database.models import Campaign, Activity, ShillerRing, Account


class ShillerStatistics:
    """Класс для сбора и анализа статистики шиллинга"""

    @staticmethod
    async def get_campaign_stats(campaign_id: int, date: datetime = None) -> Dict:
        """
        Получить статистику кампании за день

        Args:
            campaign_id: ID кампании
            date: Дата (по умолчанию - сегодня)

        Returns:
            Словарь со статистикой
        """
        if not date:
            date = datetime.now().date()
        else:
            date = date.date()

        async with db_manager.get_async_session() as session:
            # Получаем кампанию
            campaign = await session.get(Campaign, campaign_id)
            if not campaign:
                return {}

            # Подсчет активностей по типам
            result = await session.execute(
                select(
                    Activity.action_type,
                    func.count(Activity.id).label('count')
                )
                .where(
                    and_(
                        Activity.campaign_id == campaign_id,
                        func.date(Activity.created_at) == date
                    )
                )
                .group_by(Activity.action_type)
            )

            activities = {row.action_type: row.count for row in result}

            # Подсчет уникальных шиллеров
            unique_shillers_result = await session.execute(
                select(func.count(func.distinct(Activity.account_id)))
                .where(
                    and_(
                        Activity.campaign_id == campaign_id,
                        func.date(Activity.created_at) == date
                    )
                )
            )
            unique_shillers = unique_shillers_result.scalar() or 0

            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "token_name": campaign.token_name,
                "date": date.isoformat(),
                "comments": activities.get("comment", 0),
                "likes": activities.get("like", 0),
                "quotes": activities.get("quote", 0),
                "replies": activities.get("reply", 0),
                "total_actions": sum(activities.values()),
                "unique_shillers": unique_shillers,
            }

    @staticmethod
    async def get_ring_stats(ring_id: int, date: datetime = None) -> Dict:
        """Получить статистику кольца за день"""
        if not date:
            date = datetime.now().date()
        else:
            date = date.date()

        async with db_manager.get_async_session() as session:
            # Получаем кольцо
            ring = await session.get(ShillerRing, ring_id)
            if not ring:
                return {}

            # Получаем ID участников кольца
            member_ids = [member.id for member in ring.members]

            # Подсчет активностей участников кольца
            result = await session.execute(
                select(
                    Activity.action_type,
                    Activity.account_id,
                    func.count(Activity.id).label('count')
                )
                .where(
                    and_(
                        Activity.account_id.in_(member_ids),
                        func.date(Activity.created_at) == date
                    )
                )
                .group_by(Activity.action_type, Activity.account_id)
            )

            # Группируем по участникам
            member_stats = {}
            total_activities = {"comment": 0, "like": 0, "quote": 0, "reply": 0}

            for row in result:
                if row.account_id not in member_stats:
                    member_stats[row.account_id] = {
                        "comment": 0, "like": 0, "quote": 0, "reply": 0
                    }
                member_stats[row.account_id][row.action_type] = row.count
                total_activities[row.action_type] += row.count

            # Получаем информацию о ротациях
            from database.models import ShillerRotation
            rotations_result = await session.execute(
                select(func.count(ShillerRotation.id))
                .where(
                    and_(
                        ShillerRotation.ring_id == ring_id,
                        func.date(ShillerRotation.created_at) == date
                    )
                )
            )
            rounds_today = rotations_result.scalar() or 0

            return {
                "ring_id": ring_id,
                "ring_name": ring.name,
                "date": date.isoformat(),
                "members_count": len(member_ids),
                "rounds_completed": rounds_today,
                "total_comments": total_activities["comment"],
                "total_likes": total_activities["like"],
                "total_quotes": total_activities["quote"],
                "total_replies": total_activities["reply"],
                "member_breakdown": member_stats,
            }

    @staticmethod
    async def get_all_rings_stats(date: datetime = None) -> List[Dict]:
        """Получить статистику всех колец за день"""
        if not date:
            date = datetime.now().date()
        else:
            date = date.date()

        async with db_manager.get_async_session() as session:
            # Получаем все активные кольца
            result = await session.execute(
                select(ShillerRing).where(ShillerRing.is_active == True)
            )
            rings = result.scalars().all()

            stats = []
            for ring in rings:
                ring_stats = await ShillerStatistics.get_ring_stats(ring.id,
                                                                    datetime.combine(date, datetime.min.time()))
                stats.append(ring_stats)

            return stats

    @staticmethod
    async def get_shiller_performance(account_id: int, period_days: int = 7) -> Dict:
        """Получить производительность шиллера за период"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=period_days)

        async with db_manager.get_async_session() as session:
            # Получаем аккаунт
            account = await session.get(Account, account_id)
            if not account:
                return {}

            # Подсчет активностей
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
            daily_performance = {}
            total_by_type = {"comment": 0, "like": 0, "quote": 0, "reply": 0}

            for row in result:
                date_str = row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date)
                if date_str not in daily_performance:
                    daily_performance[date_str] = {
                        "comment": 0, "like": 0, "quote": 0, "reply": 0
                    }

                action_type = row.action_type
                count = row.count

                if action_type in daily_performance[date_str]:
                    daily_performance[date_str][action_type] = count
                    total_by_type[action_type] += count

            # Рассчитываем среднее
            avg_per_day = {
                action: total / period_days if period_days > 0 else 0
                for action, total in total_by_type.items()
            }

            return {
                "account_id": account_id,
                "username": account.username,
                "period_days": period_days,
                "daily_breakdown": daily_performance,
                "total_comments": total_by_type["comment"],
                "total_likes": total_by_type["like"],
                "total_quotes": total_by_type["quote"],
                "total_replies": total_by_type["reply"],
                "avg_comments_per_day": round(avg_per_day["comment"], 1),
                "avg_likes_per_day": round(avg_per_day["like"], 1),
                "avg_quotes_per_day": round(avg_per_day["quote"], 1),
                "avg_replies_per_day": round(avg_per_day["reply"], 1),
            }

    @staticmethod
    async def get_campaign_effectiveness(campaign_id: int) -> Dict:
        """Оценить эффективность кампании"""
        async with db_manager.get_async_session() as session:
            # Получаем кампанию
            campaign = await session.get(Campaign, campaign_id)
            if not campaign:
                return {}

            # Считаем общую статистику
            result = await session.execute(
                select(
                    Activity.action_type,
                    func.count(Activity.id).label('count'),
                    func.count(func.distinct(Activity.account_id)).label('unique_accounts')
                )
                .where(Activity.campaign_id == campaign_id)
                .group_by(Activity.action_type)
            )

            stats = {}
            total_actions = 0
            for row in result:
                stats[row.action_type] = {
                    "count": row.count,
                    "unique_accounts": row.unique_accounts
                }
                total_actions += row.count

            # Считаем продолжительность кампании
            if campaign.ended_at:
                duration = (campaign.ended_at - campaign.created_at).total_seconds() / 3600  # в часах
            else:
                duration = (datetime.utcnow() - campaign.created_at).total_seconds() / 3600

            # Рассчитываем метрики
            actions_per_hour = total_actions / duration if duration > 0 else 0

            # Получаем количество участников
            participants_result = await session.execute(
                select(func.count(func.distinct(Activity.account_id)))
                .where(Activity.campaign_id == campaign_id)
            )
            total_participants = participants_result.scalar() or 0

            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "token_name": campaign.token_name,
                "is_active": campaign.is_active,
                "duration_hours": round(duration, 1),
                "total_actions": total_actions,
                "actions_per_hour": round(actions_per_hour, 1),
                "total_participants": total_participants,
                "breakdown": stats,
                "effectiveness_score": await ShillerStatistics._calculate_effectiveness_score(stats, duration),
            }

    @staticmethod
    async def _calculate_effectiveness_score(stats: Dict, duration_hours: float) -> float:
        """
        Рассчитать оценку эффективности кампании

        Формула учитывает:
        - Количество действий
        - Разнообразие действий
        - Количество уникальных участников
        - Длительность кампании
        """
        if duration_hours == 0:
            return 0.0

        # Веса для разных типов действий
        weights = {
            "comment": 1.0,  # Комментарии наиболее ценны
            "quote": 0.8,  # Цитаты тоже важны
            "reply": 0.6,  # Ответы средней важности
            "like": 0.3,  # Лайки наименее ценны
        }

        weighted_score = 0
        action_types_used = 0

        for action_type, weight in weights.items():
            if action_type in stats:
                count = stats[action_type]["count"]
                unique = stats[action_type]["unique_accounts"]

                # Учитываем количество и уникальность
                action_score = count * weight * (unique / max(count, 1))
                weighted_score += action_score

                if count > 0:
                    action_types_used += 1

        # Бонус за разнообразие действий
        diversity_bonus = action_types_used / len(weights)

        # Нормализуем по времени (действий в час)
        hourly_score = weighted_score / duration_hours

        # Финальная оценка (0-100)
        final_score = min(100, hourly_score * diversity_bonus)

        return round(final_score, 1)

    @staticmethod
    async def generate_campaign_report(campaign_id: int) -> str:
        """Генерировать полный отчет по кампании"""
        # Получаем различные статистики
        today_stats = await ShillerStatistics.get_campaign_stats(campaign_id)
        effectiveness = await ShillerStatistics.get_campaign_effectiveness(campaign_id)

        if not today_stats or not effectiveness:
            return "❌ Кампания не найдена"

        # Получаем статистику колец
        rings_stats = await ShillerStatistics.get_all_rings_stats()
        active_rings = len([r for r in rings_stats if r.get("total_comments", 0) > 0])

        report = f"""
📊 ОТЧЕТ ПО КАМПАНИИ ШИЛЛИНГА
{'=' * 40}

💰 Токен: ${effectiveness['token_name']}
📅 Статус: {'🟢 Активна' if effectiveness['is_active'] else '🔴 Завершена'}
⏱ Длительность: {effectiveness['duration_hours']:.1f} часов

📈 ОБЩАЯ СТАТИСТИКА:
• Всего действий: {effectiveness['total_actions']}
• Действий в час: {effectiveness['actions_per_hour']:.1f}
• Участников: {effectiveness['total_participants']}
• Активных колец: {active_rings}

📊 СТАТИСТИКА ЗА СЕГОДНЯ:
• Комментариев: {today_stats['comments']}
• Лайков: {today_stats['likes']}
• Цитат: {today_stats['quotes']}
• Ответов: {today_stats.get('replies', 0)}
• Уникальных шиллеров: {today_stats['unique_shillers']}

💎 РАЗБИВКА ПО ТИПАМ:
"""

        # Добавляем разбивку
        for action_type, data in effectiveness['breakdown'].items():
            report += f"• {action_type.capitalize()}: {data['count']} (от {data['unique_accounts']} аккаунтов)\n"

        report += f"""
⚡ ОЦЕНКА ЭФФЕКТИВНОСТИ: {effectiveness['effectiveness_score']}/100

{'=' * 40}
"""

        return report.strip()