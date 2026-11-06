# Архитектура БаЛаЛайки

Статус: принята
Дата: 2026-11-06

Документ описывает **как устроена система**. Причины решений и отвергнутые альтернативы — в `docs/decisions.md` (ADR). План работ — в `docs/ROADMAP.md`.

## 1. Назначение и ограничения

БаЛаЛайка — MVP-видеоплатформа: регистрация, загрузка, обработка, просмотр, лайки, комментарии, каналы, подписки, плейлисты, поиск, модерация и приватные видео.

Ограничения:

- Python 3.12+, FastAPI, PostgreSQL 16;
- один сервер Ubuntu 22.04/24.04, только IP и HTTP;
- деплой одной командой;
- 7 дней разработки, поэтому один монолит, один worker и один rendition видео;
- Swagger `/docs` обязателен;
- фронтенд — Jinja2 + precompiled Tailwind + vanilla JS.

Границы MVP и non-goals: ADR-001. Деплой: ADR-013.

## 2. Качественные атрибуты

| Атрибут | Как обеспечивается |
|---|---|
| Безопасность | ACL на каждом чтении, 404 для чужих, Argon2id, CSRF, rate limit, приватный MinIO, валидация загрузки |
| Разворачиваемость | Docker Compose, healthchecks, идемпотентный `deploy.sh`, seed |
| Похожесть на YouTube | SSR-экраны, единый UI-чеклист, превью, плеер с Range, каналы, подписки, плейлисты |
| Объём | feature-модули, приоритет P0/P2, отказ от HLS/рекомендаций/CDN |
| Сопровождаемость | слои, доменные ошибки, ADR, тесты сервисов и security-регрессии |
| Надёжность | статусы обработки, retries, reconciler, идемпотентность |

## 3. Контекст и контейнеры

```text
Браузер
  |
  | HTTP :80
  v
nginx  ──────────────  /incoming-videos/  ──────────────>  MinIO
  |                                                        (incoming-videos,
  | /, /media/, /static/, /docs/                            media, raw-videos)
  v
FastAPI backend  ───────────────>  PostgreSQL
  |        |                        (данные, сессии, аудит)
  |        |
  |        └──────────────────>  Redis (ARQ, rate limit)
  |
  └── Jinja2 templates + JSON API

Frontend не является отдельным контейнером: шаблоны и статика из `frontend/` попадают в образ backend. `deploy/` — не runtime-сервис, а каталог инфраструктуры.

ARQ worker  ───> PostgreSQL / Redis / MinIO
     |
     └──> ffmpeg / ffprobe (subprocess)
```

### 3.1. Nginx

- Единственная публичная точка на порту 80.
- Конфигурация — `deploy/nginx/`.
- Отдаёт статику, проксирует страницы и API в backend.
- Проксирует `/incoming-videos/` в MinIO для presigned POST.
- Проксирует `/media/` в backend; backend проверяет доступ и поддерживает Range.
- Не проксирует `media` и `raw-videos` напрямую.
- `client_max_body_size 500m`, `proxy_request_buffering off` для загрузки.
- Сохраняет `Host` и путь без rewrite, чтобы SigV4 совпадал с presigned URL.
- MinIO, PostgreSQL и Redis наружу не публикуются.

### 3.2. Backend

- Код — `backend/app/`, миграции — `backend/alembic/`.
- FastAPI, async SQLAlchemy 2.0, Pydantic v2.
- Jinja2-страницы и `/api/v1`.
- Аутентификация, сессии, CSRF, роли.
- Сервисы домена, read-модели, стриминг медиа.
- OpenAPI и Swagger `/docs`.
- Health endpoints `/healthz` и `/readyz`.

### 3.3. Worker

- ARQ worker, отдельный контейнер из того же образа.
- Забирает jobs из Redis.
- Запускает `ffprobe` и `ffmpeg` через `asyncio.create_subprocess_exec`.
- Обновляет статусы в PostgreSQL и складывает результаты в MinIO.
- Не обслуживает HTTP.

### 3.4. PostgreSQL

- Основное хранилище данных, сессий, жалоб и аудита.
- Источник истины для статусов видео.
- Миграции — Alembic.

### 3.5. Redis

- Очередь ARQ.
- Rate limit.
- Не хранит сессии; `appendonly yes`.

### 3.6. MinIO

