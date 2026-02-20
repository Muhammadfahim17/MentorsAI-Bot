from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
import asyncio
import re
from keyboards import (
    get_main_menu_keyboard,
    get_admin_reply_keyboard,
    get_cancel_keyboard,
    back_button,
    get_categories_inline,
    get_subcategories_inline,
    get_content_type_keyboard,
    get_confirm_keyboard_admin,
    get_sponsors_inline,
    get_broadcast_keyboard
)
from database import get_db
from models import User, Sponsor, Broadcast, UserProgress, Bookmark
from config import Config
from utils.json_db import json_db
from utils.helpers import is_valid_url
import logging

logger = logging.getLogger(__name__)

router = Router()

class AdminStates(StatesGroup):
    # Категории
    waiting_category_name = State()
    waiting_delete_category = State()
    # Подкатегории
    waiting_subcategory_category = State()
    waiting_subcategory_name = State()
    waiting_subcategory_wiki = State()
    waiting_subcategory_pros = State()
    waiting_subcategory_cons = State()
    waiting_delete_subcategory = State()
    # Материалы
    waiting_material_category = State()
    waiting_material_subcategory = State()
    waiting_material_name = State()
    waiting_material_description = State()
    waiting_material_content_type = State()
    waiting_material_content = State()
    waiting_material_confirm = State()
    waiting_delete_material = State()
    # Спонсоры
    waiting_sponsor_name = State()
    waiting_sponsor_url = State()
    waiting_delete_sponsor = State()
    # Рассылка
    waiting_broadcast_name = State()
    waiting_broadcast_description = State()
    waiting_broadcast_content_type = State()
    waiting_broadcast_content = State()
    waiting_broadcast_button_text = State()
    waiting_broadcast_button_url = State()
    waiting_broadcast_confirm = State()

def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS

async def ensure_admin_mode(state: FSMContext, message: Message) -> bool:
    """Проверяет и восстанавливает админ-режим"""
    data = await state.get_data()
    if not data.get('is_admin_mode', False):
        await state.set_data({"is_admin_mode": True})
        await message.answer(
            "⚠️ Сессия администратора восстановлена.",
            reply_markup=get_admin_reply_keyboard()
        )
        return False
    return True

@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    await state.clear()
    await state.set_data({"is_admin_mode": True})
    await message.answer(
        "👑 **Добро пожаловать в админ-панель!**\n\nВыберите действие:",
        reply_markup=get_admin_reply_keyboard()
    )

@router.message(F.text == "🚪 Выход")
async def admin_exit(message: Message, state: FSMContext):
    """Выход из админ-панели в меню пользователя"""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    await message.answer(
        "👋 Вы вышли из админ-панели.\n"
        "Возвращаю главное меню:",
        reply_markup=get_main_menu_keyboard()
    )

# ==================== ИСПРАВЛЕННЫЙ ХЕНДЛЕР ОТМЕНЫ ====================
@router.message(F.text == "❌ Отмена")
@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(message_or_callback, state: FSMContext):
    """Отмена действия - ВСЕГДА возвращает в админ-меню"""
    
    # Определяем, что пришло: Message или CallbackQuery
    if isinstance(message_or_callback, Message):
        user_id = message_or_callback.from_user.id
        message = message_or_callback
    else:
        user_id = message_or_callback.from_user.id
        # Удаляем сообщение с инлайн-клавиатурой
        await message_or_callback.message.delete()
        message = message_or_callback.message
    
    # Проверяем, админ ли это
    if not is_admin(user_id):
        return
    
    # Полностью очищаем состояние
    await state.clear()
    
    # ПРИНУДИТЕЛЬНО устанавливаем флаг админ-режима
    await state.set_data({"is_admin_mode": True})
    
    # Отправляем новое сообщение с админ-клавиатурой
    await message.answer(
        "❌ Действие отменено. Вы в админ-панели.",
        reply_markup=get_admin_reply_keyboard()
    )
    
    # Если это был callback, отвечаем на него
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer()

