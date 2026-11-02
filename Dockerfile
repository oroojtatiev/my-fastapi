FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# libpq is required by pure psycopg (without the [binary] extra); there is nothing to build — all dependencies come as wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install uv (version pinned for reproducible builds)
COPY --from=ghcr.io/astral-sh/uv:0.12.4 /uv /uvx /usr/local/bin/

# Copy dependencies
COPY pyproject.toml uv.lock ./

# Dependencies: prod by default (--no-dev), dev — via --build-arg UV_SYNC_FLAGS=""
# The uv cache is mounted rather than written into the image layer; UV_LINK_MODE=copy is required with a cache mount
# (the cache and .venv are on different filesystems, so a hardlink is impossible)
ARG UV_SYNC_FLAGS="--no-dev"
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen ${UV_SYNC_FLAGS}

# Copy the code
COPY . .

# Unprivileged user. The media/ directory is not included in the image (see .dockerignore),
# so we create it: the named volume inherits the owner and writes from app work.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media/profile_pics \
    && chown -R app:app /app
USER app

EXPOSE 8000

# Default for prod (dev overrides command in docker-compose.dev.yaml)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]