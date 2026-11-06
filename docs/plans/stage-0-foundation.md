# Stage 0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Получить запускаемый каркас БаЛаЛайки: backend с health endpoints, PostgreSQL/Alembic, базовый Jinja-экран и Docker Compose, который поднимается на чистой машине.

**Architecture:** Один FastAPI-монолит по ADR-002/003. На этапе 0 создаются только инфраструктурные слои: настройки, логирование, ошибки, БД, Redis, шаблоны и compose. Доменные модули, auth и upload добавляются на следующих этапах.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic, PostgreSQL 16, Redis 7, Jinja2, precompiled Tailwind CSS, Docker Compose, nginx.

**Spec:** `docs/decisions.md`, `docs/architecture.md`, `docs/ROADMAP.md`

## Global Constraints

- Python 3.12+, Poetry 2.2, PostgreSQL 16, Redis 7, Node.js 20+.
- Backend-код — только в `backend/app/`; шаблоны и статика — в `frontend/`; инфраструктура — в `deploy/`.
- Секреты и `.env` не коммитятся. `.env.example` содержит только безопасные примеры.
- Схема БД меняется только через Alembic; `--autogenerate` в деплое запрещён.
- Ошибки — единый JSON-формат; недоступный объект — `404`; внутренние детали не раскрываются.
- UI на русском, идентификаторы — на английском.
- TDD для конфигурации, ошибок, readiness и миграций.
- Коммиты — Conventional Commits, по одному на задачу.
- `make` может отсутствовать на Windows; в этом случае использовать команды `poetry run ...` из `backend/`.
- Ветка: `feature/foundation` от `develop`.

## Review Focus

- Отсутствует обязательная env-переменная: приложение должно падать при старте с понятным сообщением, не печатая секрет.
- PostgreSQL недоступен: `/readyz` возвращает `503` за ограниченное время, а не `500`, не зависает и не раскрывает stacktrace.
- Redis недоступен при живом PostgreSQL: `/readyz` возвращает `503` с отдельным статусом каждой зависимости.
- Клиент прислал небезопасный `X-Request-ID`: значение заменяется на UUID, ответ не содержит управляющих символов.
- Контейнер запущен из `backend/`: шаблоны и CSS находятся по путям `/app/frontend/...`, а не только на машине разработчика.

---

## File Map

```text
backend/
  pyproject.toml, poetry.lock, poetry.toml
  Makefile
  Dockerfile
  alembic.ini
  app/
    main.py                 # create_app, middleware, handlers, static, routers
    core/
      config.py             # Settings, get_settings
      errors.py             # AppError, NotFoundError, handlers
      logging.py            # JSON formatter, request_id context
      middleware.py         # RequestIDMiddleware
      db.py                 # engine, sessionmaker, get_session, check_database
      redis.py              # client, check_redis
    web/
      router.py             # GET /
      templating.py         # get_templates, Jinja2Templates
    api/
      health.py             # /healthz, /readyz (infrastructure, not /api/v1)
  alembic/
    env.py
    script.py.mako
    versions/0001_enable_pg_trgm.py
  tests/
    conftest.py
    unit/test_config.py
    unit/test_errors.py
    unit/test_readiness.py
    integration/test_health.py
    integration/test_home.py
    integration/test_migrations.py
frontend/
  package.json, package-lock.json
  tailwind.config.js
  static/src/input.css
  static/css/app.css
  templates/base.html
  templates/pages/home.html
deploy/
  docker-compose.yml
  docker-compose.dev.yml    # local-only port publishing for postgres/redis
  .env.example
  nginx/default.conf
```

Не входят в этап 0: auth, users, channels, upload, worker, ARQ, MinIO-клиент в приложении, UI-экраны кроме главной, `deploy/deploy.sh`.

Feature-модули (`auth`, `users`, `channels`, `videos`, `media`, `engagement`, `playlists`, `search`, `moderation`, `admin`) создаются на своих этапах. Этап 0 фиксирует только `core`, `api` и `web`, чтобы не добавлять пустые заглушки.

---

## Task 0: Branch, plan commit and ROADMAP status

**Files:**
- Add: `docs/plans/stage-0-foundation.md`
- Modify: `docs/ROADMAP.md`

**Interfaces:**
- Produces: ветка `feature/foundation` от `develop`.
- Produces: этап 0 в ROADMAP со статусом `в работе`.
- Produces: план закоммичен до первой правки кода.

- [x] **Step 1: Создать ветку**

```bash
git switch develop
git switch -c feature/foundation
```

- [x] **Step 2: Перевести этап 0 в статус «в работе»**

В `docs/ROADMAP.md` заменить пустой `**Статус:**` этапа 0 на `**Статус:** в работе`.

- [x] **Step 3: Закоммитить план и статус**

```bash
git add docs/plans/stage-0-foundation.md docs/ROADMAP.md
git commit -m "docs: start foundation stage and add implementation plan"
```

