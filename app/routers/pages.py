"""
Page Routes

Serves full HTML pages (not HTMX partials).
These are the pages users navigate to directly.
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import REGIONS
from app.feature_flags import (
    is_region_enabled,
    is_feature_enabled,
    get_refresh_interval,
    get_demo_flags,
    DEMO_MODE
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def dashboard(request: Request):
    """
    Main dashboard page.
    Renders the full HTML with all region cards.
    """
    user_key = request.headers.get("X-User-ID", "anonymous")
    
    # Build region data with current flag status
    regions_data = {}
    for region_id, region in REGIONS.items():
        regions_data[region_id] = {
            "id": region_id,
            "name": region.name,
            "role": region.role,
            "color": region.color,
            "enabled": is_region_enabled(region_id, user_key),
            "configured": region.dsn is not None
        }
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "regions": regions_data,
        "health_checks_enabled": is_feature_enabled("health-checks", user_key),
        "load_testing_enabled": is_feature_enabled("load-testing", user_key),
        "refresh_interval": get_refresh_interval(user_key),
        "demo_mode": DEMO_MODE,
        "flags": get_demo_flags() if DEMO_MODE else {}
    })