- Приватные бакеты `incoming-videos`, `media`, `raw-videos`.
- `incoming-videos` — временные загрузки, lifecycle 24 часа.
- `media` — готовые видео и превью.
- `raw-videos` — архив исходников.
- `minio-init` создаёт бакеты, lifecycle и scoped-пользователя.

## 4. Модульная структура

```text
backend/
  app/
    core/            # config, db, security, errors, logging, pagination
    auth/            # регистрация, вход, сессии, CSRF
    users/           # профили, роли
    channels/        # каналы, подписки
    videos/          # метаданные, статусы, upload/complete, streaming
    media/           # MinIO-клиент, presigned POST, ffprobe/ffmpeg
    engagement/      # лайки, комментарии, просмотры
    playlists/       # плейлисты и элементы
    search/          # поиск и read-модели ленты
    moderation/      # жалобы, скрытие, аудит
    admin/           # управление ролями и служебные операции
    web/             # Jinja-роуты, шаблоны, формы
    api/             # JSON-роуты /api/v1
    workers/         # ARQ worker, задачи обработки
  tests/
    unit/
    integration/
    e2e/
  alembic/
  pyproject.toml     # перенос из корня на этапе 0
frontend/
  templates/         # base, partials, macros, pages, errors
  static/            # css (precompiled Tailwind), js, img
  package.json       # только dev-сборка CSS
deploy/
  docker-compose.yml
  deploy.sh
  nginx/
  .env.example
```

Правила:

- Feature-модуль содержит `router.py`, `api.py`, `service.py`, `repository.py`, `models.py`, `schemas.py`.
- Роутеры и API-адаптеры не содержат бизнес-логику и SQL.
- Сервис владеет транзакцией и проверкой прав.
- Read-модели — в `queries/` соответствующего модуля; они используют явные JOIN и единый фильтр видимости.
- Модуль не импортирует ORM-модели другого модуля напрямую.
- Шаблоны в `frontend/templates/` не содержат бизнес-логики; статика в `frontend/static/` собирается заранее.
- `deploy/` описывает только инфраструктуру; секреты хранятся в `.env`, а не в compose.

## 5. Основные потоки

### 5.1. Регистрация и вход

1. `POST /api/v1/auth/register` создаёт пользователя, канал и сессию.
2. `POST /api/v1/auth/login` проверяет Argon2id-хэш, создаёт сессию и ставит cookie.
3. Cookie: `HttpOnly`, `SameSite=Lax`, `Secure` из env.
4. Для JSON-запросов UI передаёт CSRF-токен; для Swagger login возвращает тот же session-token как Bearer.
5. Logout удаляет сессию; logout-all удаляет все сессии пользователя.

### 5.2. Загрузка видео

1. `POST /api/v1/videos` — создаётся `draft` с метаданными и visibility.
2. `POST /api/v1/videos/{id}/upload-url` — backend выдаёт presigned POST:
   - bucket `incoming-videos`;
   - key `videos/{user_id}/{video_id}/source`;
   - лимит 500 МБ, `Content-Type: video/*`;
   - expiry 15 минут.
3. Браузер загружает файл напрямую в MinIO через nginx; прогресс — XHR.
4. `POST /api/v1/videos/{id}/complete`:
   - проверяет владельца и `draft`;
   - делает `HEAD` объекта;
   - сверяет размер, тип и ключ;
   - переводит в `uploaded`;
   - ставит job `video:{id}:process`;
   - возвращает `202` и `status_url`.
5. Ошибка загрузки или несоответствие — `422`, объект удаляется.

### 5.3. Обработка

1. ARQ worker берёт job.
2. `ffprobe` проверяет наличие видеопотока и длительность ≤ 30 минут.
3. `ffmpeg` делает H.264/AAC MP4 720p с `+faststart`.
4. Генерируется превью на 1-й секунде.
5. Результаты загружаются в `media`:
   - `videos/{video_id}/720p.mp4`;
   - `thumbnails/{video_id}.jpg`.
6. Исходник переносится в `raw-videos`, временный объект удаляется.
7. Статус — `ready`; при ошибке — `rejected` с причиной, исходник остаётся для retry.
8. Reconciler возвращает зависшие `processing` и потерянные `uploaded` в очередь.

### 5.4. Просмотр

1. `GET /watch/{id}` рендерит страницу.
2. Плеер запрашивает `GET /media/videos/{id}`.
3. Backend применяет `AccessPolicy`:
   - `public` — доступен всем;
   - `unlisted` — доступен по прямой ссылке, но не в списках;
   - `private` — owner + ACL;
   - `hidden` — 404 для всех, кроме owner/moderator/admin.
