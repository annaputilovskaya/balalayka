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
