from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime


class User(BaseModel):
  username: str = Field(min_length=1, max_length=50)
  email: EmailStr = Field(min_length=1, max_length=120)


class UserCreate(User):
  password: str = Field(min_length=8)


class UserUpdate(BaseModel):
  username: Annotated[str, Field(min_length=1, max_length=50)] | None = None
  email: Annotated[EmailStr, Field(min_length=1, max_length=120)] | None = None


class UserPublic(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: int
  username: str
  image_file: str | None
  image_path: str


class UserPrivate(UserPublic):
  email: EmailStr


class Token(BaseModel):
  access_token: str
  token_type: str


class Post(BaseModel):
  title: str = Field(min_length=1, max_length=100)
  content: str = Field(min_length=1)


class PostCreate(Post):
  pass


class PostUpdate(BaseModel):
  title: str | None = Field(default=None, min_length=1, max_length=100)
  content: str | None = Field(default=None, min_length=1)


class PostResponse(Post):
  model_config = ConfigDict(from_attributes=True)

  id: int
  user_id: int
  date_posted: datetime
  author: UserPublic

class PaginatedPostsResponse(BaseModel):
  posts: list[PostResponse]
  total: int
  skip: int
  limit: int
  has_more: bool


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(max_length=120)


class ResetPasswordRequest(BaseModel):
  token: str
  new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
  current_password: str
  new_password: str = Field(min_length=8)