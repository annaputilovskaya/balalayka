import asyncio
import logging
from collections.abc import Awaitable, Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.db import check_database
from app.core.redis import check_redis

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


async def _check(name: str, check: Callable[[], Awaitable[None]]) -> str:
    try:
        await check()
    except Exception as exc:
        logger.warning(
            "Readiness check failed",
            extra={"check": name, "error": type(exc).__name__},
        )
        return "error"
    return "ok"


@router.get("/readyz")
async def readyz() -> JSONResponse:
    postgres_status, redis_status = await asyncio.gather(
        _check("postgres", check_database),
        _check("redis", check_redis),
    )
    checks = {"postgres": postgres_status, "redis": redis_status}
    healthy = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )
