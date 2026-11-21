# app

FastAPI blog with async SQLAlchemy/PostgreSQL and Alembic, JWT/argon2 auth, Jinja2/Tailwind templates, S3 profile pictures and email password reset.

## Running via Docker Compose

The project uses two compose files: `docker-compose.dev.yaml` (dev) and `docker-compose.yaml` (prod). The dev file has a non-standard name, so it must be specified explicitly with `-f`.

### Dev mode (with auto-reload)

```bash
docker compose -f docker-compose.dev.yaml up --build
```

In the background:

```bash
docker compose -f docker-compose.dev.yaml up -d --build
```

### Prod mode

```bash
docker compose up -d --build
```

### Stopping

```bash
docker compose -f docker-compose.dev.yaml down   # dev
docker compose down                              # prod
```

The application will be available at: [http://localhost:8000](http://localhost:8000)

## PostgreSQL

Credentials are in `.env`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`. The application itself uses `DATABASE_URL`.

Inside the container:

```bash
docker compose exec db psql -U <POSTGRES_USER> -d <POSTGRES_DB>                      # prod
docker compose -f docker-compose.dev.yaml exec db psql -U <POSTGRES_USER> -d <POSTGRES_DB>  # dev
```

From the host (port 5432 is published):

```bash
psql -h localhost -U <POSTGRES_USER> -d <POSTGRES_DB>
```

In `psql`: `\l` — databases, `\dt` — tables, `\q` — exit.

## S3

Profile pictures are stored in `S3_BUCKET_NAME` under `profile_pics/`. The fallback image is `profile_pics/default.jpeg`.

Required in `.env`: `S3_BUCKET_NAME`, `S3_REGION` (default `eu-north-1`), `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`. `S3_ENDPOINT_URL` is optional.

```bash
uv run python -m utils.s3 --check   # test credentials
uv run python -m utils.s3 --fill    # upload media/profile_pics/* to the bucket
```

## API overview

- REST: `/api/users`, `/api/posts`; auth via OAuth2 Bearer token from `/api/users/login`
- Pages: `/`, `/posts`, `/posts/{id}`, `/users/{id}/posts`
- Service: `/health` (DB check), `/docs` (Swagger UI)

## Project structure

Flat layout, absolute imports from the project root (`from database import Base`):

- `routers/` — API routers; `crud/` — DB queries
- `models.py`, `schemas.py`, `database.py` — models, Pydantic schemas, engine/session
- `templates/` — Jinja2 pages; `utils/` — images, email, S3 helpers
- `alembic/` — migrations; `tests/` — pytest suite

## Tests

```bash
uv run pytest
```

Tests expect PostgreSQL at host `db` and mock S3 with `moto`; run them where `db` is reachable.

## Alembic (DB migrations, async)

The project uses **async SQLAlchemy**. Therefore Alembic is initialized with an asynchronous template.

### Initialization

```bash
uv run alembic init -t async alembic
```

> The `-t async` option creates `env.py` with support for the async engine. Without it, migrations for the async engine will be configured incorrectly.

### Main commands

All commands are run via `uv run`.

| Command | What it does | Example/notes |
|---|---|---|
| `uv run alembic init -t async alembic` | Initializes Alembic with the asynchronous template | Creates the `alembic/` folder and the `alembic.ini` file |
| `uv run alembic revision -m "name"` | Creates an empty migration manually | Useful when autogeneration is not needed |
| `uv run alembic revision --autogenerate -m "name"` | Automatically generates a migration based on SQLAlchemy model changes | **The main approach**. Always review the generated code before applying |
| `uv run alembic upgrade head` | Applies all unapplied migrations up to `head` | Brings the DB up to date |
| `uv run alembic upgrade +1` | Applies exactly 1 next migration | Step-by-step upgrade |
| `uv run alembic downgrade -1` | Rolls back exactly 1 last migration | Step-by-step rollback |
| `uv run alembic downgrade <revision>` | Rolls back migrations to the specified revision | For example: `uv run alembic downgrade a1b2c3d4e5f6` |
| `uv run alembic downgrade base` | Rolls back all migrations completely | Returns the DB schema to an empty state |
| `uv run alembic current` | Shows the current applied revision | Helps to understand the DB state |
| `uv run alembic history` | Shows the full migration history (from oldest to newest) | Convenient for reviewing changes |
| `uv run alembic heads` | Shows all head revisions (`head`) | Needed when migrations branch |
| `uv run alembic show <revision>` | Shows the details of a specific migration | For example: `uv run alembic show head` |
| `uv run alembic stamp head` | Marks the DB as synchronized **without executing** SQL | Only if the DB schema already matches the models manually |
| `uv run alembic merge heads -m "merge"` | Merges several head revisions into one | Used when resolving branching conflicts |
| `uv run alembic check` | Checks whether there are model changes without a corresponding migration | Useful in CI so you don't forget to generate a migration |

### Important points

- **Async DB URL.** In `alembic.ini` or via `.env` in `env.py`, use an async driver, for example: `postgresql+asyncpg://user:pass@localhost/dbname`. The synchronous `psycopg2` will not work.
- **Always review migrations.** `--autogenerate` is not always ideal — especially renames, composite indexes, `UNIQUE`, type changes, JSON fields, etc.
- **The async template is mandatory.** If Alembic was initialized without `-t async`, it is better to recreate the `alembic/` structure with the async template or carefully adjust `env.py` for async operation.
