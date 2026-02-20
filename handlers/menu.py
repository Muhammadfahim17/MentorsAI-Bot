from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from database import get_db
from models import User, UserProgress, Bookmark
from keyboards import (
    get_main_menu_keyboard,
    back_button,
    get_rating_keyboard
)
from utils.json_db import json_db
from utils.helpers import format_profile, get_random_tip
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    """Показать профиль пользователя"""
    telegram_id = message.from_user.id
    async for db in get_db():
        user = await db.execute(select(User).where(User.tg_id == telegram_id))
        user = user.scalar_one_or_none()
        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return
        progress_count = await db.execute(select(func.count(UserProgress.id)).where(UserProgress.user_id == user.id))
        progress_count = progress_count.scalar()
        profile_text = format_profile(user)
        profile_text += f"\n\n📚 Начато курсов: {progress_count}"
        if user.photo_file_id:
            await message.answer_photo(photo=user.photo_file_id, caption=profile_text, reply_markup=back_button("back_to_main"))
        else:
            await message.answer(profile_text, reply_markup=back_button("back_to_main"))
        break

@router.message(F.text == "📊 Прогресс")
async def progress_handler(message: Message):
    """Показать прогресс пользователя"""
    telegram_id = message.from_user.id
    async for db in get_db():
        user = await db.execute(select(User).where(User.tg_id == telegram_id))
        user = user.scalar_one_or_none()
        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь.")
            return
        progresses = await db.execute(select(UserProgress).where(UserProgress.user_id == user.id))
        progresses = progresses.scalars().all()
        if not progresses:
            await message.answer("📊 Вы ещё не начали ни одного курса.\nНажмите '📚 Курсы' чтобы начать!", reply_markup=get_main_menu_keyboard())
            return
        text = "📊 **Ваш прогресс:**\n\n"
        for p in progresses:
            subcat = json_db.get_subcategory(p.subcategory_id)
            subcat_name = subcat['name'] if subcat else f"ID: {p.subcategory_id}"
            materials = json_db.get_materials(p.subcategory_id)
            total = len(materials)
            if total > 0:
                percent = (p.current_material_index / total) * 100
                emoji = "✅" if p.current_material_index >= total else "🔄"
                text += f"{emoji} **{subcat_name}**: {p.current_material_index}/{total} ({percent:.1f}%)\n"
            else:
                text += f"📌 **{subcat_name}**: {p.current_material_index} уроков\n"
        await message.answer(text, reply_markup=back_button("back_to_main"))
        break

@router.message(F.text == "🏆 ТОП-10")
async def top10_handler(message: Message):
    """Показать топ-10 пользователей"""
    async for db in get_db():
        top_users = await db.execute(select(User).order_by(User.xp.desc()).limit(10))
        top_users = top_users.scalars().all()
        if not top_users:
            await message.answer("🏆 Пока нет данных для топа.", reply_markup=get_main_menu_keyboard())
            return
        text = "🏆 **ТОП-10 пользователей**\n\n"
        for i, user in enumerate(top_users, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
            text += f"{medal} {i}. {user.name} — {user.xp} XP (ур.{user.level})\n"
        await message.answer(text, reply_markup=back_button("back_to_main"))
        break

@router.message(F.text == "⭐ Закладки")
async def bookmarks_handler(message: Message):
    """Показать сохраненные материалы"""
    telegram_id = message.from_user.id
    async for db in get_db():
        user = await db.execute(select(User).where(User.tg_id == telegram_id))
        user = user.scalar_one_or_none()
        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь.", reply_markup=get_main_menu_keyboard())
            return
        bookmarks = await db.execute(select(Bookmark).where(Bookmark.user_id == user.id).order_by(Bookmark.added_at.desc()))
        bookmarks = bookmarks.scalars().all()
        if not bookmarks:
            await message.answer(
                "⭐ **Ваши закладки**\n\nУ вас пока нет сохраненных материалов.\n\nЧтобы сохранить материал, нажмите кнопку '⭐ Сохранить' во время урока.",
                reply_markup=back_button("back_to_main")
            )
            return
        text = "⭐ **Ваши закладки**\n\n"
        for i, b in enumerate(bookmarks, 1):
            subcat = json_db.get_subcategory(b.subcategory_id)
            subcat_name = subcat['name'] if subcat else "Неизвестный курс"
            text += f"{i}. **{b.material_name}**\n   📚 Курс: {subcat_name}\n   📅 {b.added_at.strftime('%d.%m.%Y')}\n\n"
        await message.answer(text, reply_markup=back_button("back_to_main"))
        break
    
@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

@router.message(F.text == "❓ FAQ")
async def faq_handler(message: Message):
    """Часто задаваемые вопросы"""
    from utils.json_db import json_db
    
    faqs = json_db.get_faq()
    
    if not faqs:
        text = (
            "❓ **Часто задаваемые вопросы**\n\n"
            "**1. Как начать обучение?**\n"
            "   Нажмите '📚 Курсы', выберите категорию и подкатегорию.\n\n"
            "**2. Как работает система уровней?**\n"
            "   За прохождение уроков вы получаете XP. Чем больше XP, тем выше уровень.\n\n"
            "**3. Сколько стоят курсы?**\n"
            "   Все курсы абсолютно бесплатны!\n\n"
            "**4. Как связаться с администратором?**\n"
            "   Напишите @admin"
        )
    else:
        text = "❓ **Часто задаваемые вопросы**\n\n"
        for i, faq in enumerate(faqs, 1):
            text += f"**{i}. {faq.get('question', 'Вопрос')}**\n{faq.get('answer', 'Ответ')}\n\n"
    
    await message.answer(text, reply_markup=back_button("back_to_main"))

@router.message(F.text == "ℹ️ О боте")
async def about_handler(message: Message):
    """Информация о боте"""
    categories_count = len(json_db.get_categories())
    subcategories_count = len(json_db.get_subcategories())
    materials_count = len(json_db.get_materials())
    async for db in get_db():
        users_count = await db.execute(select(func.count(User.id)))
        users_count = users_count.scalar()
    tip = json_db.get_random_tip()
    text = (
        f"ℹ️ **О MentorAI Bot**\n\n"
        f"**Версия:** 2.0.0\n"
        f"**Описание:** Интерактивный бот для обучения\n\n"
        f"📊 **Статистика:**\n"
        f"• Категорий: {categories_count}\n"
        f"• Подкатегорий: {subcategories_count}\n"
        f"• Материалов: {materials_count}\n"
        f"• Пользователей: {users_count}\n\n"
        f"🎯 **Возможности:**\n"
        f"• Изучение материалов\n"
        f"• Отслеживание прогресса\n"
        f"• Система достижений\n"
        f"• Ежедневные советы\n\n"
        f"Разработано с ❤️\n\n"
        f"💡 **Совет дня:**\n{tip}"
    )
    await message.answer(text, reply_markup=back_button("back_to_main"))


@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.delete()
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
    await callback.answer()