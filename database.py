from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем движок
engine = create_async_engine(
    Config.DATABASE_URL,
    echo=True,
    pool_pre_ping=True
)

# Создаем фабрику сессий - ЭТО НУЖНО ДЛЯ ЭКСПОРТА
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Функция для получения сессии (для хендлеров)
async def get_db():
    """Возвращает сессию базы данных для использования с 'async for'"""
    async with AsyncSessionLocal() as session:
        yield session

# Функция для проверки соединения
async def check_connection():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("✅ Подключение к БД работает")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        return False