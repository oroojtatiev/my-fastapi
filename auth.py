from datetime import UTC, datetime, timedelta
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pwdlib import PasswordHash
import jwt
import hashlib
import secrets
from config import settings
from database import get_db
from crud import get_user_by_id
from models import User

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")


def verify_password(plain_password, hashed_password):
  return password_hash.verify(plain_password, hashed_password)


def generate_reset_token() -> str:
  return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
  return hashlib.sha256(token.encode()).hexdigest()


def get_password_hash(password) -> str:
  return password_hash.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
  """Create a JWT access token."""
  to_encode = data.copy()

  if expires_delta:
    expire = datetime.now(UTC) + expires_delta
  else:
    expire = datetime.now(UTC) + timedelta(
      minutes=settings.auth_access_token_expire_minutes,
    )

  to_encode.update({"exp": expire})

  encoded_jwt = jwt.encode(
    to_encode,
    settings.auth_secret_key.get_secret_value(),
    algorithm=settings.auth_algorithm,
  )

  return encoded_jwt


def verify_access_token(token: str) -> str | None:
  """Verify a JWT access token and return the subject (user id) if valid."""
  try:
    payload = jwt.decode(
      token,
      settings.auth_secret_key.get_secret_value(),
      algorithms=[settings.auth_algorithm],
      options={"require": ["exp", "sub"]},
    )
  except jwt.InvalidTokenError:
    return None
  else:
    return payload.get("sub")


async def get_current_user(
  token: Annotated[str, Depends(oauth2_scheme)],
  db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
  user_id = verify_access_token(token)

  if user_id is None:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid or expired token",
      headers={"WWW-Authenticate": "Bearer"},
    )

  # Validate user_id is a valid integer (defense against malformed JWT)
  try:
    user_id_int = int(user_id)
  except (TypeError, ValueError):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid or expired token",
      headers={"WWW-Authenticate": "Bearer"},
    )

  user = await get_user_by_id(db, user_id_int)

  if not user:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="User not found",
      headers={"WWW-Authenticate": "Bearer"},
    )

  return user


CurrentUser = Annotated[User, Depends(get_current_user)]
