from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ===== REPLY КЛАВИАТУРЫ (обычные кнопки внизу) =====

def get_main_menu_keyboard():
    """Главное меню с кнопками (ReplyKeyboard)"""
    buttons = [
        [KeyboardButton(text="📚 Курсы")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📊 Прогресс")],
        [KeyboardButton(text="🏆 ТОП-10"), KeyboardButton(text="⭐ Закладки")],
        [KeyboardButton(text="❓ FAQ"), KeyboardButton(text="ℹ️ О боте")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_cancel_keyboard():
    """Кнопка отмены (для админки)"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
    


def get_admin_reply_keyboard():
    """Меню для админа (ReplyKeyboard)"""
    buttons = [
        [KeyboardButton(text="📁 Добавить категорию")],
        [KeyboardButton(text="📂 Добавить подкатегорию")],
        [KeyboardButton(text="📎 Добавить материал")],
        [KeyboardButton(text="🔗 Добавить спонсора")],
        [KeyboardButton(text="❌ Удалить спонсора")],
        [KeyboardButton(text="🗑 Удалить категорию")],
        [KeyboardButton(text="🗑 Удалить подкатегорию")],
        [KeyboardButton(text="🗑 Удалить материал")],
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🏆 ТОП-10 (админ)")],
        [KeyboardButton(text="📨 Рассылка")],
        [KeyboardButton(text="🚪 Выход")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ===== INLINE КЛАВИАТУРЫ =====

def main_menu():
    """Инлайн главное меню"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📚 Выбрать материалы для обучения", callback_data="learn"))
    builder.add(InlineKeyboardButton(text="ℹ️ О боте", callback_data="about"))
    builder.add(InlineKeyboardButton(text="❓ Часто задаваемые вопросы", callback_data="faq"))
    builder.add(InlineKeyboardButton(text="🏆 ТОП 10", callback_data="top10"))
    builder.add(InlineKeyboardButton(text="👤 Профиль", callback_data="profile"))
    builder.add(InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats"))
    builder.add(InlineKeyboardButton(text="🎓 Мой путь обучения", callback_data="my_path"))
    builder.adjust(1)
    return builder.as_markup()

def back_button(cb_data: str = "back_to_main"):
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data=cb_data))
    return builder.as_markup()

def get_roles_keyboard():
    """Кнопки для выбора роли"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🎓 Студент", callback_data="role_student"))
    builder.add(InlineKeyboardButton(text="📚 Школьник", callback_data="role_pupil"))
    builder.add(InlineKeyboardButton(text="💼 Работающий", callback_data="role_worker"))
    builder.add(InlineKeyboardButton(text="👤 Другое", callback_data="role_other"))
    builder.adjust(2)
    return builder.as_markup()

def get_confirm_keyboard():
    """Кнопки подтверждения (для регистрации)"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Всё верно", callback_data="confirm"))
    builder.add(InlineKeyboardButton(text="✏️ Изменить", callback_data="edit"))
    builder.adjust(2)
    return builder.as_markup()

def get_edit_keyboard():
    """Кнопки для выбора поля для изменения"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👤 Имя", callback_data="edit_name"))
    builder.add(InlineKeyboardButton(text="👤 Фамилия", callback_data="edit_surname"))
    builder.add(InlineKeyboardButton(text="🔢 Возраст", callback_data="edit_age"))
    builder.add(InlineKeyboardButton(text="👥 Роль", callback_data="edit_role"))
    builder.add(InlineKeyboardButton(text="📸 Фото", callback_data="edit_photo"))
    builder.add(InlineKeyboardButton(text="✅ Готово", callback_data="edit_done"))
    builder.adjust(2)
    return builder.as_markup()

# ===== КЛАВИАТУРЫ ДЛЯ ОБУЧЕНИЯ (ИЗ JSON) =====

def get_categories_keyboard(categories):
    """Кнопки категорий из JSON"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.add(InlineKeyboardButton(text=cat['name'], callback_data=f"cat_{cat['id']}"))
    builder.adjust(2)
    return builder.as_markup()

def get_subcategories_keyboard(subcategories):
    """Кнопки подкатегорий из JSON"""
    builder = InlineKeyboardBuilder()
    for sub in subcategories:
        builder.add(InlineKeyboardButton(text=sub['name'], callback_data=f"sub_{sub['id']}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_categories"))
    builder.adjust(2)
    return builder.as_markup()

