# AGENTS.md — deploy

## 1. Область

Каталог `deploy/` содержит всё для развёртывания на чистой Ubuntu: compose, nginx, скрипт деплоя и пример env. Правила действуют для `deploy/deploy.sh`, `deploy/docker-compose.yml`, `deploy/nginx/` и `deploy/.env.example`.

- Цель — поднять систему одной командой на Ubuntu 22.04/24.04 по IP и HTTP.
- Деплой не содержит бизнес-логики приложения и не дублирует backend-код.
- Источник истины — ADR-013; топология и порядок запуска — `docs/architecture.md`.
- Секреты и `.env` не попадают в git, логи и сообщения коммитов.

## 2. Состав Compose

```text
nginx        # единственная публичная точка, :80
backend      # FastAPI, страницы и API
worker       # ARQ + ffmpeg, без HTTP
postgres     # PostgreSQL 16, источник истины
redis        # ARQ и rate limit
minio        # приватное object storage
minio-init   # one-shot: бакеты, lifecycle, scoped-пользователь
```

- `backend` и `worker` собираются из одного образа и используют общий код.
- Volumes: `pgdata`, `redisdata`, `miniodata`; удаление volume уничтожает данные.
- `restart: unless-stopped` для долгоживущих сервисов.
- `minio-init` и миграции — one-shot контейнеры; они не должны висеть после успеха.
- Порядок: healthy `postgres`/`redis`/`minio` → `minio-init` → миграции → `backend`/`worker` → `nginx` → seed.

## 3. Сетевая модель

- Наружу открыт только nginx на `:80`.
- `postgres`, `redis` и `minio` — только internal network; порты не публикуются на хост.
- MinIO console отключён, root-доступ наружу не публикуется.
- Nginx проксирует:
  - `/` и страницы — в `backend`;
  - `/api/`, `/docs`, `/openapi.json` — в `backend`;
  - `/static/` — в `backend` или смонтированную статику;
  - `/media/` — в `backend` с проверкой доступа;
  - `/incoming-videos/` — в `minio` **без rewrite пути**.
- Для `/incoming-videos/`: сохранять `Host`, `client_max_body_size 500m`, `proxy_request_buffering off`, не буферизовать тело.
- Подпись presigned POST должна совпадать с публичным URL; `PUBLIC_BASE_URL=http://<IP>`.
- Не добавляй TLS-терминацию по умолчанию: у проверяющего только IP и HTTP.

## 4. Конфигурация и секреты

- `deploy/.env.example` содержит только имена переменных и безопасные примеры, без реальных паролей.
- `.env` создаётся `deploy.sh` **один раз** и повторно не перезаписывается.
- Обязательные переменные: `DATABASE_URL`, `REDIS_URL`, `MINIO_ENDPOINT`, `MINIO_PUBLIC_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `PUBLIC_BASE_URL`, `SECRET_KEY`, `SESSION_COOKIE_SECURE`, `MAX_UPLOAD_BYTES`, `MAX_VIDEO_DURATION_SECONDS`, `FFMPEG_TIMEOUT_SECONDS`, `DEMO_SEED`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
- Для HTTP по IP: `SESSION_COOKIE_SECURE=false`; это осознанный компромисс для демо.
- `SECRET_KEY` и пароли генерируются криптографически стойко.
- `.env` имеет ограниченные права доступа; не выводи его содержимое в логи и консоль.
- Не логируй presigned query string, пароли, токены и содержимое `.env`.

## 5. Healthchecks и зависимости

- `postgres`: `pg_isready`.
- `redis`: `redis-cli ping`.
- `minio`: health endpoint.
- `backend`: `/healthz`; готовность — `/readyz` с проверкой PostgreSQL и Redis.
- `nginx` зависит от backend, но не маскирует его падение.
- Запуск backend/worker — только после успешных healthchecks и миграций.
- Compose использует `depends_on: condition: service_healthy` там, где это поддерживается.
- Healthcheck имеет `start_period`, `interval`, `timeout` и `retries`; бесконечное ожидание запрещено.

## 6. Миграции, storage и seed

- Миграции — только `alembic upgrade head`; `--autogenerate` в деплое запрещён.
- Миграции выполняются один раз до старта backend; повторный запуск идемпотентен.
- `minio-init` создаёт бакеты `incoming-videos`, `media`, `raw-videos`, lifecycle 24 часа для `incoming-videos` и scoped-пользователя.
- `minio-init` идемпотентен: повторный запуск не падает и не пересоздаёт данные.
- Seed выполняется после миграций и запускается только при `DEMO_SEED=true`.
- Seed идемпотентен: демо-пользователи, видео, комментарии и плейлисты не дублируются.
- Демо-пароли фиксированы и описаны в README с предупреждением.

## 7. deploy.sh

`deploy/deploy.sh` — единственная точка входа.

```bash
./deploy/deploy.sh
```

Скрипт должен:

1. Проверить Ubuntu и наличие прав.
2. Установить Docker Engine и Compose plugin, если их нет.
3. Сгенерировать `.env`, только если файла ещё нет.
4. Определить IP и выставить `PUBLIC_BASE_URL=http://<IP>`.
5. Поднять compose с ожиданием healthchecks.
6. Прогнать миграции, `minio-init` и seed.
7. Выполнить smoke-проверки и вернуть ненулевой код при ошибке.

Требования:

- Идемпотентность: повторный запуск не перетирает `.env`, не удаляет volumes и не дублирует данные.
- `set -euo pipefail`; каждая ошибка видна и останавливает деплой.
- Никаких интерактивных вопросов, кроме явно оговорённых.
- Скрипт не хранит секреты в репозитории и не печатает их.
- LF-переводы строк для `*.sh`; файл исполняемый.
- Логи деплоя сохраняются локально и не содержат секретов.

## 8. Smoke на чистой VM

После деплоя обязательно проверить:

- `GET /` — 200, главная с лентой.
- `GET /docs` — Swagger открывается.
- `GET /healthz` — 200; `GET /readyz` — зависимости доступны.
- Регистрация и вход работают через cookie.
- Загрузка небольшого MP4 проходит через presigned POST и nginx.
- Видео получает `ready`, открывается на watch-странице и играет с перемоткой.
- Лайк и комментарий создаются.
- Приватное видео недоступно чужому пользователю.
- Повторный `./deploy/deploy.sh` не ломает работающую систему.

Smoke выполняется на чистой Ubuntu 22.04/24.04, а не только на машине разработчика.

## 9. Эксплуатация

- Логи: отдельно nginx, backend, worker; JSON с request ID.
- Не храни секреты и персональные данные в логах.
- Диск: следи за `raw-videos` и `media`; запас обязателен.
- Обновление — повторный деплой; миграции только вперёд.
- Не удаляй volumes без явного подтверждения пользователя.
- При падении Redis загрузка принимается, обработка ждёт восстановления.
- При недоступности PostgreSQL или MinIO healthcheck деградирует, а не маскируется.
