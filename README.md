# БаЛаЛайка

MVP-видеоплатформа: каналы, загрузка и просмотр видео, подписки, плейлисты, поиск, приватность и модерация. Интерфейс повторяет привычные сценарии видеоплатформы, но использует собственный бренд и демо-контент.

## Стек

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic
- PostgreSQL 16, Redis 7, MinIO
- Jinja2, precompiled Tailwind CSS, vanilla ES-модули
- Docker Compose, nginx

## Структура репозитория

```text
backend/   FastAPI-приложение, тесты и миграции
frontend/  Jinja2-шаблоны, статика и сборка Tailwind
deploy/    compose, nginx и шаблон env
docs/      ТЗ, ADR, архитектура, ROADMAP
```

## Backend

Команды выполняются из `backend/`.

```bash
cd backend
poetry env use 3.12
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Проверки:

```bash
cd backend
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy app
```

`make check` делает то же самое на Ubuntu/CI; на Windows используйте команды `poetry run ...`.

Для локального запуска создайте `backend/.env` из `deploy/.env.example` и замените хосты БД и Redis на `localhost`:

```dotenv
DATABASE_URL=postgresql+asyncpg://balalayka:change-me@localhost:5432/balalayka
REDIS_URL=redis://localhost:6379/0
```

Поднять только PostgreSQL и Redis с проброшенными на `127.0.0.1` портами:

```bash
cd deploy
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis
```

Корневой `.venv` остался от старой конфигурации и считается stale. Backend-команды выполняются только из `backend/`.

## Frontend

```bash
cd frontend
npm ci
npm run build:css
npm run watch:css
```

Собранный `frontend/static/css/app.css` коммитится. Node нужен только для сборки CSS и не требуется в runtime.

## Быстрый старт через Docker Compose

```bash
cp deploy/.env.example deploy/.env
cd deploy
docker compose up -d
```

Если нужен режим ожидания, используйте `docker compose up -d --wait`. В текущей версии Compose он может завершиться с кодом `1` из-за штатно завершившегося one-shot `minio-init`, даже когда все долгоживущие сервисы healthy. Это не ошибка стека: проверьте `docker compose ps -a` и endpoints ниже.

Перед использованием в `deploy/.env` замените пароли и `SECRET_KEY`. Файл `.env` не коммитится.

Проверки после запуска:

- `http://localhost/` — главная страница
- `http://localhost/docs` — Swagger UI
- `http://localhost/healthz` — liveness
- `http://localhost/readyz` — готовность PostgreSQL и Redis

One-shot-сервисы `migrate` и `minio-init` должны завершиться с кодом `0`, долгоживущие сервисы — быть в состоянии `healthy`. Посмотреть состояния:

```bash
cd deploy
docker compose ps -a
```

Остановка:

```bash
cd deploy
docker compose down
```

`docker compose down -v` удаляет volumes и все данные. Выполняйте только для одноразового стенда.

## Сеть и безопасность

- Снаружи опубликован только nginx на порту `80`.
- PostgreSQL, Redis и MinIO доступны только внутри compose-сети; их порты на хост не публикуются.
- MinIO console не публикуется наружу.
- `deploy/docker-compose.dev.yml` — только для локальной разработки, в деплое не используется.
- HTTP и демо-пароли допустимы только для проверки, но не для production.

Официальные образы `minio/minio` и `minio/mc` больше не публичны. В compose используется закреплённый `bitnamilegacy/minio:2025.7.23-debian-12-r5`, который содержит официальные бинарники `minio` и `mc`. Тег `latest` не используется.

## Windows

- Используйте `curl.exe`, а не алиас `curl` из PowerShell.
- Файлы `.env` создаются копированием: `Copy-Item deploy\.env.example deploy\.env`.
- Для временных файлов используйте `$env:TEMP` вместо `/tmp`.

## Документация

- `docs/task.md` — исходное ТЗ
- `docs/decisions.md` — принятые решения (ADR)
- `docs/architecture.md` — архитектура
- `docs/ROADMAP.md` — этапы и статусы

Swagger UI по умолчанию загружает JS/CSS с CDN. При отсутствии интернета используйте `/openapi.json` или локальные ассеты (вне этапа 0).

## AI-артефакты

Экспорт сессии прикладывается к архиву сдачи. Промпты и служебные AI-файлы в git не добавляются (ADR-016).
