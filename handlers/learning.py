from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from datetime import datetime
from database import get_db
from models import User, UserProgress, Bookmark  # <-- ДОБАВИЛИ Bookmark
from keyboards import (
    get_main_menu_keyboard,
    get_categories_keyboard,
    get_subcategories_keyboard,
    get_material_navigation_keyboard,
    back_button,
    get_continue_keyboard
)
from utils.json_db import json_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

@router.message(F.text == "📚 Курсы")
async def courses_handler(message: Message, state: FSMContext):
    """Показать категории курсов из JSON"""
    await state.clear()
    
    categories = json_db.get_categories()
    
    if not categories:
        await message.answer(
            "📚 Пока нет доступных курсов. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await message.answer(
        "📚 **Выберите категорию курсов:**",
        reply_markup=get_categories_keyboard(categories)
    )

@router.callback_query(F.data.startswith("cat_"))
async def category_selected(callback: CallbackQuery):
    """Выбрана категория"""
    cat_id = int(callback.data.split("_")[1])
    
    subcategories = json_db.get_subcategories(cat_id)
    
    if not subcategories:
        await callback.answer("В этой категории пока нет подкатегорий", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📂 **Выберите подкатегорию:**",
        reply_markup=get_subcategories_keyboard(subcategories)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("sub_"))
async def subcategory_selected(callback: CallbackQuery, state: FSMContext):
    """Выбрана подкатегория - проверяем прогресс"""
    sub_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    
    # Получаем материалы из JSON
    materials = json_db.get_materials(sub_id)
    materials = sorted(materials, key=lambda x: x['order_num'])
    
    if not materials:
        await callback.answer("В этой подкатегории пока нет материалов", show_alert=True)
        return
    
    # Проверяем прогресс в PostgreSQL
    async for db in get_db():
        user = await db.execute(select(User).where(User.tg_id == telegram_id))
        user = user.scalar_one_or_none()
        
        if not user:
            await callback.answer("Сначала зарегистрируйтесь", show_alert=True)
            return
        
        # Проверяем существующий прогресс
        progress = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.subcategory_id == sub_id
            )
        )
        progress = progress.scalar_one_or_none()
        
        if progress and progress.current_material_index > 0:
            # Есть прогресс - спрашиваем, хочет ли продолжить
            await state.update_data(
                current_subcategory=sub_id,
                current_index=progress.current_material_index,
                total_materials=len(materials)
            )
            
            subcat_info = json_db.get_subcategory(sub_id)
            subcat_name = subcat_info['name'] if subcat_info else "этот курс"
            
            await callback.message.edit_text(
                f"📚 **Вы уже начали курс '{subcat_name}'**\n\n"
                f"Вы остановились на уроке {progress.current_material_index + 1} из {len(materials)}.\n\n"
                f"Хотите продолжить или начать заново?",
                reply_markup=get_continue_keyboard(sub_id)
            )
        else:
            # Новый курс - начинаем с первого урока
            if not progress:
                # Создаем новый прогресс
                progress = UserProgress(
                    user_id=user.id,
                    subcategory_id=sub_id,
                    current_material_index=0,
                    completed_materials=[]
                )
                db.add(progress)
                await db.commit()
            
            await start_learning(callback.message, sub_id, 0, telegram_id)
        
        break
    
    await callback.answer()

@router.callback_query(F.data.startswith("continue_"))
async def continue_course(callback: CallbackQuery, state: FSMContext):
    """Продолжить обучение"""
    sub_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    
    data = await state.get_data()
    current_index = data.get('current_index', 0)
    
    await start_learning(callback.message, sub_id, current_index, telegram_id)
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith("restart_"))
async def restart_course(callback: CallbackQuery, state: FSMContext):
    """Начать курс заново"""
    sub_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    
    # Сбрасываем прогресс
    async for db in get_db():
        user = await db.execute(select(User).where(User.tg_id == telegram_id))
        user = user.scalar_one()
        
        progress = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.subcategory_id == sub_id
            )
        )
        progress = progress.scalar_one()
        progress.current_material_index = 0
        progress.completed_materials = []
        await db.commit()
    
    await start_learning(callback.message, sub_id, 0, telegram_id)
    await callback.message.delete()
    await callback.answer()

async def start_learning(message, sub_id, start_index, telegram_id):
    """Начать обучение с указанного урока"""
    materials = json_db.get_materials(sub_id)
    materials = sorted(materials, key=lambda x: x['order_num'])
    
    await show_material(message, materials[start_index], start_index, len(materials), sub_id, telegram_id)