---

## Task 1: Backend skeleton, config, errors and `/healthz`

**Files:**
- Move: `pyproject.toml`, `poetry.lock`, `poetry.toml` → `backend/`
- Create: `.gitattributes`
- Modify: `.gitignore`
- Create: `backend/Makefile`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/errors.py`
- Create: `backend/app/core/logging.py`
- Create: `backend/app/core/middleware.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/unit/test_config.py`
- Create: `backend/tests/unit/test_errors.py`
- Create: `backend/tests/integration/test_health.py`

**Interfaces:**
- Produces: `Settings` с полями `app_env`, `log_level`, `database_url`, `redis_url`, `secret_key: SecretStr`, `public_base_url`, `session_cookie_secure`, `templates_dir: Path`, `static_dir: Path`.
- Produces: `get_settings() -> Settings`.
- Produces: `AppError(code: str, message: str, status_code: int = 500, details: object | None = None)`.
- Produces: `NotFoundError(message: str, details: object | None = None)` с `code="not_found"` и `status_code=404`.
- Produces: `register_exception_handlers(app: FastAPI) -> None`.
- Produces: `RequestIDMiddleware`.
- Produces: `create_app() -> FastAPI` и модульный `app = create_app()` в `app.main`.
- Produces: `app/__init__.py` реэкспортирует `create_app`.
- Produces: `GET /healthz -> 200 {"status": "ok"}`.

- [ ] **Step 1: Перенести Poetry-конфиг и настроить backend**

`pyproject.toml` и `poetry.lock` отслеживаются Git, поэтому переносятся через `git mv`. `poetry.toml` в `.gitignore` (`/poetry.toml`), поэтому `git mv` для него невозможен: используйте `Move-Item` в PowerShell или `mv` в POSIX-оболочке.

```powershell
git mv pyproject.toml backend/pyproject.toml
git mv poetry.lock backend/poetry.lock
Move-Item poetry.toml backend/poetry.toml
```

```bash
# POSIX-эквивалент
git mv pyproject.toml backend/pyproject.toml
git mv poetry.lock backend/poetry.lock
mv poetry.toml backend/poetry.toml
```

Добавить в `.gitignore`:

```text
/backend/poetry.toml
```

В `backend/pyproject.toml`:

- убрать `readme = "README.md"` (корневой README описывает проект);
- добавить `[tool.poetry] packages = [{ include = "app" }]`;
- добавить `[tool.ruff]` с `target-version = "py312"`, `line-length = 100`, `select = ["E", "F", "I", "UP", "B"]`;
- добавить `[tool.mypy]` с `python_version = "3.12"`, `disallow_untyped_defs = true`, `warn_unused_ignores = true`;
- добавить `[tool.pytest.ini_options]` с `asyncio_mode = "auto"`, `testpaths = ["tests"]`.

- [ ] **Step 2: Добавить зависимости**

```bash
cd backend
poetry config virtualenvs.in-project true --local
poetry env use 3.12
poetry add "fastapi>=0.115,<1.0" "uvicorn[standard]>=0.30,<1.0" "pydantic-settings>=2.5,<3.0"
poetry add --group dev "pytest>=8.0,<9.0" "pytest-asyncio>=0.24,<1.0" "httpx>=0.27,<1.0" "ruff>=0.6,<1.0" "mypy>=1.11,<2.0"
poetry install
```

`poetry config --local` создаёт игнорируемый `backend/poetry.toml`. Корневой `.venv` после переноса конфига считается stale: не используйте его для backend-команд. После проверки его можно удалить вручную (`Remove-Item -Recurse -Force .venv` в PowerShell или `rm -rf .venv` в POSIX).

- [ ] **Step 3: Написать падающие тесты конфигурации и health**

`backend/tests/conftest.py`:

```python
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
```

`backend/tests/unit/test_config.py`:

```python
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)
    assert "database_url" in str(error.value)


