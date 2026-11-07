from fastapi import APIRouter, Request
from starlette.responses import Response

from app.web.templating import get_templates

router = APIRouter()


@router.get("/", name="home")
async def home(request: Request) -> Response:
    templates = get_templates()
    return templates.TemplateResponse(
        request=request,
        name="pages/home.html",
        context={"title": "Главная"},
    )
