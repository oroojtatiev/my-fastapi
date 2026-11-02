# app

## Запуск через Docker Compose

Проект использует два compose-файла: `docker-compose.dev.yaml` (dev) и `docker-compose.yaml` (prod). Dev-файл имеет нестандартное имя, поэтому его нужно указывать явно через `-f`.

### Dev режим (с автоперезагрузкой)

```bash
docker compose -f docker-compose.dev.yaml up --build
```

В фоне:

```bash
docker compose -f docker-compose.dev.yaml up -d --build
```

### Prod режим

```bash
docker compose up -d --build
```

### Остановка

```bash
docker compose -f docker-compose.dev.yaml down   # dev
docker compose down                              # prod
```

Приложение будет доступно по адресу: [http://localhost:8000](http://localhost:8000)

## Alembic (миграции БД, async)

Проект использует **async SQLAlchemy**. Поэтому Alembic инициализируется с асинхронным шаблоном.

### Инициализация

```bash
uv run alembic init -t async alembic
```

> Опция `-t async` создаст `env.py` с поддержкой асинхронного движка. Без неё миграции под async-движок настроятся некорректно.

### Основные команды

Все команды запускаются через `uv run`.

| Команда | Что делает | Пример/примечания |
|---|---|---|
| `uv run alembic init -t async alembic` | Инициализирует Alembic с асинхронным шаблоном | Создаст папку `alembic/` и файл `alembic.ini` |
| `uv run alembic revision -m "название"` | Создаёт пустую миграцию вручную | Полезно, если не нужна автогенерация |
| `uv run alembic revision --autogenerate -m "название"` | Автоматически генерирует миграцию на основе изменений моделей SQLAlchemy | **Основной способ**. Обязательно проверяй сгенерированный код перед применением |
| `uv run alembic upgrade head` | Применяет все неприменённые миграции до `head` | Приводит БД в актуальное состояние |
| `uv run alembic upgrade +1` | Применяет ровно 1 следующую миграцию | Пошаговый накат |
| `uv run alembic downgrade -1` | Откатывает ровно 1 последнюю миграцию | Пошаговый откат |
| `uv run alembic downgrade <revision>` | Откатывает миграции до указанной ревизии | Например: `uv run alembic downgrade a1b2c3d4e5f6` |
| `uv run alembic downgrade base` | Полностью откатывает все миграции | Возвращает схему БД в пустое состояние |
| `uv run alembic current` | Показывает текущую применённую ревизию | Помогает понять состояние БД |
| `uv run alembic history` | Показывает полную историю миграций (от старых к новым) | Удобен для обзора изменений |
| `uv run alembic heads` | Показывает все головные ревизии (`head`) | Нужен при ветвлении миграций |
| `uv run alembic show <revision>` | Показывает подробности конкретной миграции | Например: `uv run alembic show head` |
| `uv run alembic stamp head` | Помечает БД как синхронизированную, **не выполняя** SQL | Только если схема БД уже вручную соответствует моделям |
| `uv run alembic merge heads -m "объединение"` | Объединяет несколько головных ревизий в одну | Используется при разрешении конфликтов ветвления |
| `uv run alembic check` | Проверяет, есть ли изменения в моделях без соответствующей миграции | Полезен в CI, чтобы не забыть сгенерировать миграцию |

### Важные моменты

- **Асинхронный URL БД.** В `alembic.ini` или через `.env` в `env.py` используй асинхронный драйвер, например: `postgresql+asyncpg://user:pass@localhost/dbname`. Синхронный `psycopg2` не подойдёт.
- **Обязательно ревью миграций.** `--autogenerate` не всегда идеален — особенно переименования, составные индексы, `UNIQUE`, изменения типов, поля JSON и др.
- **Async-шаблон обязателен.** Если Alembic был инициализирован без `-t async`, лучше пересоздать структуру `alembic/` с async-шаблоном или аккуратно поправить `env.py` под асинхронную работу.# fastapi-course