def test_session_cookie_secure_false_is_parsed(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    settings = Settings(_env_file=None)
    assert settings.session_cookie_secure is False
    assert "test-secret" not in repr(settings)
```

`backend/tests/unit/test_errors.py`:

```python
from app.core.errors import NotFoundError


def test_app_error_has_code_and_status():
    error = NotFoundError(message="Видео не найдено")
    assert error.code == "not_found"
    assert error.status_code == 404


async def test_unhandled_error_is_generic():
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    app = create_app()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret-detail")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret-detail" not in response.text


async def test_unknown_route_uses_error_format():
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
```

`backend/tests/integration/test_health.py`:

```python
from httpx import ASGITransport, AsyncClient


async def test_healthz_returns_ok():
    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


async def test_request_id_is_echoed():
    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz", headers={"X-Request-ID": "request-123"})

    assert response.headers["X-Request-ID"] == "request-123"


async def test_unsafe_request_id_is_replaced():
    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz", headers={"X-Request-ID": "x" * 129})

    assert response.headers["X-Request-ID"] != "x" * 129
    assert len(response.headers["X-Request-ID"]) == 36
```

- [ ] **Step 4: Запустить тесты и убедиться, что они падают**

```bash
cd backend
poetry run pytest tests/unit/test_config.py tests/unit/test_errors.py tests/integration/test_health.py -v
```

Ожидается: `ModuleNotFoundError` или `ImportError` для `app.core.config`.

- [ ] **Step 5: Реализовать `Settings` и `get_settings()`**

`backend/app/core/config.py` должен:

- читать env через `pydantic-settings`, локальный `env_file=".env"` в `backend/`;
- использовать `SecretStr` для `SECRET_KEY`;
- вычислять `templates_dir` и `static_dir` от `Path(__file__).resolve().parents[3] / "frontend"`;
- кэшировать настройки через `@lru_cache`.

- [ ] **Step 6: Реализовать ошибки, request ID и JSON-логи**

`backend/app/core/errors.py`:

- `AppError` с `code`, `message`, `status_code=500`, `details=None`;
- `NotFoundError` с `code="not_found"`, `status_code=404`;
- `register_exception_handlers(app)`:
  - `AppError` → `{"error": {"code", "message", "details", "request_id"}}`;
  - `RequestValidationError` → `code="validation_error"`, `status_code=422`, `details=jsonable_encoder(exc.errors())`;
  - `StarletteHTTPException` → `code="http_error"`, сохраняет статус;
  - `Exception` → `code="internal_error"`, `status_code=500`, логирует исключение без деталей в ответе.

`backend/app/core/middleware.py`:

- `RequestIDMiddleware` читает `X-Request-ID`;
- принимает значение длиной 1–128 символов без управляющих символов, иначе генерирует UUID4;
- кладёт значение в `request.state.request_id` и `ContextVar`;
- добавляет `X-Request-ID` в ответ.

`backend/app/core/logging.py`:

- настраивает root logger;
- JSON-формат с полями `timestamp`, `level`, `logger`, `message`, `request_id`;
- не логирует секреты.

`backend/app/main.py`:

- `create_app()` создаёт FastAPI, подключает middleware, handlers и health-router;
- `app = create_app()` на уровне модуля, чтобы работал `uvicorn app.main:app`;
- `backend/app/__init__.py` реэкспортирует `create_app` через `__all__`.

`GET /healthz` возвращает `{"status": "ok"}`.

- [ ] **Step 7: Добавить `.gitattributes` и `Makefile`**

`.gitattributes`:

```text
*.sh text eol=lf
```

`backend/Makefile`:

```make
check:
	poetry run ruff check .
	poetry run ruff format --check .
	poetry run mypy app
	poetry run pytest
```

- [ ] **Step 8: Запустить тесты, линтеры и mypy**

```bash
cd backend
poetry run pytest tests/unit/test_config.py tests/unit/test_errors.py tests/integration/test_health.py -v
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy app
```

Ожидается: все тесты PASS, Ruff и mypy без ошибок.

- [ ] **Step 9: Коммиты**

```bash
git add .gitattributes .gitignore backend/pyproject.toml backend/poetry.lock backend/Makefile
git commit -m "chore: move backend config and add tooling"

git add backend/app backend/tests
git commit -m "feat: add backend skeleton, errors and health endpoint"
```

---

## Task 2: Database, Redis, readiness and initial migration

**Files:**
- Create: `backend/app/core/db.py`
- Create: `backend/app/core/redis.py`
- Modify: `backend/app/api/health.py` (дополнить `/readyz`)
- Modify: `backend/app/main.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_enable_pg_trgm.py`
- Create: `backend/tests/unit/test_readiness.py`
- Create: `backend/tests/integration/test_migrations.py`

**Interfaces:**
- Produces: `get_engine() -> AsyncEngine`, `get_sessionmaker() -> async_sessionmaker[AsyncSession]`, `get_session() -> AsyncIterator[AsyncSession]`, `check_database() -> None`.
- Produces: `Base` — `DeclarativeBase` для Alembic.
- Produces: `get_redis() -> Redis`, `check_redis() -> None`.
- Produces: `GET /readyz -> 200 {"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}`.
- Produces: `GET /readyz -> 503 {"status": "degraded", "checks": {"postgres": "error", "redis": "ok"}}` при отказе зависимости.

- [ ] **Step 1: Добавить зависимости**

```bash
cd backend
poetry add "sqlalchemy[asyncio]>=2.0.35,<2.1" "asyncpg>=0.29,<1.0" "alembic>=1.13,<2.0" "redis>=5.0,<6.0"
poetry add --group dev "testcontainers[postgres]>=4.8,<5.0" "psycopg2-binary>=2.9,<3.0"
```

- [ ] **Step 2: Написать падающие тесты readiness**

`backend/tests/unit/test_readiness.py`:

```python
from httpx import ASGITransport, AsyncClient

from app.api import health


async def test_readyz_ok(monkeypatch):
    async def ok() -> None:
        return None

    monkeypatch.setattr(health, "check_database", ok)
    monkeypatch.setattr(health, "check_redis", ok)

    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}


async def test_readyz_reports_database_failure(monkeypatch):
    async def fail() -> None:
        raise RuntimeError("db down")

    async def ok() -> None:
        return None

    monkeypatch.setattr(health, "check_database", fail)
    monkeypatch.setattr(health, "check_redis", ok)

    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["checks"]["postgres"] == "error"
    assert "db down" not in response.text


async def test_readyz_reports_redis_failure(monkeypatch):
    async def ok() -> None:
        return None

    async def fail() -> None:
        raise RuntimeError("redis down")

    monkeypatch.setattr(health, "check_database", ok)
    monkeypatch.setattr(health, "check_redis", fail)

    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["checks"] == {"postgres": "ok", "redis": "error"}
    assert "redis down" not in response.text
```

- [ ] **Step 3: Написать падающий тест миграции**

`backend/tests/integration/test_migrations.py`:

```python
import asyncio

import asyncpg
from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

from app.core.config import get_settings


def test_alembic_upgrade_enables_pg_trgm(monkeypatch):
    with PostgresContainer("postgres:16-alpine") as postgres:
        url = postgres.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql+asyncpg"
        )
        monkeypatch.setenv("DATABASE_URL", url)
        get_settings.cache_clear()

        config = Config("alembic.ini")
        command.upgrade(config, "head")

        assert asyncio.run(_extension_exists(url)) is True

    get_settings.cache_clear()


async def _extension_exists(url: str) -> bool:
    connection = await asyncpg.connect(
        url.replace("postgresql+asyncpg://", "postgresql://")
    )
    try:
        row = await connection.fetchrow(
            "SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'"
        )
        return row is not None
    finally:
        await connection.close()
```

- [ ] **Step 4: Запустить тесты и убедиться, что они падают**

```bash
cd backend
poetry run pytest tests/unit/test_readiness.py tests/integration/test_migrations.py -v
```

Ожидается: `/readyz` возвращает 404, `alembic.ini` отсутствует.

- [ ] **Step 5: Реализовать `db.py` и `redis.py`**

`db.py`:

- `Base(DeclarativeBase)` без создания engine на уровне модуля;
- `get_engine()` создаёт `create_async_engine(settings.database_url, pool_pre_ping=True, connect_args={"timeout": 3})` лениво и кэширует;
- `async_sessionmaker(engine, expire_on_commit=False)`;
- `get_session()` отдаёт сессию и закрывает её в `finally`;
- `check_database()` выполняет `SELECT 1`.

`redis.py`:

- `from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)`;
- `check_redis()` выполняет `PING` и поднимает `RuntimeError` при неуспехе.

- [ ] **Step 6: Реализовать `/readyz`**

`backend/app/api/health.py`:

- вызывает `check_database()` и `check_redis()` независимо;
- каждый отказ логирует с `request_id`, но не возвращает текст ошибки;
- формирует `checks` и `status`;
- возвращает `JSONResponse` с `200` или `503`.

- [ ] **Step 7: Инициализировать Alembic**

```bash
cd backend
poetry run alembic init -t async alembic
```

В `backend/alembic.ini` оставить `sqlalchemy.url =` пустым.

В `backend/alembic/env.py`:

- читать URL **только** из `get_settings().database_url` (то есть из `DATABASE_URL`), не из `alembic.ini` и не из CLI;
- импортировать `Base` из `app.core.db`; модуль не должен создавать engine при импорте;
- не выполнять `autogenerate` автоматически.

Создать первую ревизию `0001_enable_pg_trgm`:

```python
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
```

- [ ] **Step 8: Запустить тесты, линтеры и миграцию на чистой БД**

```bash
cd backend
poetry run pytest tests/unit/test_readiness.py tests/integration/test_migrations.py -v
poetry run ruff check .
poetry run mypy app
```

Ожидается: readiness-тесты PASS, миграция включает `pg_trgm`.

- [ ] **Step 9: Коммит**

```bash
git add backend/app backend/alembic backend/alembic.ini backend/tests backend/pyproject.toml backend/poetry.lock
git commit -m "feat: add readiness checks and initial migration"
```

---

## Task 3: Jinja base layout and Tailwind build

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/package-lock.json` (генерируется npm)
- Create: `frontend/tailwind.config.js`
- Create: `frontend/static/src/input.css`
- Create: `frontend/static/css/app.css` (генерируется сборкой)
- Create: `frontend/templates/base.html`
- Create: `frontend/templates/pages/home.html`
- Modify: `backend/app/main.py`
- Create: `backend/app/web/__init__.py`
- Create: `backend/app/web/router.py`
- Create: `backend/app/web/templating.py`
- Create: `backend/tests/integration/test_home.py`

**Interfaces:**
- Produces: `GET / -> 200 text/html`, содержит `БаЛаЛайка` и `/static/css/app.css`.
- Produces: `GET /static/css/app.css -> 200 text/css`.
- Produces: `create_app()` монтирует `StaticFiles` по `/static`; шаблоны отдаёт `get_templates()` из `app.web.templating`.

- [ ] **Step 1: Добавить Jinja2 и создать frontend-конфиг**

```bash
cd backend
poetry add "jinja2>=3.1,<4.0"
```

`frontend/package.json`:

```json
{
  "private": true,
  "scripts": {
    "build:css": "tailwindcss -i ./static/src/input.css -o ./static/css/app.css --minify",
    "watch:css": "tailwindcss -i ./static/src/input.css -o ./static/css/app.css --watch"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0"
  }
}
```

`frontend/tailwind.config.js`:

```js
module.exports = {
  content: ["./templates/**/*.html"],
  theme: { extend: {} },
  plugins: [],
};
```

`frontend/static/src/input.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 2: Собрать CSS**

```bash
cd frontend
npm install
npm run build:css
```

Ожидается: создан `frontend/static/css/app.css`, `package-lock.json` закоммичен вместе с проектом.

- [ ] **Step 3: Написать падающий тест главной**

`backend/tests/integration/test_home.py`:

```python
from httpx import ASGITransport, AsyncClient


async def test_home_renders_base_layout():
    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "БаЛаЛайка" in response.text
    assert "/static/css/app.css" in response.text


async def test_compiled_css_is_served():
    from app.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/static/css/app.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
```

- [ ] **Step 4: Запустить тест и убедиться, что он падает**

```bash
cd backend
poetry run pytest tests/integration/test_home.py -v
```

Ожидается: `404` для `/`.

- [ ] **Step 5: Реализовать шаблоны и маршрут**

`backend/app/web/templating.py`:

- `get_templates()` с `@lru_cache`;
- возвращает `Jinja2Templates(directory=str(get_settings().templates_dir))`;
- не создаёт шаблоны на уровне импорта.

`base.html`:

- `<!doctype html>`, `lang="ru"`;
- topbar с логотипом `БаЛаЛайка` и ссылкой на `/`;
- `<link rel="stylesheet" href="{{ url_for('static', path='/css/app.css') }}">`;
- блок `content`.

`home.html`:

- extends `base.html`;
- заголовок и пустое состояние «Здесь появятся видео».

`backend/app/web/router.py`:

- `GET /` берёт `templates = get_templates()` и возвращает `templates.TemplateResponse(request=request, name="pages/home.html", context={"title": "Главная"})`.

`backend/app/main.py`:

- монтирует `StaticFiles(directory=str(settings.static_dir))` по `/static`;
- подключает web-router.

- [ ] **Step 6: Запустить тесты, проверить сборку**

```bash
cd backend
poetry run pytest tests/integration/test_home.py -v
cd ../frontend
npm run build:css
```

Ожидается: тесты PASS, сборка CSS завершается без ошибок.

- [ ] **Step 7: Коммит**

```bash
git add frontend backend/app backend/tests
git commit -m "feat: add Jinja layout and Tailwind build"
```

---

## Task 4: Compose, nginx, env template and README

**Files:**
- Create: `backend/Dockerfile`
- Create: `.dockerignore`
- Create: `deploy/docker-compose.yml`
- Create: `deploy/docker-compose.dev.yml`
- Create: `deploy/nginx/default.conf`
- Create: `deploy/.env.example`
- Create: `README.md`

**Interfaces:**
- Produces: `docker compose up -d --wait` поднимает `nginx`, `backend`, `postgres`, `redis`, `minio`, `minio-init`, `migrate`.
- Produces: one-shot `migrate` и `minio-init` завершаются с кодом `0`; backend стартует только после успешной миграции.
- Produces: снаружи доступен только nginx на `:80`.
- Produces: `GET /`, `/docs`, `/healthz`, `/readyz` через nginx.

- [ ] **Step 1: Создать Dockerfile**

`backend/Dockerfile`:

- base `python:3.12-slim`;
- установить Poetry 2.2.1, `ENV POETRY_VIRTUALENVS_CREATE=false`;
- скопировать `backend/pyproject.toml`, `backend/poetry.lock`, выполнить `poetry install --only main --no-root`;
- скопировать `backend/app`, `backend/alembic`, `backend/alembic.ini` в `/app/backend`;
- скопировать `frontend` в `/app/frontend`;
- `WORKDIR /app/backend`, `PYTHONPATH=/app/backend`;
- создать non-root пользователя;
- `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

- [ ] **Step 2: Создать `.dockerignore`**

Исключить `.git`, `.venv`, `node_modules`, `__pycache__`, `.env`, `.env.*`, `*.log`, `docs`, `ai-docs`.

- [ ] **Step 3: Создать `.env.example`**

```dotenv
APP_ENV=dev
LOG_LEVEL=INFO
POSTGRES_DB=balalayka
POSTGRES_USER=balalayka
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+asyncpg://balalayka:change-me@postgres:5432/balalayka
REDIS_URL=redis://redis:6379/0
MINIO_ROOT_USER=balalayka
MINIO_ROOT_PASSWORD=change-me-minio
PUBLIC_BASE_URL=http://localhost
SECRET_KEY=change-me-generate-with-openssl
SESSION_COOKIE_SECURE=false
```

`DATABASE_URL` в примере — для compose. Для локального backend в `backend/.env` заменить хосты на `localhost` и использовать те же логин/пароль. Compose всё равно переопределяет `DATABASE_URL` и `REDIS_URL` контейнерными значениями.

- [ ] **Step 4: Создать compose**

`deploy/docker-compose.yml`:

- `postgres`: `postgres:16-alpine`, volume `pgdata`, healthcheck:

```yaml
test: ["CMD-SHELL", "pg_isready -h 127.0.0.1 -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
interval: 5s
timeout: 5s
retries: 10
start_period: 10s
```

- `redis`: `redis:7-alpine`, `--appendonly yes`, volume `redisdata`, healthcheck `redis-cli ping` с `interval: 5s`, `timeout: 3s`, `retries: 10`, `start_period: 5s`.
- `minio`: `minio/minio:RELEASE.2024-10-13T13-34-11Z`, `command: server /data --console-address ":9001"`, `env_file: .env`, volume `miniodata`, healthcheck `curl -fsS http://127.0.0.1:9000/minio/health/live`.
- `minio-init`: one-shot `minio/mc:RELEASE.2024-11-21T17-21-54Z`, `depends_on: minio: service_healthy`, `restart: "no"`, ждёт MinIO и создаёт бакеты `incoming-videos`, `media`, `raw-videos`:

```yaml
entrypoint: >
  /bin/sh -c "
  until mc alias set local http://minio:9000 $$MINIO_ROOT_USER $$MINIO_ROOT_PASSWORD; do sleep 2; done;
  mc mb --ignore-existing local/incoming-videos local/media local/raw-videos;
  "
```

Перед коммитом обязательно проверить выбранные теги и наличие инструментов:

```bash
docker pull minio/minio:RELEASE.2024-10-13T13-34-11Z
docker run --rm --entrypoint /bin/sh minio/minio:RELEASE.2024-10-13T13-34-11Z -c 'command -v curl; command -v wget; command -v sh'
docker pull minio/mc:RELEASE.2024-11-21T17-21-54Z
docker run --rm --entrypoint /bin/sh minio/mc:RELEASE.2024-11-21T17-21-54Z -c 'command -v sh; command -v mc'
```

Если тег недоступен или `curl`/`wget` отсутствует, заменить на проверенный release-тег и healthcheck-инструмент, зафиксировать это в compose. `latest` запрещён.

Lifecycle и scoped-пользователь добавляются на этапе 2.

- `migrate`: build context `..`, `dockerfile: backend/Dockerfile`, тот же образ `image: balalayka-backend:local`, что и backend; `env_file: .env`, `environment` с `DATABASE_URL` из `${POSTGRES_USER}`, `${POSTGRES_PASSWORD}` и `${POSTGRES_DB}`, `restart: "no"`, `depends_on: postgres: service_healthy`, bounded retry:

```yaml
command: >
  /bin/sh -c "
  for i in 1 2 3 4 5 6 7 8 9 10; do
    alembic upgrade head && exit 0;
    echo 'migration failed, retry' >&2;
    sleep 3;
  done;
  exit 1;
  "
```

- `backend`: build context `..`, `dockerfile: backend/Dockerfile`, `env_file: .env`, `DATABASE_URL` и `REDIS_URL` переопределяются контейнерными значениями, зависит от `redis`, `minio` и `migrate: service_completed_successfully`; healthcheck:

```yaml
test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
interval: 10s
timeout: 3s
retries: 5
start_period: 10s
```

- `nginx`: `nginx:1.27-alpine`, `ports: ["80:80"]`, volume `./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro`, зависит от backend healthy.
- `restart: unless-stopped` для `postgres`, `redis`, `minio`, `backend`, `nginx`; one-shot `migrate` и `minio-init` — `restart: "no"`.
- Наружу не публиковать порты PostgreSQL, Redis и MinIO.
- Один общий network; публикация портов отсутствует, кроме nginx.
- `docker compose up -d --wait` должен оставить `migrate` и `minio-init` в состоянии `exited (0)`, а долгоживущие сервисы — `running/healthy`. Если версия Compose возвращает ошибку только из-за завершившихся one-shot-сервисов, использовать `docker compose up -d` и bounded-ожидание `/healthz`; это поведение фиксируется в README.

`deploy/docker-compose.dev.yml` (только для запуска backend на хосте, не для деплоя):

```yaml
services:
  postgres:
    ports:
      - "127.0.0.1:5432:5432"
  redis:
    ports:
      - "127.0.0.1:6379:6379"
```

Dev-override не используется в production-командах и не должен попадать в деплой.

- [ ] **Step 5: Создать nginx-конфиг**

`deploy/nginx/default.conf`:

- `upstream backend { server backend:8000; }`;
- `location / { proxy_pass http://backend; proxy_set_header Host $host; }`;
- `location /media/ { proxy_pass http://backend; }`;
- `location /static/ { proxy_pass http://backend; }`;
- `location /incoming-videos/ { proxy_pass http://minio:9000; proxy_set_header Host $http_host; client_max_body_size 500m; proxy_request_buffering off; }`.

- [ ] **Step 6: Создать README-каркас**

README содержит:

- описание проекта и стек;
- структуру репозитория;
- backend: `poetry env use 3.12`, `poetry install`, `poetry run ...`, без привязки к пути `.venv`;
- локальный `backend/.env`: скопировать `deploy/.env.example`, заменить хосты БД/Redis на `localhost`; для портов использовать `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis`;
- предупреждение, что корневой `.venv` stale и backend-команды выполняются из `backend/`;
- frontend: `npm ci`, `npm run build:css`, `npm run watch:css`;
- быстрый старт через compose:

```bash
cp deploy/.env.example deploy/.env
cd deploy
docker compose up -d --wait
```

- поведение one-shot `migrate`/`minio-init` и fallback, если `--wait` не поддерживает их завершение;
- проверки: `http://localhost/`, `/docs`, `/healthz`, `/readyz`;
- снаружи открыт только nginx `:80`; PostgreSQL, Redis и MinIO — internal;
- Windows: использовать `curl.exe`, а не алиас `curl` из PowerShell;
- `docker compose down -v` удаляет volumes и все данные; выполнять только для одноразового стенда;
- `/docs`: Swagger UI по умолчанию загружает JS/CSS с CDN; при отсутствии интернета использовать `/openapi.json` или локальные ассеты (вне stage 0);
- AI artifacts: экспорт сессии прикладывается к архиву, промпты в git не добавляются (ADR-016);
- предупреждение: HTTP и демо-пароли только для проверки, не для production.

- [ ] **Step 7: Проверить compose и smoke**

```bash
cp deploy/.env.example deploy/.env
cd deploy
docker compose config
docker compose up -d --wait
docker compose ps -a
curl -fsS http://localhost/healthz
curl -fsS http://localhost/readyz
curl -fsS http://localhost/docs -o /dev/null
curl -fsS http://localhost/ -o /dev/null
```

На Windows использовать `curl.exe`. Ожидается: `migrate` и `minio-init` — `exited (0)`, долгоживущие сервисы healthy, `/readyz` возвращает `200` с `postgres` и `redis` в статусе `ok`, HTML главной содержит `БаЛаЛайка`. Если `up -d --wait` завершился ошибкой только из-за one-shot-сервисов, выполнить `docker compose up -d` и bounded-ожидание `http://localhost/healthz`; результат зафиксировать в README.

- [ ] **Step 8: Коммит**

```bash
git add backend/Dockerfile .dockerignore deploy README.md
git commit -m "chore: add compose, nginx and env template"
```

---

## Task 5: Stage 0 verification and close-out

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Прогнать полную проверку**

```bash
cd backend
make check
```

На Windows без `make`:

```bash
cd backend
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy app
```

Ожидается: все тесты PASS, линтеры и mypy без ошибок.

- [ ] **Step 2: Проверить миграцию на чистой БД**

Только для одноразовой stage 0 БД: `down -v` уничтожает volumes. Не выполнять при наличии данных.

```bash
cd deploy
docker compose down -v
docker compose up -d --wait
docker compose run --rm migrate alembic current
```

Ожидается: `alembic current` показывает ревизию `0001`.

- [ ] **Step 3: Пройти smoke этапа 0**

```bash
curl -fsS http://localhost/healthz
curl -fsS http://localhost/readyz
curl -fsS http://localhost/ -o /dev/null
curl -fsS http://localhost/docs -o /dev/null
```

Ожидается: `/`, `/docs`, `/healthz`, `/readyz` отвечают `200`; `postgres` и `redis` — `ok`; HTML главной содержит `БаЛаЛайка`.

- [ ] **Step 4: Smoke из чистого клона**

```bash
SMOKE_DIR="$(mktemp -d)"
git clone --branch feature/foundation . "$SMOKE_DIR/balalayka"
cd "$SMOKE_DIR/balalayka"
cp deploy/.env.example deploy/.env
cd deploy
docker compose up -d --wait
curl -fsS http://localhost/healthz
curl -fsS http://localhost/readyz
curl -fsS http://localhost/ -o /dev/null
curl -fsS http://localhost/docs -o /dev/null
docker compose down -v
```

На Windows использовать `$env:TEMP` и `curl.exe`. Ожидается: чистая копия собирается без локальных артефактов, все endpoints отвечают `200`.

- [ ] **Step 5: Проверить DoD**

Из корня репозитория:

```bash
git check-ignore -v deploy/.env
git ls-files deploy/.env
git ls-files -- '*.env' '*.env.*'
git grep -n -E "TODO|FIXME"

cd deploy
docker compose ps -a
docker compose port postgres 5432
docker compose port redis 6379
docker compose port minio 9000
docker compose run --rm migrate alembic current
docker compose logs --no-color > /tmp/balalayka-logs.txt
if grep -E "SECRET_KEY|POSTGRES_PASSWORD|MINIO_ROOT_PASSWORD|DATABASE_URL" /tmp/balalayka-logs.txt; then
  echo "secret leak in logs" >&2
  exit 1
fi
```

На Windows заменить `grep` на `Select-String`, `/tmp` — на `$env:TEMP`, `curl` — на `curl.exe`.

Ожидается:

- `migrate` и `minio-init` — `exited (0)`, остальные сервисы healthy;
- `docker compose port` для PostgreSQL, Redis и MinIO не возвращает опубликованный порт;
- `deploy/.env` игнорируется и не отслеживается, других `.env*` в индексе нет;
- `git grep TODO|FIXME` не находит совпадений;
- `alembic current` показывает `0001`;
- проверка логов завершается успешно: `SECRET_KEY`, паролей и `DATABASE_URL` с credentials нет.

- [ ] **Step 6: Обновить ROADMAP**

- перевести этап 0 в статус `готово`;
- зафиксировать, что worker, ARQ, MinIO-клиент и upload остаются на этапе 2;
- не добавлять новые функции и не менять ADR.

- [ ] **Step 7: Коммит**

```bash
git add docs/ROADMAP.md
git commit -m "docs: close foundation stage"
```

---

## Out of Scope

- Регистрация, вход, сессии, CSRF, роли.
- Модели `users`, `sessions`, `channels` и доменные миграции.
- Загрузка в MinIO, presigned POST, ARQ, ffmpeg, worker.
- Экраны кроме главной, JSON API `/api/v1`, модерация.
- `deploy/deploy.sh`, seed и demo-данные.
- TLS, домен, Caddy-профиль.

## Risks

| Риск | Проверка | Действие |
|---|---|---|
| `make` отсутствует на Windows | локальный запуск | использовать `poetry run ...`; Makefile только для Ubuntu/CI |
| Корневой `.venv` остался от старого конфига | `poetry env info` из `backend/` | не использовать; удалить вручную после проверки |
| `poetry.toml` игнорируется Git | `git check-ignore backend/poetry.toml` | переносить `Move-Item`/`mv`, не `git mv`; держать в `.gitignore` |
| `testcontainers` не может запустить Docker | `pytest tests/integration` | проверить Docker Desktop; не заменять PostgreSQL на SQLite |
| MinIO-образ недоступен или требует иной тег | `docker compose pull` и проверка `/bin/sh`, `curl`/`wget` | зафиксировать проверенный release-тег; `latest` запрещён |
| `docker compose up --wait` и one-shot-сервисы | `docker compose ps -a` | если ошибка только из-за `exited (0)`, использовать `up -d` + bounded-ожидание `/healthz` |
| CRLF ломает `*.sh` | `git ls-files --eol` | `.gitattributes` с `eol=lf` |
| Шаблоны не найдены в контейнере | smoke `GET /` | пути `/app/frontend/templates` и `/app/frontend/static` |
| `SECRET_KEY` попал в лог | smoke и чтение логов | маскировать через `SecretStr`, не логировать настройки целиком |

## Definition of Done

- `cd backend && make check` (или `poetry run ...` на Windows) — зелёный.
- `alembic upgrade head` проходит на чистой PostgreSQL; `alembic current` = `0001`.
- `cd deploy && docker compose up -d --wait` поднимает систему; one-shot-сервисы завершаются с `0`.
- `/`, `/docs`, `/healthz`, `/readyz` отвечают `200`.
- Наружу открыт только nginx `:80`; порты PostgreSQL, Redis и MinIO не опубликованы.
- Секретов в git и логах нет; `deploy/.env` игнорируется.
- `git grep TODO|FIXME` не находит совпадений.
- Smoke из чистого клона проходит.
- `docs/ROADMAP.md` переведён в `готово`.
