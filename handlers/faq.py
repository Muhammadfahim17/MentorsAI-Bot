from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu_keyboard, back_button
from utils.json_db import json_db

router = Router()

@router.message(F.text == "❓ FAQ")
async def faq_handler(message: Message):
    """Показать часто задаваемые вопросы"""
    faqs = json_db.get_faq()
    
    if not faqs:
        await message.answer(
            "❓ FAQ пока пуст. Скоро здесь появятся вопросы!",
            reply_markup=back_button("back_to_main")
        )
        return
    
    text = "❓ **Часто задаваемые вопросы**\n\n"
    for i, faq in enumerate(faqs, 1):
        text += f"**{i}. {faq['question']}**\n{faq['answer']}\n\n"
    
    await message.answer(text, reply_markup=back_button("back_to_main"))