4. Для `Range` возвращается `206` с `Content-Range`; невалидный диапазон — `416`.
5. Превью — `GET /media/thumbnails/{id}` с той же проверкой.

### 5.5. Лента, поиск, канал

- Read-модели выбирают только `ready` и `visible`.
- `public` попадает в ленту, поиск и канал; `unlisted`, `private`, `hidden` — нет.
- Поиск — `pg_trgm` по названию и имени канала, keyset-пагинация.
- Канал показывает видео и плейлисты; подписка — unique `(subscriber_id, channel_id)`.

### 5.6. Лайки, комментарии, просмотры

- Лайк — unique `(user_id, video_id)`; повторный запрос идемпотентен.
- Комментарий создаётся в транзакции с обновлением `comments_count`.
- Просмотр увеличивает `views_count`; дедупликация по сессии — P2.
- Счётчики денормализованы; reconciliation-джоба исправляет расхождения.

### 5.7. Модерация

1. Пользователь создаёт жалобу на видео.
2. Модератор открывает очередь жалоб.
3. Hide меняет `moderation_status` на `hidden`; restore возвращает `visible`.
4. Действие пишется в `audit_log` с actor, target, reason и request ID.
5. Private-видео доступно модератору только в контексте жалобы.

### 5.8. Приватный доступ

1. Владелец в настройках видео добавляет пользователя по handle.
2. Backend разрешает handle в `user_id` и создаёт `video_acl`.
3. Владелец может отозвать доступ.
4. Все read-поверхности используют один SQL-предикат видимости.
5. Чужой пользователь получает `404`, а не `403`.

## 6. Данные

### 6.1. PostgreSQL

Основные таблицы:

- `users`, `sessions`;
- `channels`, `subscriptions`;
- `videos`, `video_assets`, `video_acl`;
- `playlists`, `playlist_items`;
- `likes`, `comments`;
- `reports`, `moderation_actions`, `audit_log`.

Ключевые поля `videos`:

- `id`, `channel_id`, `title`, `description`;
- `visibility`: `public | unlisted | private`;
- `processing_status`: `draft | uploaded | processing | ready | rejected`;
- `moderation_status`: `visible | hidden`;
- `duration`, `width`, `height`, `thumb_key`;
- `views_count`, `likes_count`, `comments_count`;
- `published_at`, `created_at`, `updated_at`, `deleted_at`.

Ограничения и индексы — ADR-005.

### 6.2. Object storage

| Bucket | Доступ | Содержимое |
|---|---|---|
| `incoming-videos` | private, presigned POST | `videos/{user_id}/{video_id}/source` |
| `media` | private, только backend | `videos/{video_id}/720p.mp4`, `thumbnails/{video_id}.jpg` |
| `raw-videos` | private, только backend/worker | `videos/{user_id}/{video_id}/source` |

Правила:

- наружу не публикуется ни один bucket;
- presigned POST — только в `incoming-videos`;
- presigned GET не используется;
- исходник переносится в `raw-videos` после успешной обработки;
- lifecycle удаляет брошенные объекты из `incoming-videos` через 24 часа.

### 6.3. Redis

- ARQ-очередь.
- Rate limit ключи.
- Без сессий и без бизнес-данных.

## 7. Безопасность и границы доверия

### 7.1. Границы

- **Публичная зона:** nginx :80.
- **Внутренняя зона:** backend, worker, PostgreSQL, Redis, MinIO.
- Браузер не имеет прямого доступа к PostgreSQL, Redis и MinIO.
- Presigned POST — единственная операция, которая проходит в MinIO через nginx.

### 7.2. Меры

- Пароли — Argon2id; rate limit на login/register.
- Сессии — PostgreSQL, opaque token, hash в БД, ротация, expiry.
- CSRF — double-submit + `Origin` для cookie-запросов.
- Роли проверяются в сервисе; UI не является защитой.
- Приватность — `AccessPolicy` + SQL-предикат на всех чтениях.
- Неавторизованный доступ — `404`.
- Загрузка: presigned POST policy, лимит 500 МБ, `Content-Type`, `HEAD` после загрузки, `ffprobe`.
- ffmpeg: non-root, timeout, ограниченная конкурентность, без произвольного интернета.
- Секреты — только в `.env`, не в git и не в логах.
- Presigned URL не логируется с query string.
- MinIO console отключён; root-доступ не публикуется.
- Аудит модерации и ролевых изменений.

