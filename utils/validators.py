from aiogram.types import Message

async def is_photo(message: Message) -> bool:
    return bool(message.photo)

async def is_valid_url(text: str) -> bool:
    return text.startswith(("http://", "https://"))

async def is_text_only(message: Message) -> bool:
    return bool(message.text) and not message.photo and not message.video and not message.document