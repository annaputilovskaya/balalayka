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
