from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import get_db
from models import User, Sponsor
from sqlalchemy import select
from keyboards import get_main_menu_keyboard, get_subscribe_keyboard
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    """Проверка подписки после нажатия кнопки"""
    user_id = callback.from_user.id
    bot = callback.bot
    
    await callback.answer("🔍 Проверяю подписку...")
    
    async for db in get_db():
        try:
            # Получаем пользователя
            user = await db.execute(select(User).where(User.tg_id == user_id))
            user = user.scalar_one_or_none()
            
            if not user:
                await callback.message.answer(
                    "❌ Сначала зарегистрируйтесь через /start",
                    reply_markup=get_main_menu_keyboard()
                )
                return
            
            # Получаем активных спонсоров
            sponsors = await db.execute(select(Sponsor).where(Sponsor.is_active == True))
            sponsors = sponsors.scalars().all()
            
            if not sponsors:
                # Если нет спонсоров
                user.is_subscribed = True
                await db.commit()
                await callback.message.delete()
                await callback.message.answer(
                    "✅ Добро пожаловать!",
                    reply_markup=get_main_menu_keyboard()
                )
                await callback.answer("✅ Доступ разрешен")
                return
            
            # Проверяем подписку на каждого спонсора
            not_subscribed = []
            for sponsor in sponsors:
                try:
                    if 't.me/' in sponsor.url:
                        username = sponsor.url.split('t.me/')[-1].split('/')[0].replace('@', '')
                        chat_id = f"@{username}"
                        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                        if member.status in ["left", "kicked"]:
                            not_subscribed.append(sponsor)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    not_subscribed.append(sponsor)
            
            if not_subscribed:
                # Если есть неподписанные спонсоры
                text = "❌ **Вы подписались не на всех!**\n\nОсталось:\n"
                for s in not_subscribed:
                    text += f"• {s.name}\n"
                
                # Обновляем статус в БД на False
                if user.is_subscribed:
                    user.is_subscribed = False
                    await db.commit()
                    logger.info(f"❌ Пользователь {user_id} не подписан, статус обновлен")
                
                await callback.message.edit_text(
                    text,
                    reply_markup=get_subscribe_keyboard(not_subscribed),
                    parse_mode="HTML"
                )
                await callback.answer("❌ Подпишитесь на всех", show_alert=True)
            else:
                # Если подписан на всех
                if not user.is_subscribed:
                    user.is_subscribed = True
                    await db.commit()
                    logger.info(f"✅ Пользователь {user_id} подтвердил подписку")
                
                await callback.message.delete()
                await callback.message.answer(
                    f"✅ **Добро пожаловать, {user.name}!**",
                    reply_markup=get_main_menu_keyboard()
                )
                await callback.answer("✅ Доступ разрешен!")
                
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.message.answer(
                "❌ Ошибка. Попробуйте /start",
                reply_markup=get_main_menu_keyboard()
            )