### 7.3. Ограничение HTTP

Деплой по IP использует HTTP. Это значит:

- пароли и cookie идут без TLS;
- `SESSION_COOKIE_SECURE=false`;
- допустимо только для проверки/демо;
- для production нужен домен и TLS (Caddy-профиль).

## 8. Конфигурация

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | PostgreSQL DSN |
| `REDIS_URL` | Redis DSN |
| `MINIO_ENDPOINT` | внутренний endpoint MinIO |
| `MINIO_PUBLIC_ENDPOINT` | публичный endpoint для presigned POST |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | credentials MinIO |
| `PUBLIC_BASE_URL` | `http://<IP>` для ссылок |
| `SECRET_KEY` | подпись/сессии |
| `SESSION_COOKIE_SECURE` | `false` для HTTP-демо |
| `MAX_UPLOAD_BYTES` | 524288000 |
| `MAX_VIDEO_DURATION_SECONDS` | 1800 |
| `FFMPEG_TIMEOUT_SECONDS` | 2700 |
| `DEMO_SEED` | включать seed при деплое |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | bootstrap админа |

## 9. Деплой

Compose-файл — `deploy/docker-compose.yml`; конфигурация nginx — `deploy/nginx/`; переменные окружения — `deploy/.env.example`.

Compose-сервисы:

- `nginx`
- `backend`
- `worker`
- `postgres`
- `redis`
- `minio`
- `minio-init`

Порядок:

1. `postgres`, `redis`, `minio` проходят healthcheck.
2. `minio-init` создаёт бакеты, lifecycle и scoped-пользователя.
3. Одноразовый контейнер выполняет `alembic upgrade head`.
4. `backend` и `worker` стартуют.
5. `nginx` принимает трафик.
6. Seed выполняется идемпотентно, если включён.

Volumes: `pgdata`, `redisdata`, `miniodata`.

`deploy/deploy.sh`:

- проверяет/устанавливает Docker и Compose;
- генерирует `.env` один раз;
- определяет `PUBLIC_BASE_URL`;
- поднимает compose с `--wait`;
- прогоняет миграции и init;
- выполняет seed;
- проверяет `/healthz` и smoke-загрузку.

## 10. Отказы и деградация

| Отказ | Поведение |
|---|---|
| Redis недоступен | Загрузка принимается, видео остаётся `uploaded`; reconciler поставит job после восстановления |
| Worker упал | Job retry; зависшие `processing` возвращаются reconciler-ом |
| ffmpeg ошибка | `rejected`, причина в БД, исходник сохранён для retry |
| MinIO недоступен | `complete`/стриминг возвращают 503; загрузка не начинается |
| PostgreSQL недоступен | 503, записи не выполняются |
| Диск заполнен | Загрузка отклоняется, healthcheck деградирует |
| Дубликат complete | Идемпотентно, повторный job не создаётся |
| Дубликат job | Идемпотентность по `video:{id}:process` |

## 11. Наблюдаемость

- JSON-логи с request ID.
- Отдельные логи backend, worker, nginx.
- `/healthz` — процесс жив; `/readyz` — БД и Redis доступны.
- Метрики — опционально; минимум — длина очереди и failed jobs.
- Аудит модерации и ролей — в БД.
- Presigned query strings и секреты не логируются.

## 12. Ограничения текущей версии

- Один rendition 720p; HLS/ABR отсутствует.
- Один worker; масштабирование — репликами.
- Нет рекомендаций, live, уведомлений, OAuth, email-верификации, сброса пароля.
- Нет CDN и nginx-кэша видео.
- HTTP без TLS в демо.
- Одна VM, без HA и бэкапов.

## 13. Карта ADR

| Тема | ADR |
|---|---|
| Границы MVP | ADR-001 |
| Монолит и модули | ADR-002 |
| Слои и транзакции | ADR-003 |
| Jinja + API | ADR-004 |
| Схема БД | ADR-005 |
| Загрузка и MinIO | ADR-006 |
| Раздача и приватность | ADR-007 |
| Очередь и обработка | ADR-008 |
| Модель приватности | ADR-009 |
| Аутентификация и роли | ADR-010 |
| Frontend | ADR-011 |
| Поиск | ADR-012 |
| Деплой | ADR-013 |
| Модерация | ADR-014 |
| Тесты | ADR-015 |
| AI-артефакты | ADR-016 |
