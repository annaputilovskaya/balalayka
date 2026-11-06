# Черновик. Заменён docs/architecture.md и docs/decisions.md.

Черновик архитектуры (не финальный):
- Модульный монолит: feature-модули + src/core.
- HTML на Jinja2 (router.py), JSON API /api/v1 (api.py), Swagger.
- Слои: router/api → service → repository → models; сервис владеет транзакцией (UoW).
- PostgreSQL + SQLAlchemy 2.0 async + Alembic; UUID PK; UTC.
- MinIO: presigned PUT для загрузки, presigned GET для просмотра; bucket media.
- ARQ + Redis: worker для ffprobe/ffmpeg, превью, статусы видео.
- Сессии в Redis + HttpOnly cookie + CSRF; Argon2id.
- Приватность: visibility (public/private) + video_access ACL.
- Роли: user/moderator/admin; жалобы, скрытие, аудит.
- Read-модели: feed/ для главной, поиска и канала; явные JOIN.
- Jinja2 + локальный Tailwind + vanilla JS + fetch.
- Docker Compose: nginx, backend, worker, db, minio, minio-init, redis.
- Одна команда deploy.sh на чистой Ubuntu.
