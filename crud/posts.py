from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from models import Post
from schemas import PostResponse


async def get_posts_by_user(db: AsyncSession, user_id: int) -> list[Post]:
  result = await db.execute(
    select(Post)
    .options(selectinload(Post.author))
    .where(Post.user_id == user_id)
    .order_by(Post.date_posted.desc()),
  )
  return list(result.scalars().all())


async def get_all_posts(db: AsyncSession, skip: int, limit: int) -> tuple[list[PostResponse], int]:
  result = await db.execute(
    select(Post)
    .options(selectinload(Post.author))
    .order_by(Post.date_posted.desc())
    .limit(limit)
    .offset(skip),
  )

  count_result = await db.execute(select(func.count()).select_from(Post))
  total = count_result.scalar() or 0
  posts = result.scalars().all()
  posts: list[PostResponse] = [PostResponse.model_validate(post) for post in posts]

  return posts, total


async def get_post_or_404(db: AsyncSession, post_id: int) -> Post:
  result = await db.execute(
    select(Post)
    .options(selectinload(Post.author))
    .where(Post.id == post_id),
  )
  post = result.scalars().first()

  if not post:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

  return post