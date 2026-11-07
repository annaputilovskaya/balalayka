from functools import lru_cache

from fastapi.templating import Jinja2Templates

from app.core.config import get_settings


@lru_cache
def get_templates() -> Jinja2Templates:
    return Jinja2Templates(directory=str(get_settings().templates_dir))
