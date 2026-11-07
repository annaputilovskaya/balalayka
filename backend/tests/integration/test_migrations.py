import asyncio

import asyncpg
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

from alembic import command
from app.core.config import get_settings


def test_alembic_upgrade_enables_pg_trgm(monkeypatch):
    with PostgresContainer("postgres:16-alpine") as postgres:
        url = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")
        monkeypatch.setenv("DATABASE_URL", url)
        get_settings.cache_clear()

        config = Config("alembic.ini")
        command.upgrade(config, "head")

        assert asyncio.run(_extension_exists(url)) is True

    get_settings.cache_clear()


async def _extension_exists(url: str) -> bool:
    connection = await asyncpg.connect(url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        row = await connection.fetchrow(
            "SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'"
        )
        return row is not None
    finally:
        await connection.close()
