from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from utils.helpers import get_random_tip
from models import User, UserProgress
from sqlalchemy import select
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_daily_tip(bot: Bot, db):
    """
    Отправляет ежедневный совет всем активным пользователям
    """
    try:
        # Получаем активных пользователей (заходили за последние 7 дней)
        week_ago = datetime.now() - timedelta(days=7)
        users = await db.execute(
            select(User).where(User.last_active >= week_ago)
        )
        users = users.scalars().all()
        
        tip = get_random_tip()
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await bot.send_message(
                    user.tg_id, 
                    f"💡 **Совет дня**\n\n{tip}",
                    parse_mode="HTML"
                )
                sent += 1
            except Exception as e:
                failed += 1
                logger.error(f"Не удалось отправить совет пользователю {user.tg_id}: {e}")
        
        logger.info(f"✅ Ежедневные советы отправлены: {sent} успешно, {failed} с ошибками")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке советов: {e}")


async def smart_resume(bot: Bot, db, user_id: int = None):
    """
    Отправляет напоминание о незавершенных уроках
    Если user_id указан - отправляет конкретному пользователю,
    иначе - всем пользователям с незавершенными курсами
    """
    try:
        if user_id:
            # Отправляем конкретному пользователю
            await send_resume_to_user(bot, db, user_id)
        else:
            # Отправляем всем пользователям с незавершенными курсами
            users_with_progress = await db.execute(
                select(User)
                .join(UserProgress)
                .distinct()
            )
            users = users_with_progress.scalars().all()
            
            for user in users:
                await send_resume_to_user(bot, db, user.id)
                
    except Exception as e:
        logger.error(f"❌ Ошибка в smart_resume: {e}")


async def send_resume_to_user(bot: Bot, db, user_id: int):
    """
    Отправляет напоминание конкретному пользователю
    """
    try:
        # Получаем пользователя
        user = await db.get(User, user_id)
        if not user:
            return
        
        # Получаем прогресс пользователя
        progresses = await db.execute(
            select(UserProgress)
            .where(UserProgress.user_id == user_id)
            .order_by(UserProgress.last_accessed.desc())
        )
        progresses = progresses.scalars().all()
        
        if not progresses:
            return  # Нет незавершенных курсов
        
        # Берём последний активный курс
        last_progress = progresses[0]
        
        # Здесь нужно получить название подкатегории из JSON
        from utils.json_db import json_db
        subcategory = json_db.get_subcategory(last_progress.subcategory_id)
        
        if not subcategory:
            return
        
        # Формируем сообщение
        text = (
            f"👋 **Привет, {user.name}!**\n\n"
            f"Вы остановились на курсе **{subcategory['name']}**.\n"
            f"Урок: {last_progress.current_material_index + 1}\n\n"
            f"Хотите продолжить обучение? Нажмите /start и выберите '📚 Курсы'!"
        )
        
        await bot.send_message(user.tg_id, text, parse_mode="HTML")
        logger.info(f"✅ Напоминание отправлено пользователю {user.tg_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке напоминания пользователю {user_id}: {e}")


async def check_inactive_users(bot: Bot, db, days: int = 7):
    """
    Проверяет неактивных пользователей и отправляет мотивационное сообщение
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        inactive_users = await db.execute(
            select(User).where(User.last_active < cutoff_date)
        )
        inactive_users = inactive_users.scalars().all()
        
        for user in inactive_users:
            try:
                text = (
                    f"👋 **Мы скучаем!**\n\n"
                    f"Привет, {user.name}! Вы давно не заходили в бота.\n"
                    f"Новые курсы уже ждут вас! Заходите продолжить обучение 🚀"
                )
                await bot.send_message(user.tg_id, text, parse_mode="HTML")
                logger.info(f"✅ Мотивационное сообщение отправлено {user.tg_id}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки {user.tg_id}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Ошибка в check_inactive_users: {e}")


async def send_weekly_stats(bot: Bot, db):
    """
    Отправляет еженедельную статистику активным пользователям
    """
    try:
        week_ago = datetime.now() - timedelta(days=7)
        
        active_users = await db.execute(
            select(User).where(User.last_active >= week_ago)
        )
        active_users = active_users.scalars().all()
        
        for user in active_users:
            try:
                # Получаем прогресс за неделю
                progresses = await db.execute(
                    select(UserProgress)
                    .where(
                        UserProgress.user_id == user.id,
                        UserProgress.last_accessed >= week_ago
                    )
                )
                progresses = progresses.scalars().all()
                
                lessons_done = 0
                for p in progresses:
                    if p.completed_materials:
                        lessons_done += len(p.completed_materials)
                
                text = (
                    f"📊 **Ваша статистика за неделю**\n\n"
                    f"👤 {user.name}\n"
                    f"📚 Изучено уроков: {lessons_done}\n"
                    f"📈 Текущий уровень: {user.level}\n"
                    f"⭐ Всего XP: {user.xp}\n\n"
                    f"Так держать! 🚀"
                )
                
                await bot.send_message(user.tg_id, text, parse_mode="HTML")
                logger.info(f"✅ Статистика отправлена {user.tg_id}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки статистики {user.tg_id}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Ошибка в send_weekly_stats: {e}")