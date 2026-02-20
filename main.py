import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import selectors
from config import Config
from database import engine, Base, AsyncSessionLocal
from handlers import registration, menu, learning, admin, subscription
from services.notifications import send_daily_tip
from middlewares.subscription import SubscriptionMiddleware
from services.achievements import initialize_achievements
from middlewares.admin_mode import AdminModeMiddleware


# Настройка event loop для Windows
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
selector = selectors.SelectSelector()
loop = asyncio.SelectorEventLoop(selector)
asyncio.set_event_loop(loop)

# Инициализация бота и диспетчера
bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.message.middleware(AdminModeMiddleware())
dp.callback_query.middleware(AdminModeMiddleware())

# Подключаем middleware
dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())

# Подключаем роутеры
dp.include_router(registration.router)
dp.include_router(menu.router)
dp.include_router(learning.router)
dp.include_router(admin.router)
dp.include_router(subscription.router)

async def on_startup():
    """Действия при запуске бота"""
    # Создаем таблицы в БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Инициализируем достижения
    async with AsyncSessionLocal() as db:
        await initialize_achievements(db)
    
    print("✅ MentorAI Bot запущен!")
    print(f"🤖 Бот: @{(await bot.me()).username}")
    print(f"👤 Админы: {Config.ADMIN_IDS}")

async def on_shutdown():
    """Действия при остановке бота"""
    print("🛑 Бот остановлен")
    await bot.session.close()

async def send_daily_tip_wrapper():
    """Обертка для отправки ежедневных советов"""
    async with AsyncSessionLocal() as db:
        await send_daily_tip(bot, db)

async def main():
    # Настройка планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_tip_wrapper, 'cron', hour=9, minute=0)  # Каждый день в 9:00
    scheduler.start()
    print("⏰ Планировщик задач запущен")

    # Регистрируем обработчики событий
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")