async def show_material(message, material, current_index, total, sub_id, telegram_id):
    """Показать материал урока"""
    # Сохраняем прогресс в БД
    async for db in get_db():
        user = await db.execute(select(User).where(User.tg_id == telegram_id))
        user = user.scalar_one()
        
        progress = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.subcategory_id == sub_id
            )
        )
        progress = progress.scalar_one()
        progress.current_material_index = current_index
        progress.last_accessed = datetime.utcnow()
        await db.commit()
    
    # Отправляем материал в зависимости от типа
    if material['content_type'] == "text":
        text = f"**{material['name']}**\n\n"
        if material.get('description'):
            text += f"*{material['description']}*\n\n"
        text += material['content'].get('text', '')
        
        await message.answer(
            text,
            reply_markup=get_material_navigation_keyboard(current_index, total, sub_id, material['id'])
        )
    
    elif material['content_type'] == "photo":
        caption = f"**{material['name']}**\n\n"
        if material.get('description'):
            caption += material['description']
        
        await message.answer_photo(
            photo=material['content'].get('file_id'),
            caption=caption,
            reply_markup=get_material_navigation_keyboard(current_index, total, sub_id, material['id'])
        )
    
    elif material['content_type'] == "video":
        caption = f"**{material['name']}**\n\n"
        if material.get('description'):
            caption += material['description']
        
        await message.answer_video(
            video=material['content'].get('file_id'),
            caption=caption,
            reply_markup=get_material_navigation_keyboard(current_index, total, sub_id, material['id'])
        )
    
    elif material['content_type'] == "document":
        caption = f"**{material['name']}**\n\n"
        if material.get('description'):
            caption += material['description']
        
        await message.answer_document(
            document=material['content'].get('file_id'),
            caption=caption,
            reply_markup=get_material_navigation_keyboard(current_index, total, sub_id, material['id'])
        )
    
    elif material['content_type'] == "youtube":
        text = f"**{material['name']}**\n\n"
        if material.get('description'):
            text += f"*{material['description']}*\n\n"
        text += f"🎬 **Ссылка на видео:**\n{material['content'].get('url', '')}"
        
        await message.answer(
            text,
            reply_markup=get_material_navigation_keyboard(current_index, total, sub_id, material['id'])
        )

@router.callback_query(F.data.startswith("next_"))
async def next_material(callback: CallbackQuery, state: FSMContext):
    """Следующий материал"""
    parts = callback.data.split("_")
    sub_id = int(parts[1])
    current = int(parts[2])
    telegram_id = callback.from_user.id
    
    materials = json_db.get_materials(sub_id)
    materials = sorted(materials, key=lambda x: x['order_num'])
    
    if current + 1 >= len(materials):
        # Последний урок - показываем сообщение о завершении
        await callback.message.edit_text(
            "🎉 **Поздравляем! Вы прошли все уроки!**\n\n"
            "Скоро здесь будет тест для проверки знаний.",
            reply_markup=back_button("back_to_categories")
        )
        await callback.answer()
        return
    
    await callback.message.delete()
    await show_material(callback.message, materials[current + 1], current + 1, len(materials), sub_id, telegram_id)
    await callback.answer()

@router.callback_query(F.data.startswith("prev_"))
async def prev_material(callback: CallbackQuery, state: FSMContext):
    """Предыдущий материал"""
    parts = callback.data.split("_")
    sub_id = int(parts[1])
    current = int(parts[2])
    telegram_id = callback.from_user.id
    
    if current <= 0:
        await callback.answer("Это первый урок", show_alert=True)
        return
    
    materials = json_db.get_materials(sub_id)
    materials = sorted(materials, key=lambda x: x['order_num'])
    
    await callback.message.delete()
    await show_material(callback.message, materials[current - 1], current - 1, len(materials), sub_id, telegram_id)
    await callback.answer()

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery):
    """Назад к категориям"""
    categories = json_db.get_categories()
    
    await callback.message.edit_text(
        "📚 **Выберите категорию курсов:**",
        reply_markup=get_categories_keyboard(categories)
    )
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Назад в главное меню"""
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("save_"))
async def save_material(callback: CallbackQuery):
    """Сохранить материал в закладки"""
    material_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    
    # Получаем информацию о материале из JSON
    material = json_db.get_material(material_id)
    if not material:
        await callback.answer("❌ Материал не найден", show_alert=True)
        return
    
    async for db in get_db():
        try:
            # Получаем пользователя
            user = await db.execute(select(User).where(User.tg_id == telegram_id))
            user = user.scalar_one()
            
            # Проверяем, не сохранен ли уже этот материал
            from models import Bookmark
            existing = await db.execute(
                select(Bookmark).where(
                    Bookmark.user_id == user.id,
                    Bookmark.material_id == material_id
                )
            )
            if existing.scalar_one_or_none():
                await callback.answer("❌ Этот материал уже в закладках", show_alert=True)
                return
            
            # Создаем закладку
            bookmark = Bookmark(
                user_id=user.id,
                material_id=material_id,
                subcategory_id=material['subcategory_id'],
                material_name=material['name']
            )
            db.add(bookmark)
            await db.commit()
            
            await callback.answer("⭐ Материал сохранен в закладки!", show_alert=True)
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении в закладки: {e}")
            await callback.answer("❌ Ошибка при сохранении", show_alert=True)

@router.callback_query(F.data.startswith("rate_"))
async def rate_course(callback: CallbackQuery):
    """Оценить курс"""
    parts = callback.data.split("_")
    sub_id = int(parts[1])
    stars = int(parts[2])
    telegram_id = callback.from_user.id
    
    # Сохраняем оценку в PostgreSQL
    async for db in get_db():
        user = await db.execute(select(User).where(User.tg_id == telegram_id))
        user = user.scalar_one()
        
        # Здесь можно создать модель UserRating если нужно
        # Пока просто сохраняем в прогресс
        progress = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.subcategory_id == sub_id
            )
        )
        progress = progress.scalar_one()
        # Можно добавить поле rating в модель UserProgress
        await db.commit()
    
    await callback.answer(f"Спасибо за оценку {stars} ⭐!", show_alert=True)