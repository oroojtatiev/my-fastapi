# Project Instructions

## General

- Do NOT add or change anything without being explicitly asked.
- Do NOT invent structure or patterns — follow FastAPI official documentation.
- Choose PROD-like solutions with using Docker
- Follow `uv` documentation for package management.
- Answer in the same language as the previous question.
- Conversation in Russian language

## Project structure

- Layout: flat — modules live in the project root (`main.py`, `routers/`, `templates/`).
- Not an installable package (`[tool.uv] package = false` in `pyproject.toml`); distribution name `fastapi-course`.
- Imports are absolute from the project root: `from database import Base`, not `from .database import Base`.

## How to run

- Dev: `uv run uvicorn main:app --reload`
- Prod: `uv run uvicorn main:app` (or gunicorn with uvicorn workers)
- NEVER put `uvicorn.run()` or `main()` wrapper in application code. The `app` object is the entry point.

## Patterns

- Follow FastAPI official docs: https://fastapi.tiangolo.com/
- Use Pydantic models for request/response schemas.
- Prefer routers (`APIRouter`) for separating endpoints when the project grows.
- Use `pydantic-settings` for config (env variables) only if explicitly asked.

## Constraints

- No task runners (taskipy, poe) unless explicitly asked.
- No `[tool.uv.tasks]` — uv does not support it.
- `pyproject.toml` scripts section: only if the user requests an alias / entry point.
- Keep dependencies minimal — do not add packages proactively.
