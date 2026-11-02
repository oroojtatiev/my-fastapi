FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# libpq нужен чистому psycopg (без extra [binary]); собирать нечего — все зависимости приходят колёсами
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv (версия закреплена для воспроизводимых сборок)
COPY --from=ghcr.io/astral-sh/uv:0.12.4 /uv /uvx /usr/local/bin/

# Копируем зависимости
COPY pyproject.toml uv.lock ./

# Зависимости: prod по умолчанию (--no-dev), dev — через --build-arg UV_SYNC_FLAGS=""
# Кэш uv монтируется, а не пишется в слой образа; UV_LINK_MODE=copy обязателен при cache mount
# (кэш и .venv на разных ФС, hardlink невозможен)
ARG UV_SYNC_FLAGS="--no-dev"
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen ${UV_SYNC_FLAGS}

# Копируем код
COPY . .

# Непривилегированный пользователь. Каталог media/ в образ не попадает (см. .dockerignore),
# поэтому создаём его: named volume наследует владельца и запись от app работает.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media/profile_pics \
    && chown -R app:app /app
USER app

EXPOSE 8000

# По умолчанию для prod (dev переопределяет command в docker-compose.dev.yaml)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]