def get_material_navigation_keyboard(current, total, subcat_id, material_id):
    """Кнопки навигации по урокам"""
    builder = InlineKeyboardBuilder()
    
    if current > 0:
        builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"prev_{subcat_id}_{current}"))
    
    if current < total - 1:
        builder.add(InlineKeyboardButton(text="➡️ Далее", callback_data=f"next_{subcat_id}_{current}"))
    
    builder.add(InlineKeyboardButton(text="⭐ Сохранить", callback_data=f"save_{material_id}"))
    builder.add(InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_rating_keyboard(sub_id: int = 0):
    """Кнопки оценки курса (1-5 звезд)"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.add(InlineKeyboardButton(text="⭐" * i, callback_data=f"rate_{sub_id}_{i}"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_categories"))
    builder.adjust(5, 1)
    return builder.as_markup()

def stars_keyboard(sub_id: int):
    """Кнопки оценки звездами (альтернативное название)"""
    return get_rating_keyboard(sub_id)

# ===== КЛАВИАТУРЫ ДЛЯ АДМИНА =====

def get_categories_inline(categories, prefix="cat"):
    """Инлайн клавиатура для выбора категории (админ)"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        # Поддерживаем и SQL объекты, и JSON словари
        if isinstance(cat, dict):
            text = cat['name']
            cat_id = cat['id']
        else:
            text = cat.name
            cat_id = cat.id
        builder.add(InlineKeyboardButton(text=text, callback_data=f"{prefix}_{cat_id}"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    builder.adjust(1)
    return builder.as_markup()

def get_subcategories_inline(subcategories, prefix="sub"):
    """Инлайн клавиатура для выбора подкатегории (админ)"""
    builder = InlineKeyboardBuilder()
    for sub in subcategories:
        # Поддерживаем и SQL объекты, и JSON словари
        if isinstance(sub, dict):
            text = sub['name']
            sub_id = sub['id']
        else:
            text = sub.name
            sub_id = sub.id
        builder.add(InlineKeyboardButton(text=text, callback_data=f"{prefix}_{sub_id}"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    builder.adjust(1)
    return builder.as_markup()

def get_content_type_keyboard():
    """Клавиатура выбора типа контента"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📝 Текст", callback_data="ctype_text"))
    builder.add(InlineKeyboardButton(text="📸 Фото", callback_data="ctype_photo"))
    builder.add(InlineKeyboardButton(text="🎥 Видео", callback_data="ctype_video"))
    builder.add(InlineKeyboardButton(text="📄 Документ", callback_data="ctype_document"))
    builder.add(InlineKeyboardButton(text="🔗 YouTube", callback_data="ctype_youtube"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    builder.adjust(2)
    return builder.as_markup()

def get_confirm_keyboard_admin(action="material"):
    """Клавиатура подтверждения для админа"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"))
    builder.add(InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}"))
    builder.adjust(2)
    return builder.as_markup()

def get_sponsors_inline(sponsors, action="delete"):
    """Клавиатура выбора спонсора"""
    builder = InlineKeyboardBuilder()
    for s in sponsors:
        builder.add(InlineKeyboardButton(
            text=f"{s.name}",
            callback_data=f"del_sponsor_{s.id}" if action == "delete" else f"sponsor_{s.id}"
        ))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    builder.adjust(1)
    return builder.as_markup()

def get_broadcast_keyboard(data):
    """Клавиатура для рассылки"""
    if not data.get('button_text'):
        return None
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=data['button_text'],
        url=data['button_url']
    ))
    return builder.as_markup()

def get_subscribe_keyboard(sponsors):
    """Кнопки для подписки на спонсоров"""
    builder = InlineKeyboardBuilder()
    for s in sponsors:
        builder.add(InlineKeyboardButton(text=f"📢 {s.name}", url=s.url))
    builder.add(InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription"))
    builder.adjust(1)
    return builder.as_markup()

def get_continue_keyboard(sub_id: int):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="▶️ Продолжить", callback_data=f"continue_{sub_id}"))
    builder.add(InlineKeyboardButton(text="🔄 Начать заново", callback_data=f"restart_{sub_id}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_categories"))
    builder.adjust(2, 1)
    return builder.as_markup()