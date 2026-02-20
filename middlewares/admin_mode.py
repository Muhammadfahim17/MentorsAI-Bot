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
        if isinstance(event, Message):
            user_id = event.from_user.id
        else:
            user_id = event.from_user.id
        
        if user_id in Config.ADMIN_IDS:
            state = data.get('state')
            if state:
                state_data = await state.get_data()
                if not state_data.get('is_admin_mode'):
                    await state.update_data(is_admin_mode=True)
        
        return await handler(event, data)