from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
  result = await db.execute(select(User).where(User.id == user_id))
  return result.scalars().first()


async def get_user_or_404(db: AsyncSession, user_id: int) -> User:
  user = await get_user_by_id(db, user_id)

  if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

  return user