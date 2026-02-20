from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from config import Config

class AdminModeMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id
        if isinstance(event, Message):
            user_id = event.from_user.id
        else:
            user_id = event.from_user.id
        
        # Проверяем, админ ли
        if user_id in Config.ADMIN_IDS:
            # Для админов всегда проверяем состояние
            state = data.get('state')
            if state:
                state_data = await state.get_data()
                # Если нет is_admin_mode, устанавливаем его
                if not state_data.get('is_admin_mode'):
                    await state.update_data(is_admin_mode=True)
        
        return await handler(event, data)