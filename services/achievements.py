from sqlalchemy import select
from models import Achievement, UserAchievement, User
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_and_give_achievement(db: AsyncSession, user_id: int, code: str):
    """
    Проверяет и выдаёт достижение пользователю, если его ещё нет
    """
    try:
        # Находим достижение по коду
        result = await db.execute(select(Achievement).where(Achievement.code == code))
        ach = result.scalar_one_or_none()
        
        if not ach:
            logger.warning(f"Достижение с кодом {code} не найдено")
            return None
        
        # Проверяем, есть ли уже такое достижение у пользователя
        result = await db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == ach.id
            )
        )
        exists = result.scalar_one_or_none()
        
        if not exists:
            # Выдаём достижение
            new_ach = UserAchievement(user_id=user_id, achievement_id=ach.id)
            db.add(new_ach)
            await db.commit()
            
            logger.info(f"🏆 Пользователь {user_id} получил достижение: {ach.name}")
            
            # Возвращаем информацию о достижении для уведомления
            return {
                "name": ach.name,
                "description": ach.description,
                "icon": ach.icon or "🏆"
            }
        
        return None  # Уже есть такое достижение
        
    except Exception as e:
        logger.error(f"Ошибка при выдаче достижения: {e}")
        return None


async def get_user_achievements(db: AsyncSession, user_id: int):
    """
    Возвращает список достижений пользователя
    """
    try:
        result = await db.execute(
            select(Achievement)
            .join(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.unlocked_at.desc())
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Ошибка при получении достижений: {e}")
        return []


async def check_lesson_achievements(db: AsyncSession, user_id: int, lesson_count: int):
    """
    Проверяет достижения, связанные с количеством уроков
    """
    achievements_to_check = []
    
    if lesson_count >= 1:
        achievements_to_check.append("first_lesson")
    if lesson_count >= 10:
        achievements_to_check.append("10_lessons")
    if lesson_count >= 50:
        achievements_to_check.append("50_lessons")
    if lesson_count >= 100:
        achievements_to_check.append("100_lessons")
    
    new_achievements = []
    for code in achievements_to_check:
        result = await check_and_give_achievement(db, user_id, code)
        if result:
            new_achievements.append(result)
    
    return new_achievements


async def check_course_achievements(db: AsyncSession, user_id: int, course_count: int):
    """
    Проверяет достижения, связанные с количеством курсов
    """
    achievements_to_check = []
    
    if course_count >= 1:
        achievements_to_check.append("first_course")
    if course_count >= 5:
        achievements_to_check.append("5_courses")
    if course_count >= 10:
        achievements_to_check.append("10_courses")
    
    new_achievements = []
    for code in achievements_to_check:
        result = await check_and_give_achievement(db, user_id, code)
        if result:
            new_achievements.append(result)
    
    return new_achievements


async def check_streak_achievements(db: AsyncSession, user_id: int, streak_days: int):
    """
    Проверяет достижения, связанные с непрерывными днями обучения
    """
    achievements_to_check = []
    
    if streak_days >= 3:
        achievements_to_check.append("streak_3")
    if streak_days >= 7:
        achievements_to_check.append("streak_7")
    if streak_days >= 30:
        achievements_to_check.append("streak_30")
    
    new_achievements = []
    for code in achievements_to_check:
        result = await check_and_give_achievement(db, user_id, code)
        if result:
            new_achievements.append(result)
    
    return new_achievements


async def initialize_achievements(db: AsyncSession):
    """
    Инициализирует базовые достижения в БД (если их нет)
    """
    achievements = [
        {"code": "first_lesson", "name": "Первый урок!", "description": "Изучил первый урок", "icon": "📚"},
        {"code": "10_lessons", "name": "10 уроков", "description": "Изучил 10 уроков", "icon": "📖"},
        {"code": "50_lessons", "name": "50 уроков", "description": "Изучил 50 уроков", "icon": "📕"},
        {"code": "100_lessons", "name": "100 уроков", "description": "Изучил 100 уроков", "icon": "📗"},
        
        {"code": "first_course", "name": "Первый курс!", "description": "Завершил первый курс", "icon": "🎓"},
        {"code": "5_courses", "name": "5 курсов", "description": "Завершил 5 курсов", "icon": "🏅"},
        {"code": "10_courses", "name": "10 курсов", "description": "Завершил 10 курсов", "icon": "🏆"},
        
        {"code": "streak_3", "name": "3 дня подряд", "description": "Учился 3 дня подряд", "icon": "🔥"},
        {"code": "streak_7", "name": "7 дней подряд", "description": "Учился 7 дней подряд", "icon": "⚡"},
        {"code": "streak_30", "name": "30 дней подряд", "description": "Учился месяц без перерыва", "icon": "💫"},
    ]
    
    for ach_data in achievements:
        # Проверяем, есть ли уже такое достижение
        result = await db.execute(select(Achievement).where(Achievement.code == ach_data["code"]))
        existing = result.scalar_one_or_none()
        
        if not existing:
            ach = Achievement(**ach_data)
            db.add(ach)
    
    await db.commit()
    logger.info("✅ Достижения инициализированы")