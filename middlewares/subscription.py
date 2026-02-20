from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from database import get_db
from models import Sponsor, User
from sqlalchemy import select
from keyboards import get_subscribe_keyboard
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id
        if isinstance(event, Message):
            user_id = event.from_user.id
            # Пропускаем команду /start без проверки
            if event.text and event.text == "/start":
                return await handler(event, data)
        else:
            user_id = event.from_user.id
            # Пропускаем callback подписки
            if event.data == "check_subscription":
                return await handler(event, data)
        
        # Проверяем подписку
        async for db in get_db():
            try:
                # Получаем пользователя
                user = await db.execute(select(User).where(User.tg_id == user_id))
                user = user.scalar_one_or_none()
                
                if not user:
                    return await handler(event, data)
                
                # Получаем активных спонсоров
                sponsors = await db.execute(select(Sponsor).where(Sponsor.is_active == True))
                sponsors = sponsors.scalars().all()
                
                if not sponsors:
                    # Если нет спонсоров, пропускаем
                    return await handler(event, data)
                
                # ===== ВАЖНО: ВСЕГДА ПРОВЕРЯЕМ РЕАЛЬНУЮ ПОДПИСКУ =====
                # Даже если в БД стоит True, проверяем через API
                
                not_subscribed_sponsors = []
                
                for sponsor in sponsors:
                    try:
                        # Извлекаем username из ссылки
                        if 't.me/' in sponsor.url:
                            username = sponsor.url.split('t.me/')[-1].split('/')[0].replace('@', '')
                            chat_id = f"@{username}"
                        else:
                            continue
                        
                        # Проверяем статус пользователя в канале
                        member = await data['bot'].get_chat_member(chat_id=chat_id, user_id=user_id)
                        
                        if member.status in ["left", "kicked"]:
                            not_subscribed_sponsors.append(sponsor)
                            
                    except Exception as e:
                        logger.error(f"Ошибка при проверке {sponsor.name}: {e}")
                        not_subscribed_sponsors.append(sponsor)
                
                # ===== СИНХРОНИЗИРУЕМ СТАТУС В БД =====
                if not_subscribed_sponsors:
                    # Если есть неподписанные спонсоры - обновляем БД на False
                    if user.is_subscribed:
                        user.is_subscribed = False
                        await db.commit()
                        logger.info(f"❌ Пользователь {user_id} отписался, статус обновлен в БД")
                    
                    # Показываем сообщение с требованием подписки
                    text = "🔒 **Для доступа к боту необходимо подписаться:**\n\n"
                    for s in not_subscribed_sponsors:
                        text += f"• {s.name}\n"
                    text += "\nПосле подписки нажмите кнопку ниже."
                    
                    keyboard = get_subscribe_keyboard(not_subscribed_sponsors)
                    
                    if isinstance(event, Message):
                        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
                    else:
                        await event.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                    return
                else:
                    # Если подписан на всех - обновляем БД на True
                    if not user.is_subscribed:
                        user.is_subscribed = True
                        await db.commit()
                        logger.info(f"✅ Пользователь {user_id} подписан на всех, статус обновлен в БД")
                    
                    # Пропускаем
                    return await handler(event, data)
                
            except Exception as e:
                logger.error(f"Ошибка в middleware: {e}")
                return await handler(event, data)