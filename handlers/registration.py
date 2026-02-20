from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import get_main_menu_keyboard, get_cancel_keyboard, get_roles_keyboard,get_confirm_keyboard,get_edit_keyboard
from database import get_db
from models import User
from sqlalchemy import select
import re
from keyboards import (
    get_main_menu_keyboard,  
    get_cancel_keyboard,
    get_roles_keyboard,
    get_confirm_keyboard,
    get_edit_keyboard
)


router = Router()

class Registration(StatesGroup):
    name = State()
    surname = State()
    age = State()
    role = State()
    photo = State()
    confirm = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = message.from_user.id
    
    async for db in get_db():
        user = await db.execute(select(User).where(User.tg_id == telegram_id))
        user = user.scalar_one_or_none()
        
        if not user:
            await state.set_state(Registration.name)
            await message.answer(
                "👋 Добро пожаловать! Давайте зарегистрируемся.\n\n"
                "📝 Введите ваше **имя** (только буквы):",
                reply_markup=get_cancel_keyboard()
            )
        else:
            await message.answer(
                f"👋 С возвращением, {user.name}!",
                reply_markup=get_main_menu_keyboard()
            )
        break

@router.message(Registration.name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    
    if not name.replace(' ', '').isalpha() or len(name) < 2:
        await message.answer(
            "❌ Имя должно содержать только буквы и быть не короче 2 символов.\n"
            "Пожалуйста, введите имя правильно:"
        )
        return
    
    if any(char.isdigit() for char in name):
        await message.answer(
            "❌ Имя не должно содержать цифры.\n"
            "Пожалуйста, введите имя правильно:"
        )
        return
    
    await state.update_data(name=name)
    await state.set_state(Registration.surname)
    await message.answer(
        "📝 Введите вашу **фамилию** (только буквы, можно пропустить введя '-'):",
        reply_markup=get_cancel_keyboard()
    )

@router.message(Registration.surname)
async def process_surname(message: Message, state: FSMContext):
    surname = message.text.strip()
    
    if surname == "-":
        surname = None
    else:
        if not surname.replace(' ', '').isalpha():
            await message.answer(
                "❌ Фамилия должна содержать только буквы.\n"
                "Пожалуйста, введите фамилию правильно или '-' для пропуска:"
            )
            return
        
        if any(char.isdigit() for char in surname):
            await message.answer(
                "❌ Фамилия не должна содержать цифры.\n"
                "Пожалуйста, введите фамилию правильно или '-' для пропуска:"
            )
            return
    
    await state.update_data(surname=surname)
    await state.set_state(Registration.age)
    await message.answer(
        "🔢 Введите ваш **возраст** (только число, от 5 до 120):",
        reply_markup=get_cancel_keyboard()
    )

@router.message(Registration.age)
async def process_age(message: Message, state: FSMContext):
    age_text = message.text.strip()
    
    if not age_text.isdigit():
        await message.answer(
            "❌ Возраст должен быть числом.\n"
            "Пожалуйста, введите возраст цифрами:"
        )
        return
    
    age = int(age_text)
    
    if age < 5 or age > 120:
        await message.answer(
            "❌ Возраст должен быть от 5 до 120 лет.\n"
            "Пожалуйста, введите корректный возраст:"
        )
        return
    
    await state.update_data(age=age)
    await state.set_state(Registration.role)
    await message.answer(
        "👤 Выберите вашу **роль**:",
        reply_markup=get_roles_keyboard()
    )

@router.callback_query(Registration.role)
async def process_role(callback: CallbackQuery, state: FSMContext):
    role_map = {
        "role_student": "🎓 Студент",
        "role_pupil": "📚 Школьник",
        "role_worker": "💼 Работающий",
        "role_other": "👤 Другое"
    }
    
    if callback.data not in role_map:
        await callback.answer("Пожалуйста, выберите роль из кнопок")
        return
    
    role = role_map[callback.data]
    await state.update_data(role=role)
    await state.set_state(Registration.photo)
    
    await callback.message.delete()
    await callback.message.answer(
        "📸 Отправьте ваше **фото** (обязательно):\n\n"
        "Это должно быть именно фото, а не файл или документ.",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Registration.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    
    await state.update_data(photo=photo_file_id)
    
    data = await state.get_data()
    
    profile_text = (
        f"📇 **Ваша карточка:**\n\n"
        f"👤 **Имя:** {data['name']}\n"
        f"👤 **Фамилия:** {data.get('surname', '—')}\n"
        f"🔢 **Возраст:** {data['age']}\n"
        f"👥 **Роль:** {data['role']}\n"
    )
    
    await message.answer_photo(
        photo=photo_file_id,
        caption=profile_text,
        reply_markup=get_confirm_keyboard()  
    )
    await state.set_state(Registration.confirm)

@router.message(Registration.photo)
async def process_photo_invalid(message: Message, state: FSMContext):
    await message.answer(
        "❌ Это не фото. Пожалуйста, отправьте именно **фотографию**, а не файл или документ.\n"
        "Если хотите отменить регистрацию, нажмите /cancel",
        reply_markup=get_cancel_keyboard()
    )

@router.callback_query(Registration.confirm, F.data == "confirm")
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    telegram_id = callback.from_user.id
    
    async for db in get_db():
        user = User(
            tg_id=telegram_id,
            name=data['name'],
            surname=data.get('surname'),
            age=data['age'],
            role=data['role'],
            photo_file_id=data['photo'],
            level=1,
            xp=0
        )
        db.add(user)
        await db.commit()
        
        await callback.message.delete()
        await callback.message.answer(
            "✅ **Регистрация успешно завершена!**\n\n"
            "Добро пожаловать в MentorAI Bot!",
            reply_markup=get_main_menu_keyboard()
        )
        break
    
    await state.clear()
    await callback.answer()

@router.callback_query(Registration.confirm, F.data == "edit")
async def process_edit(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "Выберите, что хотите изменить:",
        reply_markup=get_edit_keyboard()
    )
    await callback.answer()

@router.message(F.text == "❌ Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Действие отменено. Возвращаюсь в главное меню.",
        reply_markup=get_main_menu_keyboard()
    )