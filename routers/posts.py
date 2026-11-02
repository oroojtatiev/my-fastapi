from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from models import Post, User
from database import get_db
from schemas import PostResponse, PostCreate, PostUpdate, PaginatedPostsResponse
from auth import CurrentUser
from crud import get_all_posts, get_post_or_404

router = APIRouter()


async def get_own_post(post_id: int, user: User, db: AsyncSession) -> Post:
  post = await get_post_or_404(db, post_id)

  if post.user_id != user.id:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update/delete this post")

  return post


@router.get("", response_model=PaginatedPostsResponse)
async def get_posts(
  db: Annotated[AsyncSession, Depends(get_db)],
  skip: Annotated[int, Query(ge=0)] = 0,
  limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
  posts, total = await get_all_posts(db, skip, limit)

  return PaginatedPostsResponse(
    posts=posts,
    total=total,
    skip=skip,
    limit=limit,
    has_more=skip + len(posts) < total,
  )


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
  new_post = Post(title=post.title, content=post.content, user_id=user.id)
  db.add(new_post)

  await db.commit()
  await db.refresh(new_post, attribute_names=["author"])

  return new_post


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
  return await get_post_or_404(db, post_id)


@router.put("/{post_id}", response_model=PostResponse)
async def update_post_full(
  post_id: int,
  post_data: PostCreate,
  user: CurrentUser,
  db: Annotated[AsyncSession, Depends(get_db)]
):
  post = await get_own_post(post_id, user, db)

  post.title = post_data.title
  post.content = post_data.content

  await db.commit()
  await db.refresh(post, attribute_names=["author"])

  return post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial(
  post_id: int,
  post_data: PostUpdate,
  user: CurrentUser,
  db: Annotated[AsyncSession, Depends(get_db)]
):
  post = await get_own_post(post_id, user, db)

  update_data = post_data.model_dump(exclude_unset=True)

  for field, value in update_data.items():
    setattr(post, field, value)

  await db.commit()
  await db.refresh(post, attribute_names=["author"])

  return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
  post = await get_own_post(post_id, user, db)

  await db.delete(post)
  await db.commit()
