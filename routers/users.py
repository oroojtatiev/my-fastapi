from typing import Annotated
from datetime import timedelta, UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from PIL import UnidentifiedImageError
from botocore.exceptions import ClientError
from models import User, PasswordResetToken
from database import get_db
from crud import get_user_or_404, get_posts_by_user
from schemas import UserCreate, UserPublic, UserPrivate, UserUpdate, PostResponse, Token
from schemas import ChangePasswordRequest, ResetPasswordRequest, ForgotPasswordRequest
from auth import create_access_token, verify_password, get_password_hash, CurrentUser, generate_reset_token
from auth import hash_reset_token
from config import settings
from utils.images import process_profile_image, delete_profile_image, upload_profile_image
from utils.emails import send_password_reset_email

router = APIRouter()


@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
  result = await db.execute(
    select(User)
    .where(func.lower(User.username) == user.username.lower()),
  )
  existing_user = result.scalars().first()

  if existing_user:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

  result = await db.execute(
    select(User)
    .where(func.lower(User.email) == user.email.lower()),
  )
  existing_email = result.scalars().first()

  if existing_email:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

  new_user = User(username=user.username, email=user.email.lower(), password_hash=get_password_hash(user.password))
  db.add(new_user)

  await db.commit()
  await db.refresh(new_user)

  return new_user


@router.post("/login", response_model=Token)
async def login(
  form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
  db: Annotated[AsyncSession, Depends(get_db)],
):
  # Look up user by email (case-insensitive)
  # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
  result = await db.execute(
    select(User)
    .where(func.lower(User.email) == form_data.username.lower()),
  )
  user: User | None = result.scalars().first()

  # Verify user exists and password is correct
  # Don't reveal which one failed (security best practice)
  if not user or not verify_password(form_data.password, user.password_hash):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Incorrect email or password",
      headers={"WWW-Authenticate": "Bearer"},
    )

  # Create access token with user id as subject
  access_token_expires = timedelta(minutes=settings.auth_access_token_expire_minutes)
  access_token = create_access_token(
    data={"sub": str(user.id)},
    expires_delta=access_token_expires,
  )

  return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivate)
async def read_me(user: CurrentUser):
  return user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
  request_data: ForgotPasswordRequest,
  background_tasks: BackgroundTasks,
  db: Annotated[AsyncSession, Depends(get_db)],
):
  result = await db.execute(
    select(User)
    .where(func.lower(User.email) == request_data.email.lower()),
  )
  user: User | None = result.scalars().first()

  if user:
    await db.execute(
      delete(PasswordResetToken)
      .where(
        PasswordResetToken.user_id == user.id,
      ),
    )

    token = generate_reset_token()
    token_hash = hash_reset_token(token)
    expires_at = datetime.now(UTC) + timedelta(
      minutes=settings.mail_reset_token_expire_minutes
    )

    reset_token = PasswordResetToken(
      user_id=user.id,
      token_hash=token_hash,
      expires_at=expires_at,
    )

    db.add(reset_token)
    await db.commit()

    background_tasks.add_task(
      send_password_reset_email,
      to_email=user.email,
      username=user.username,
      token=token,
    )

  return {
    "message": "If an account exists with this email, you will receive password reset instructions."
  }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
  request_data: ResetPasswordRequest,
  db: Annotated[AsyncSession, Depends(get_db)],
):
  token_hash = hash_reset_token(request_data.token)

  result = await db.execute(
    select(PasswordResetToken)
    .where(PasswordResetToken.token_hash == token_hash),
  )
  reset_token: PasswordResetToken | None = result.scalars().first()

  if not reset_token:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Invalid or expired reset token",
    )

  if reset_token.expires_at < datetime.now(UTC):
    await db.delete(reset_token)
    await db.commit()
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Invalid or expired reset token",
    )

  result = await db.execute(
    select(User)
    .where(User.id == reset_token.user_id),
  )
  user: User | None = result.scalars().first()

  if not user:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Invalid or expired reset token",
    )

  user.password_hash = get_password_hash(request_data.new_password)

  await db.execute(
    delete(PasswordResetToken)
    .where(PasswordResetToken.user_id == user.id),
  )

  await db.commit()

  return {
    "message": "Password reset successfully. You can now log in with your new password."
  }


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
  password_data: ChangePasswordRequest,
  current_user: CurrentUser,
  db: Annotated[AsyncSession, Depends(get_db)],
):
  if not verify_password(password_data.current_password, current_user.password_hash):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Current password is incorrect",
    )

  current_user.password_hash = get_password_hash(password_data.new_password)

  await db.execute(
    delete(PasswordResetToken)
    .where(PasswordResetToken.user_id == current_user.id),
  )

  await db.commit()

  return {"message": "Password changed successfully"}


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
  result = await db.execute(
    select(User)
    .where(User.id == user_id)
  )
  user = result.scalars().first()

  if user:
    return user

  raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
  await get_user_or_404(db, user_id)
  return await get_posts_by_user(db, user_id)


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
  user_id: int,
  user_update: UserUpdate,
  user: CurrentUser,
  db: Annotated[AsyncSession, Depends(get_db)]
):
  if user_id != user.id:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")

  if user_update.username is not None and user_update.username.lower() != user.username.lower():
    result = await db.execute(
      select(User)
      .where(func.lower(User.username) == user_update.username.lower()),
    )
    existing_user = result.scalars().first()

    if existing_user:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

  if user_update.email is not None and user_update.email.lower() != user.email.lower():
    result = await db.execute(
      select(User)
      .where(func.lower(User.email) == user_update.email.lower()),
    )
    existing_email = result.scalars().first()

    if existing_email:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

  username: str | None = user_update.username

  if username is not None:
    user.username = username

  email: str | None = user_update.email

  if email is not None:
    user.email = email.lower()

  await db.commit()
  await db.refresh(user)

  return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
  if user_id != user.id:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")

  result = await db.execute(
    select(User)
    .where(User.id == user_id)
  )
  user: User | None = result.scalar()

  if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

  old_filename = user.image_file

  await db.delete(user)
  await db.commit()

  if old_filename:
    await delete_profile_image(old_filename)


@router.patch("/{user_id}/picture", response_model=UserPrivate)
async def upload_profile_picture(
  user_id: int,
  file: UploadFile,
  user: CurrentUser,
  db: Annotated[AsyncSession, Depends(get_db)],
):
  if user.id != user_id:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Not authorized to update this user's picture",
    )

  content = await file.read()

  if len(content) > settings.media_max_upload_size_bytes:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"File too large. Maximum size is {settings.media_max_upload_size_bytes // (1024 * 1024)}MB",
    )

  try:
    file_bytes, file_name = await run_in_threadpool(process_profile_image, content)
  except UnidentifiedImageError as err:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Invalid image file. Please upload a valid image (JPEG, PNG, GIF, WebP).",
    ) from err

  # Upload to S3 (also runs in threadpool via async wrapper)
  try:
    await upload_profile_image(file_bytes, file_name)
  except ClientError as err:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Failed to upload image. Please try again.",
    ) from err

  old_filename = user.image_file

  user.image_file = file_name
  await db.commit()
  await db.refresh(user)

  if old_filename:
    await delete_profile_image(old_filename)

  return user


@router.delete("/{user_id}/picture", response_model=UserPrivate)
async def delete_user_picture(user_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
  if current_user.id != user_id:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user's picture")

  old_filename = current_user.image_file

  if old_filename is None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No profile picture to delete")

  current_user.image_file = None

  await db.commit()
  await db.refresh(current_user)

  await delete_profile_image(old_filename)

  return current_user
