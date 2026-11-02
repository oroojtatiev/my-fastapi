from contextlib import asynccontextmanager
from fastapi import Request, HTTPException, status, Form, Depends, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from typing import Annotated
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from exceptions import http_exception_handler, request_validation_handler
from database import engine, get_db
from crud import get_user_or_404, get_posts_by_user, get_all_posts, get_post_or_404
from routers import users_router, posts_router
from templating import templates


@asynccontextmanager
async def lifespan(_app: FastAPI):
  # async with engine.begin() as conn:
  #   await conn.run_sync(Base.metadata.create_all)
  yield
  # Shutdown
  await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(posts_router, prefix="/api/posts", tags=["posts"])


@app.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
  try:
    await db.execute(text("SELECT 1"))
  except Exception as exc:
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from exc
  return {"status": "healthy"}


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
  all_posts, _ = await get_all_posts(db, 0, 10)

  return templates.TemplateResponse(
    request,
    "home.html",
    {"posts": all_posts, "title": "Home"},
  )


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
  user = await get_user_or_404(db, user_id)
  user_posts = await get_posts_by_user(db, user_id)

  return templates.TemplateResponse(
    request,
    "user_posts.html",
    {"posts": user_posts, "user": user, "title": f"{user.username}'s Posts"},
  )


@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
  post = await get_post_or_404(db, post_id)

  return templates.TemplateResponse(request, "post.html", {
    "post": post,
    "title": post.title,
  })


@app.get("/posts/{post_id}/update", include_in_schema=False)
async def update_post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
  post = await get_post_or_404(db, post_id)

  return templates.TemplateResponse(request, "update_post.html", {
    "post": post,
    "title": f"Update post: {post_id}"
  })


@app.post("/posts/{post_id}/update", include_in_schema=False)
async def update_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)], title: str = Form(...),
  content: str = Form(...)):
  post = await get_post_or_404(db, post_id)

  post.title = title
  post.content = content
  await db.commit()

  return RedirectResponse(url=f"/posts/{post_id}", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/posts/{post_id}/delete", include_in_schema=False)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
  post = await get_post_or_404(db, post_id)

  await db.delete(post)
  await db.commit()

  return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# Exception handlers #############################################################################

@app.exception_handler(HTTPException)
async def handle_http_exception(request, exc):
  return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def handle_request_validation(request, exception):
  return await request_validation_handler(request, exception)
