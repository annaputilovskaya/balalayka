from fastapi import FastAPI

from app.api import health
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(title="БаЛаЛайка", version="0.1.0")
    application.add_middleware(RequestIDMiddleware)
    register_exception_handlers(application)
    application.include_router(health.router)
    return application


app = create_app()