# ---------- КАТЕГОРИИ ----------
@router.message(F.text == "📁 Добавить категорию")
async def admin_add_category(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    await state.set_state(AdminStates.waiting_category_name)
    await message.answer("📁 Введите название категории:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_category_name)
async def admin_process_category_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Слишком короткое название. Попробуйте снова:", reply_markup=get_cancel_keyboard())
        return
    
    categories = json_db.get_categories()
    if any(c['name'].lower() == name.lower() for c in categories):
        await message.answer("❌ Такая категория уже существует. Введите другое название:", reply_markup=get_cancel_keyboard())
        return
    
    new_cat = json_db.add_category(name)
    await message.answer(f"✅ Категория добавлена! ID: {new_cat['id']}", reply_markup=get_admin_reply_keyboard())
    await state.clear()
    await state.set_data({"is_admin_mode": True})

@router.message(F.text == "🗑 Удалить категорию")
async def admin_delete_category_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    categories = json_db.get_categories()
    if not categories:
        await message.answer("❌ Нет категорий для удаления.", reply_markup=get_admin_reply_keyboard())
        return
    await message.answer("Выберите категорию для удаления:", reply_markup=get_categories_inline(categories, "del_cat"))
    await state.set_state(AdminStates.waiting_delete_category)

@router.callback_query(AdminStates.waiting_delete_category, F.data.startswith("del_cat_"))
async def admin_delete_category_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    cat_id = int(callback.data.split("_")[2])
    if json_db.delete_category(cat_id):
        await callback.message.edit_text("✅ Категория удалена.")
    else:
        await callback.message.edit_text("❌ Категория не найдена.")
    await state.clear()
    await state.set_data({"is_admin_mode": True})
    await callback.message.answer("Выберите следующее действие:", reply_markup=get_admin_reply_keyboard())
    await callback.answer()

# ---------- ПОДКАТЕГОРИИ ----------
@router.message(F.text == "📂 Добавить подкатегорию")
async def admin_add_subcategory(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    categories = json_db.get_categories()
    if not categories:
        await message.answer("❌ Сначала создайте категорию.", reply_markup=get_admin_reply_keyboard())
        return
    
    await message.answer("Выберите категорию:", reply_markup=get_categories_inline(categories, "subcat"))
    await state.set_state(AdminStates.waiting_subcategory_category)

@router.callback_query(AdminStates.waiting_subcategory_category, F.data.startswith("subcat_"))
async def admin_process_subcategory_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    cat_id = int(callback.data.split("_")[1])
    await state.update_data(category_id=cat_id)
    await state.set_state(AdminStates.waiting_subcategory_name)
    await callback.message.edit_text("Введите название подкатегории:")
    await callback.answer()

@router.message(AdminStates.waiting_subcategory_name)
async def admin_process_subcategory_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Слишком короткое название. Попробуйте снова:", reply_markup=get_cancel_keyboard())
        return
    
    await state.update_data(subcategory_name=name)
    await state.set_state(AdminStates.waiting_subcategory_wiki)
    await message.answer("Введите wiki-текст (или '-' для пропуска):", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_subcategory_wiki)
async def admin_process_subcategory_wiki(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    wiki = message.text.strip()
    await state.update_data(wiki=None if wiki == '-' else wiki)
    await state.set_state(AdminStates.waiting_subcategory_pros)
    await message.answer("Введите плюсы (или '-' для пропуска):", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_subcategory_pros)
async def admin_process_subcategory_pros(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    pros = message.text.strip()
    await state.update_data(pros=None if pros == '-' else pros)
    await state.set_state(AdminStates.waiting_subcategory_cons)
    await message.answer("Введите минусы (или '-' для пропуска):", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_subcategory_cons)
async def admin_process_subcategory_cons(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    cons = message.text.strip()
    if cons == '-':
        cons = None
    
    data = await state.get_data()
    new_sub = json_db.add_subcategory(
        category_id=data['category_id'],
        name=data['subcategory_name'],
        wiki_text=data.get('wiki'),
        pros=data.get('pros'),
        cons=cons
    )
    await message.answer(f"✅ Подкатегория добавлена! ID: {new_sub['id']}", reply_markup=get_admin_reply_keyboard())
    await state.clear()
    await state.set_data({"is_admin_mode": True})

@router.message(F.text == "🗑 Удалить подкатегорию")
async def admin_delete_subcategory_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    categories = json_db.get_categories()
    if not categories:
        await message.answer("❌ Нет категорий.", reply_markup=get_admin_reply_keyboard())
        return
    await message.answer("Выберите категорию:", reply_markup=get_categories_inline(categories, "del_sub_cat"))
    await state.set_state(AdminStates.waiting_delete_subcategory)

@router.callback_query(AdminStates.waiting_delete_subcategory, F.data.startswith("del_sub_cat_"))
async def admin_delete_subcategory_choose(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    cat_id = int(callback.data.split("_")[3])
    subcats = json_db.get_subcategories(cat_id)
    if not subcats:
        await callback.message.edit_text("❌ В этой категории нет подкатегорий.", reply_markup=back_button("admin_cancel"))
        return
    await callback.message.edit_text("Выберите подкатегорию:", reply_markup=get_subcategories_inline(subcats, "del_sub"))
    await callback.answer()

@router.callback_query(AdminStates.waiting_delete_subcategory, F.data.startswith("del_sub_"))
async def admin_delete_subcategory_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    sub_id = int(callback.data.split("_")[2])
    if json_db.delete_subcategory(sub_id):
        await callback.message.edit_text("✅ Подкатегория удалена.")
    else:
        await callback.message.edit_text("❌ Подкатегория не найдена.")
    await state.clear()
    await state.set_data({"is_admin_mode": True})
    await callback.message.answer("Выберите следующее действие:", reply_markup=get_admin_reply_keyboard())
    await callback.answer()

# ---------- МАТЕРИАЛЫ ----------
@router.message(F.text == "📎 Добавить материал")
async def admin_add_material(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    categories = json_db.get_categories()
    if not categories:
        await message.answer("❌ Сначала создайте категории.", reply_markup=get_admin_reply_keyboard())
        return
    await message.answer("Выберите категорию:", reply_markup=get_categories_inline(categories, "material_cat"))
    await state.set_state(AdminStates.waiting_material_category)

@router.callback_query(AdminStates.waiting_material_category, F.data.startswith("material_cat_"))
async def admin_material_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    cat_id = int(callback.data.split("_")[2])
    await state.update_data(category_id=cat_id)
    subcats = json_db.get_subcategories(cat_id)
    if not subcats:
        await callback.message.edit_text("❌ В этой категории нет подкатегорий.", reply_markup=back_button("admin_cancel"))
        return
    await callback.message.edit_text("Выберите подкатегорию:", reply_markup=get_subcategories_inline(subcats, "material_sub"))
    await state.set_state(AdminStates.waiting_material_subcategory)
    await callback.answer()

@router.callback_query(AdminStates.waiting_material_subcategory, F.data.startswith("material_sub_"))
async def admin_material_subcategory(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    sub_id = int(callback.data.split("_")[2])
    await state.update_data(subcategory_id=sub_id)
    max_order = json_db.get_max_order(sub_id)
    await state.update_data(order_num=max_order + 1)
    await state.set_state(AdminStates.waiting_material_name)
    await callback.message.edit_text("Введите название материала:")
    await callback.answer()

@router.message(AdminStates.waiting_material_name)
async def admin_material_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Слишком короткое название. Попробуйте снова:", reply_markup=get_cancel_keyboard())
        return
    await state.update_data(material_name=name)
    await state.set_state(AdminStates.waiting_material_description)
    await message.answer("Введите описание (или '-' для пропуска):", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_material_description)
async def admin_material_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    desc = message.text.strip()
    await state.update_data(material_description=None if desc == '-' else desc)
    await state.set_state(AdminStates.waiting_material_content_type)
    await message.answer("Выберите тип контента:", reply_markup=get_content_type_keyboard())

@router.callback_query(AdminStates.waiting_material_content_type, F.data.startswith("ctype_"))
async def admin_material_content_type(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    ctype = callback.data.split("_")[1]
    await state.update_data(content_type=ctype)
    await state.set_state(AdminStates.waiting_material_content)
    instructions = {
        "text": "✏️ Отправьте текст материала:",
        "photo": "📸 Отправьте фото:",
        "video": "🎥 Отправьте видео:",
        "document": "📄 Отправьте документ:",
        "youtube": "🔗 Отправьте ссылку на YouTube:"
    }
    await callback.message.edit_text(instructions[ctype])
    await callback.answer()

@router.message(AdminStates.waiting_material_content)
async def admin_material_content(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    data = await state.get_data()
    content_type = data['content_type']
    content = {}
    
    if content_type == "text":
        content['text'] = message.text or message.caption
        if not content['text']:
            await message.answer("❌ Отправьте текст!", reply_markup=get_cancel_keyboard())
            return
    elif content_type == "photo":
        if not message.photo:
            await message.answer("❌ Отправьте фото!", reply_markup=get_cancel_keyboard())
            return
        content['file_id'] = message.photo[-1].file_id
        content['caption'] = message.caption
    elif content_type == "video":
        if not message.video:
            await message.answer("❌ Отправьте видео!", reply_markup=get_cancel_keyboard())
            return
        content['file_id'] = message.video.file_id
        content['caption'] = message.caption
    elif content_type == "document":
        if not message.document:
            await message.answer("❌ Отправьте документ!", reply_markup=get_cancel_keyboard())
            return
        content['file_id'] = message.document.file_id
        content['caption'] = message.caption
    elif content_type == "youtube":
        url = message.text or message.caption
        if not url or ("youtube.com" not in url and "youtu.be" not in url):
            await message.answer("❌ Отправьте корректную YouTube ссылку!", reply_markup=get_cancel_keyboard())
            return
        content['url'] = url
    
    await state.update_data(content=content)
    await state.set_state(AdminStates.waiting_material_confirm)
    
    preview = (
        f"📎 **Предпросмотр**\n\n"
        f"Название: {data['material_name']}\n"
        f"Описание: {data.get('material_description', '—')}\n"
        f"Порядок: {data['order_num']}\n"
        f"Тип: {content_type}\n\n"
        f"Сохранить?"
    )
    await message.answer(preview, reply_markup=get_confirm_keyboard_admin("material"))

@router.callback_query(AdminStates.waiting_material_confirm, F.data == "confirm_material")
async def admin_material_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    data = await state.get_data()
    new_material = json_db.add_material(
        subcategory_id=data['subcategory_id'],
        order_num=data['order_num'],
        name=data['material_name'],
        description=data.get('material_description'),
        content_type=data['content_type'],
        content=data['content']
    )
    await callback.message.edit_text(f"✅ Материал добавлен! ID: {new_material['id']}")
    await callback.message.answer("Выберите следующее действие:", reply_markup=get_admin_reply_keyboard())
    await state.clear()
    await state.set_data({"is_admin_mode": True})
    await callback.answer()

@router.callback_query(AdminStates.waiting_material_confirm, F.data == "cancel_material")
async def admin_material_cancel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    await state.clear()
    await state.set_data({"is_admin_mode": True})
    await callback.message.edit_text("❌ Добавление отменено.")
    await callback.message.answer("Выберите следующее действие:", reply_markup=get_admin_reply_keyboard())
    await callback.answer()

@router.message(F.text == "🗑 Удалить материал")
async def admin_delete_material_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    categories = json_db.get_categories()
    if not categories:
        await message.answer("❌ Нет категорий.", reply_markup=get_admin_reply_keyboard())
        return
    await message.answer("Выберите категорию:", reply_markup=get_categories_inline(categories, "del_mat_cat"))
    await state.set_state(AdminStates.waiting_delete_material)

@router.callback_query(AdminStates.waiting_delete_material, F.data.startswith("del_mat_cat_"))
async def admin_delete_material_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    cat_id = int(callback.data.split("_")[3])
    subcats = json_db.get_subcategories(cat_id)
    if not subcats:
        await callback.message.edit_text("❌ В этой категории нет подкатегорий.", reply_markup=back_button("admin_cancel"))
        return
    await callback.message.edit_text("Выберите подкатегорию:", reply_markup=get_subcategories_inline(subcats, "del_mat_sub"))
    await callback.answer()

@router.callback_query(AdminStates.waiting_delete_material, F.data.startswith("del_mat_sub_"))
async def admin_delete_material_subcategory(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    sub_id = int(callback.data.split("_")[3])
    materials = json_db.get_materials(sub_id)
    if not materials:
        await callback.message.edit_text("❌ В этой подкатегории нет материалов.", reply_markup=back_button("admin_cancel"))
        return
    
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    for m in materials:
        builder.add(InlineKeyboardButton(text=f"{m['order_num']}. {m['name']}", callback_data=f"del_mat_{m['id']}"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    builder.adjust(1)
    
    await callback.message.edit_text("Выберите материал для удаления:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(AdminStates.waiting_delete_material, F.data.startswith("del_mat_"))
async def admin_delete_material_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    material_id = int(callback.data.split("_")[2])
    if json_db.delete_material(material_id):
        await callback.message.edit_text("✅ Материал удален.")
    else:
        await callback.message.edit_text("❌ Материал не найден.")
    await state.clear()
    await state.set_data({"is_admin_mode": True})
    await callback.message.answer("Выберите следующее действие:", reply_markup=get_admin_reply_keyboard())
    await callback.answer()

# ---------- СПОНСОРЫ ----------
@router.message(F.text == "🔗 Добавить спонсора")
async def admin_add_sponsor(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    await state.set_state(AdminStates.waiting_sponsor_name)
    await message.answer(
        "🔗 **Добавление спонсора**\n\n"
        "Введите название спонсора (канала/бота):",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_sponsor_name)
async def admin_sponsor_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    name = message.text.strip()
    if len(name) < 2:
        await message.answer(
            "❌ Слишком короткое название. Попробуйте снова:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(sponsor_name=name)
    await state.set_state(AdminStates.waiting_sponsor_url)
    await message.answer(
        "🔗 Теперь отправьте ссылку на спонсора.\n"
        "Примеры:\n"
        "• https://t.me/channel_name\n"
        "• https://t.me/bot_name",
        reply_markup=get_cancel_keyboard()
    )

@router.message(AdminStates.waiting_sponsor_url)
async def admin_sponsor_url(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    url = message.text.strip()
    
    # Проверка ссылки
    if not (url.startswith("https://t.me/") or url.startswith("http://t.me/") or url.startswith("t.me/")):
        await message.answer(
            "❌ Ссылка должна быть на Telegram канал или бота.\n"
            "Пример: https://t.me/channel_name\n"
            "Попробуйте снова:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Приводим к единому формату
    if not url.startswith("http"):
        url = "https://" + url
    
    data = await state.get_data()
    name = data['sponsor_name']
    
    async for db in get_db():
        sponsor = Sponsor(
            name=name,
            url=url,
            is_active=True
        )
        db.add(sponsor)
        await db.commit()
        
        await message.answer(
            f"✅ **Спонсор успешно добавлен!**\n\n"
            f"📢 Название: {name}\n"
            f"🔗 Ссылка: {url}",
            reply_markup=get_admin_reply_keyboard()
        )
        break
    
    await state.clear()
    await state.set_data({"is_admin_mode": True})

@router.message(F.text == "❌ Удалить спонсора")
async def admin_delete_sponsor(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    async for db in get_db():
        sponsors = await db.execute(select(Sponsor))
        sponsors = sponsors.scalars().all()
        if not sponsors:
            await message.answer("❌ Нет спонсоров.", reply_markup=get_admin_reply_keyboard())
            return
        await message.answer("Выберите спонсора:", reply_markup=get_sponsors_inline(sponsors, "delete"))
        await state.set_state(AdminStates.waiting_delete_sponsor)
        break

@router.callback_query(AdminStates.waiting_delete_sponsor, F.data.startswith("del_sponsor_"))
async def admin_delete_sponsor_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    sponsor_id = int(callback.data.split("_")[2])
    async for db in get_db():
        sponsor = await db.get(Sponsor, sponsor_id)
        if sponsor:
            await db.delete(sponsor)
            await db.commit()
            await callback.message.edit_text(f"✅ Спонсор {sponsor.name} удален.")
        else:
            await callback.message.edit_text("❌ Спонсор не найден.")
        break
    await state.clear()
    await state.set_data({"is_admin_mode": True})
    await callback.message.answer("Выберите следующее действие:", reply_markup=get_admin_reply_keyboard())
    await callback.answer()

# ---------- СТАТИСТИКА ----------
@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message, state: FSMContext):
    """Показать статистику бота"""
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    # Отправляем сообщение о загрузке
    loading_msg = await message.answer("⏳ Загружаю статистику...")
    
    async for db in get_db():
        try:
            # Основная статистика из PostgreSQL
            users_count = await db.execute(select(func.count(User.id)))
            users_count = users_count.scalar() or 0
            
            today = datetime.now().date()
            today_users = await db.execute(
                select(func.count(User.id)).where(func.date(User.last_active) == today)
            )
            today_users = today_users.scalar() or 0
            
            week_ago = datetime.now() - timedelta(days=7)
            week_users = await db.execute(
                select(func.count(User.id)).where(User.last_active >= week_ago)
            )
            week_users = week_users.scalar() or 0
            
            sponsors_count = await db.execute(select(func.count(Sponsor.id)))
            sponsors_count = sponsors_count.scalar() or 0
            
            broadcasts_count = await db.execute(select(func.count(Broadcast.id)))
            broadcasts_count = broadcasts_count.scalar() or 0
            
            # Статистика из JSON
            categories = json_db.get_categories()
            categories_count = len(categories)
            
            subcategories_count = 0
            for cat in categories:
                subcategories_count += len(json_db.get_subcategories(cat['id']))
            
            materials_count = len(json_db.get_materials())
            
            # Активные ученики (уникальные пользователи, у которых есть прогресс)
            active_learners = await db.execute(
                select(func.count(func.distinct(UserProgress.user_id)))
            )
            active_learners = active_learners.scalar() or 0
            
            # Общее количество закладок
            bookmarks_count = await db.execute(select(func.count(Bookmark.id)))
            bookmarks_count = bookmarks_count.scalar() or 0
            
            # Средний XP на пользователя
            avg_xp = await db.execute(select(func.avg(User.xp)))
            avg_xp = avg_xp.scalar() or 0
            
            stats_text = (
                f"📊 **СТАТИСТИКА БОТА**\n\n"
                f"👥 **Пользователи (PostgreSQL):**\n"
                f"• Всего: {users_count}\n"
                f"• Активных сегодня: {today_users}\n"
                f"• Активных за неделю: {week_users}\n"
                f"• Средний XP: {avg_xp:.1f}\n\n"
                
                f"📚 **Контент (JSON):**\n"
                f"• Категорий: {categories_count}\n"
                f"• Подкатегорий: {subcategories_count}\n"
                f"• Материалов: {materials_count}\n"
                f"• Активных учеников: {active_learners}\n"
                f"• Закладок: {bookmarks_count}\n\n"
                
                f"🔗 **Спонсоров:** {sponsors_count}\n"
                f"📨 **Рассылок:** {broadcasts_count}\n\n"
                f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Удаляем сообщение о загрузке
            await loading_msg.delete()
            
            await message.answer(stats_text, reply_markup=get_admin_reply_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка в статистике: {e}")
            await loading_msg.delete()
            await message.answer(
                f"❌ Ошибка при загрузке статистики: {str(e)}",
                reply_markup=get_admin_reply_keyboard()
            )
        break

# ---------- ТОП-10 ----------
@router.message(F.text == "🏆 ТОП-10 (админ)")
async def admin_top10(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    async for db in get_db():
        top_users = await db.execute(
            select(User).order_by(User.xp.desc()).limit(10)
        )
        top_users = top_users.scalars().all()
        
        if not top_users:
            await message.answer("🏆 Пока нет данных.", reply_markup=get_admin_reply_keyboard())
            return
        
        text = "🏆 **ТОП-10 ПОЛЬЗОВАТЕЛЕЙ**\n\n"
        for i, user in enumerate(top_users, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
            
            # Получаем количество пройденных материалов
            progress_count = await db.execute(
                select(func.count(UserProgress.id)).where(UserProgress.user_id == user.id)
            )
            progress_count = progress_count.scalar() or 0
            
            text += f"{medal} {i}. {user.name} (ID: {user.tg_id})\n"
            text += f"   ├ XP: {user.xp}\n"
            text += f"   └ Материалов: {progress_count}\n\n"
        
        await message.answer(text, reply_markup=get_admin_reply_keyboard())
        break

# ---------- РАССЫЛКА ----------
@router.message(F.text == "📨 Рассылка")
async def admin_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    await state.set_state(AdminStates.waiting_broadcast_name)
    await message.answer("Введите название рассылки:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_broadcast_name)
async def admin_broadcast_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Слишком короткое название. Попробуйте снова:", reply_markup=get_cancel_keyboard())
        return
    
    await state.update_data(broadcast_name=name)
    await state.set_state(AdminStates.waiting_broadcast_description)
    await message.answer("Введите описание (или '-' для пропуска):", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_broadcast_description)
async def admin_broadcast_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    desc = message.text.strip()
    await state.update_data(broadcast_description=None if desc == '-' else desc)
    await state.set_state(AdminStates.waiting_broadcast_content_type)
    await message.answer("Выберите тип контента:", reply_markup=get_content_type_keyboard())

@router.callback_query(AdminStates.waiting_broadcast_content_type, F.data.startswith("ctype_"))
async def admin_broadcast_content_type(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    ctype = callback.data.split("_")[1]
    if ctype == "youtube":
        await callback.answer("YouTube не поддерживается для рассылки", show_alert=True)
        return
    
    await state.update_data(broadcast_content_type=ctype)
    await state.set_state(AdminStates.waiting_broadcast_content)
    
    instructions = {
        "text": "✏️ Отправьте текст для рассылки:",
        "photo": "📸 Отправьте фото:",
        "video": "🎥 Отправьте видео:",
        "document": "📄 Отправьте документ:"
    }
    await callback.message.edit_text(instructions[ctype])
    await callback.answer()

@router.message(AdminStates.waiting_broadcast_content)
async def admin_broadcast_content(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    data = await state.get_data()
    ctype = data['broadcast_content_type']
    content = {}
    
    if ctype == "text":
        content['text'] = message.text or message.caption
        if not content['text']:
            await message.answer("❌ Отправьте текст!", reply_markup=get_cancel_keyboard())
            return
    elif ctype == "photo":
        if not message.photo:
            await message.answer("❌ Отправьте фото!", reply_markup=get_cancel_keyboard())
            return
        content['file_id'] = message.photo[-1].file_id
        content['caption'] = message.caption
    elif ctype == "video":
        if not message.video:
            await message.answer("❌ Отправьте видео!", reply_markup=get_cancel_keyboard())
            return
        content['file_id'] = message.video.file_id
        content['caption'] = message.caption
    elif ctype == "document":
        if not message.document:
            await message.answer("❌ Отправьте документ!", reply_markup=get_cancel_keyboard())
            return
        content['file_id'] = message.document.file_id
        content['caption'] = message.caption
    
    await state.update_data(broadcast_content=content)
    await state.set_state(AdminStates.waiting_broadcast_button_text)
    await message.answer("Введите текст кнопки (или '-' для пропуска):", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_broadcast_button_text)
async def admin_broadcast_button_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    button_text = message.text.strip()
    if button_text == '-':
        await state.update_data(button_text=None, button_url=None)
        await admin_broadcast_confirm(message, state)
        return
    
    await state.update_data(button_text=button_text)
    await state.set_state(AdminStates.waiting_broadcast_button_url)
    await message.answer("Отправьте ссылку для кнопки:", reply_markup=get_cancel_keyboard())

@router.message(AdminStates.waiting_broadcast_button_url)
async def admin_broadcast_button_url(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not await ensure_admin_mode(state, message):
        return
    
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("t.me/")):
        await message.answer("❌ Некорректная ссылка. Попробуйте снова:", reply_markup=get_cancel_keyboard())
        return
    
    if url.startswith("t.me/"):
        url = "https://" + url
    
    await state.update_data(button_url=url)
    await admin_broadcast_confirm(message, state)

async def admin_broadcast_confirm(message: Message, state: FSMContext):
    """Показывает предпросмотр рассылки и запрашивает подтверждение"""
    data = await state.get_data()
    
    preview = (
        f"📨 **Предпросмотр рассылки**\n\n"
        f"📌 Название: {data['broadcast_name']}\n"
        f"📝 Описание: {data.get('broadcast_description', '—')}\n"
        f"📎 Тип: {data['broadcast_content_type']}\n"
    )
    
    if data.get('button_text'):
        preview += f"🔘 Кнопка: {data['button_text']} → {data['button_url']}\n"
    
    preview += "\nОтправить всем пользователям?"
    
    await message.answer(preview, reply_markup=get_confirm_keyboard_admin("broadcast"))
    await state.set_state(AdminStates.waiting_broadcast_confirm)

@router.callback_query(AdminStates.waiting_broadcast_confirm, F.data == "confirm_broadcast")
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    data = await state.get_data()
    await callback.message.edit_text("📨 Рассылка началась...")
    
    async for db in get_db():
        users = await db.execute(select(User))
        users = users.scalars().all()
        
        # Сохраняем рассылку в БД
        broadcast = Broadcast(
            name=data['broadcast_name'],
            description=data.get('broadcast_description'),
            content_type=data['broadcast_content_type'],
            content=data['broadcast_content'],
            button_text=data.get('button_text'),
            button_url=data.get('button_url')
        )
        db.add(broadcast)
        await db.commit()
        
        sent = 0
        failed = 0
        broadcast_name = data['broadcast_name']
        broadcast_desc = data.get('broadcast_description', '')
        
        for user in users:
            try:
                if data['broadcast_content_type'] == "text":
                    text = data['broadcast_content']['text']
                    full_text = f"📢 <b>{broadcast_name}</b>\n\n{broadcast_desc}\n\n{text}"
                    await callback.bot.send_message(
                        user.tg_id, 
                        full_text, 
                        parse_mode="HTML", 
                        reply_markup=get_broadcast_keyboard(data) if data.get('button_text') else None
                    )
                elif data['broadcast_content_type'] == "photo":
                    caption = f"📢 <b>{broadcast_name}</b>\n\n{broadcast_desc}"
                    await callback.bot.send_photo(
                        user.tg_id, 
                        data['broadcast_content']['file_id'], 
                        caption=caption, 
                        parse_mode="HTML", 
                        reply_markup=get_broadcast_keyboard(data) if data.get('button_text') else None
                    )
                elif data['broadcast_content_type'] == "video":
                    caption = f"📢 <b>{broadcast_name}</b>\n\n{broadcast_desc}"
                    await callback.bot.send_video(
                        user.tg_id, 
                        data['broadcast_content']['file_id'], 
                        caption=caption, 
                        parse_mode="HTML", 
                        reply_markup=get_broadcast_keyboard(data) if data.get('button_text') else None
                    )
                elif data['broadcast_content_type'] == "document":
                    caption = f"📢 <b>{broadcast_name}</b>\n\n{broadcast_desc}"
                    await callback.bot.send_document(
                        user.tg_id, 
                        data['broadcast_content']['file_id'], 
                        caption=caption, 
                        parse_mode="HTML", 
                        reply_markup=get_broadcast_keyboard(data) if data.get('button_text') else None
                    )
                sent += 1
                await asyncio.sleep(0.05)  # Защита от флуда
            except Exception as e:
                failed += 1
                logger.error(f"Ошибка отправки пользователю {user.tg_id}: {e}")
        
        await callback.message.answer(
            f"✅ Рассылка завершена!\n\n"
            f"📨 Отправлено: {sent}\n"
            f"❌ Ошибок: {failed}",
            reply_markup=get_admin_reply_keyboard()
        )
        break
    
    await state.clear()
    await state.set_data({"is_admin_mode": True})
    await callback.answer()

@router.callback_query(AdminStates.waiting_broadcast_confirm, F.data == "cancel_broadcast")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    await state.clear()
    await state.set_data({"is_admin_mode": True})
    await callback.message.edit_text("❌ Рассылка отменена.")
    await callback.message.answer("Выберите следующее действие:", reply_markup=get_admin_reply_keyboard())
    await callback.answer()