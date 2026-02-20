from sqlalchemy.ext.asyncio import AsyncSession
from database import async_session
import asyncio

async def get_db_with_retry(retries=3, delay=2):
    for attempt in range(retries):
        try:
            session = async_session()
            yield session
            return
        except Exception as e:
            print(f"DB error (attempt {attempt+1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise
        finally:
            await session.close()