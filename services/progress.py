from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import UserProgress, User
from datetime import datetime

async def update_progress(db: AsyncSession, user_id: int, subcategory_id: int, material_order: int):
    progress = (await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == user_id,
            UserProgress.subcategory_id == subcategory_id
        )
    )).scalar_one_or_none()

    if not progress:
        progress = UserProgress(user_id=user_id, subcategory_id=subcategory_id)
        db.add(progress)

    if material_order not in (progress.completed_materials or []):
        if not progress.completed_materials:
            progress.completed_materials = []
        progress.completed_materials.append(material_order)
    
    progress.current_material_order = material_order
    progress.progress_percent = min(len(progress.completed_materials) * 20, 100)  # для 5 уроков
    progress.last_accessed = func.now()
    await db.commit()