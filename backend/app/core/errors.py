import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_HTTP_MESSAGES = {
    400: "Некорректный запрос",
    401: "Требуется аутентификация",
    403: "Доступ запрещён",
    404: "Запрошенный ресурс не найден",
    405: "Метод не разрешён",
    409: "Конфликт состояния",
    413: "Слишком большой запрос",
    422: "Ошибка валидации",
    429: "Слишком много запросов",
    500: "Внутренняя ошибка сервера",
    503: "Сервис временно недоступен",
}


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: object | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str, details: object | None = None) -> None:
        super().__init__(code="not_found", message=message, status_code=404, details=details)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "-"))


def _payload(
    code: str,
    message: str,
    details: object | None,
    request_id: str,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.details, _request_id(request)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_payload(
                "validation_error",
                _HTTP_MESSAGES[422],
                jsonable_encoder(exc.errors()),
                _request_id(request),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = _HTTP_MESSAGES.get(exc.status_code, "Ошибка запроса")
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload("http_error", message, None, _request_id(request)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content=_payload(
                "internal_error",
                _HTTP_MESSAGES[500],
                None,
                _request_id(request),
            ),
        )
