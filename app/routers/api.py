"""
API Routes (HTMX Endpoints)

These endpoints return HTML fragments, not JSON.
HTMX calls these and swaps the response into the DOM.

Key pattern:
    1. Button has hx-post="/api/regions/us-east/test"
    2. Button has hx-target="#result-us-east"
    3. Server returns HTML fragment
    4. HTMX swaps it into #result-us-east
"""
import asyncio
import random

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import REGIONS, DEFAULTS
from app.database import (
    test_connection,
    get_health_metrics,
    run_load_test,
    ConnectionResult,
    HealthMetrics,
    LoadTestResult
)
from app.feature_flags import (
    is_region_enabled,
    is_feature_enabled,
    toggle_demo_flag,
    get_demo_flags,
    DEMO_MODE
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# =============================================================
# DEMO MODE SIMULATORS
# When DEMO_MODE=true, we fake database responses
# =============================================================

def simulate_connection(region_id: str) -> ConnectionResult:
    """Fake a connection result for demo mode"""
    base_latency = {
        "us-east": 25,
        "eu-west": 120, 
        "asia-pacific": 180
    }.get(region_id, 100)
    
    return ConnectionResult(
        success=True,
        latency_ms=round(base_latency + random.uniform(-10, 20), 2),
        server_ip=f"10.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        server_port=6543,
        backend_pid=random.randint(10000, 50000),
        database="defaultdb",
        pg_version="PostgreSQL 16.2"
    )


def simulate_health() -> HealthMetrics:
    """Fake health metrics for demo mode"""
    return HealthMetrics(
        cache_hit_ratio=round(95 + random.uniform(0, 4.5), 2),
        active_connections=random.randint(5, 25),
        max_connections=100,
        db_size_mb=round(random.uniform(100, 500), 2)
    )


def simulate_load_test(region_id: str, concurrent: int) -> LoadTestResult:
    """Fake load test results for demo mode"""
    base = {"us-east": 25, "eu-west": 120, "asia-pacific": 180}.get(region_id, 100)
    results = [round(base + random.uniform(-5, 30) + (i * 1.5), 2) for i in range(concurrent)]
    
    return LoadTestResult(
        concurrent=concurrent,
        min_ms=min(results),
        max_ms=max(results),
        avg_ms=round(sum(results) / len(results), 2),
        results=results
    )


# =============================================================
# REGION TESTING ENDPOINTS
# =============================================================

@router.post("/regions/{region_id}/test")
async def test_region(region_id: str, request: Request):
    """
    Test connection to a specific region.
    
    Called when user clicks "Test" button.
    Returns HTML partial: partials/connection_result.html
    """
    user_key = request.headers.get("X-User-ID", "anonymous")
    
    # Check if region exists
    if region_id not in REGIONS:
        return HTMLResponse('<div class="text-red-400">❌ Unknown region</div>')
    
    # Check feature flag
    if not is_region_enabled(region_id, user_key):
        return templates.TemplateResponse("partials/region_disabled.html", {
            "request": request,
            "region": REGIONS[region_id]
        })
    
    # Add realistic delay for demo
    await asyncio.sleep(0.3 + random.uniform(0, 0.4))
    
    # Get result (simulated or real)
    if DEMO_MODE or not REGIONS[region_id].dsn:
        result = simulate_connection(region_id)
    else:
        result = await test_connection(region_id)
    
    return templates.TemplateResponse("partials/connection_result.html", {
        "request": request,
        "region": REGIONS[region_id],
        "result": result
    })


@router.post("/regions/test-all")
async def test_all_regions(request: Request):
    """
    Test ALL enabled regions concurrently.
    
    Called when user clicks "Test All Regions" button.
    Uses asyncio.gather() to run tests in parallel.
    Returns HTML partial: partials/all_results.html
    """
    user_key = request.headers.get("X-User-ID", "anonymous")
    
    # Get enabled regions only
    enabled = [rid for rid in REGIONS if is_region_enabled(rid, user_key)]
    
    if not enabled:
        return HTMLResponse('<div class="text-amber-400">⚠️ No regions enabled</div>')
    
    # Simulate parallel delay
    await asyncio.sleep(0.5 + random.uniform(0, 0.5))
    
    # Test each region
    results = {}
    for region_id in enabled:
        if DEMO_MODE or not REGIONS[region_id].dsn:
            results[region_id] = simulate_connection(region_id)
        else:
            results[region_id] = await test_connection(region_id)
    
    # Sort by latency (fastest first)
    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1].latency_ms if x[1].success else float('inf')
    )
    
    return templates.TemplateResponse("partials/all_results.html", {
        "request": request,
        "results": sorted_results,
        "regions": REGIONS
    })


# =============================================================
# HEALTH METRICS ENDPOINT
# =============================================================

@router.post("/regions/{region_id}/health")
async def region_health(region_id: str, request: Request):
    """
    Fetch health metrics for a region.
    
    Called when user clicks "Health" button.
    Returns HTML partial: partials/health_metrics.html
    """
    user_key = request.headers.get("X-User-ID", "anonymous")
    
    if region_id not in REGIONS:
        return HTMLResponse('<div class="text-red-400">❌ Unknown region</div>')
    
    if not is_feature_enabled("health-checks", user_key):
        return HTMLResponse('<div class="text-amber-400">⚠️ Health checks disabled</div>')
    
    if not is_region_enabled(region_id, user_key):
        return HTMLResponse('<div class="text-amber-400">⚠️ Region disabled</div>')
    
    await asyncio.sleep(0.2 + random.uniform(0, 0.2))
    
    if DEMO_MODE or not REGIONS[region_id].dsn:
        metrics = simulate_health()
    else:
        metrics = await get_health_metrics(region_id)
    
    if not metrics:
        return HTMLResponse('<div class="text-red-400">❌ Failed to fetch metrics</div>')
    
    return templates.TemplateResponse("partials/health_metrics.html", {
        "request": request,
        "metrics": metrics
    })


# =============================================================
# LOAD TESTING ENDPOINT
# =============================================================

@router.post("/regions/{region_id}/load-test")
async def load_test(region_id: str, request: Request):
    """
    Run concurrent load test against a region.
    
    Called when user clicks "Load" button.
    Returns HTML partial: partials/load_test_result.html
    """
    user_key = request.headers.get("X-User-ID", "anonymous")
    
    if region_id not in REGIONS:
        return HTMLResponse('<div class="text-red-400">❌ Unknown region</div>')
    
    if not is_feature_enabled("load-testing", user_key):
        return HTMLResponse('<div class="text-amber-400">⚠️ Load testing disabled</div>')
    
    if not is_region_enabled(region_id, user_key):
        return HTMLResponse('<div class="text-amber-400">⚠️ Region disabled</div>')
    
    concurrent = DEFAULTS["load_test_concurrent"]
    
    # Longer delay for load test (simulates actual work)
    await asyncio.sleep(1.5 + random.uniform(0, 0.5))
    
    if DEMO_MODE or not REGIONS[region_id].dsn:
        result = simulate_load_test(region_id, concurrent)
    else:
        result = await run_load_test(region_id, concurrent)
    
    if not result:
        return HTMLResponse('<div class="text-red-400">❌ Load test failed</div>')
    
    return templates.TemplateResponse("partials/load_test_result.html", {
        "request": request,
        "region": REGIONS[region_id],
        "result": result
    })


# =============================================================
# FEATURE FLAG ENDPOINTS (Demo Mode)
# =============================================================

@router.post("/flags/{flag_key}/toggle")
async def toggle_flag(flag_key: str, request: Request):
    """
    Toggle a feature flag in demo mode.
    
    Called when user clicks a flag in the flag panel.
    Returns HTML partial: partials/flag_panel.html
    """
    if not DEMO_MODE:
        return HTMLResponse('<div class="text-red-400">❌ Not in demo mode</div>')
    
    toggle_demo_flag(flag_key)
    
    return templates.TemplateResponse("partials/flag_panel.html", {
        "request": request,
        "flags": get_demo_flags()
    })


@router.get("/flags")
async def get_flags(request: Request):
    """Get current flag values for the flag panel"""
    return templates.TemplateResponse("partials/flag_panel.html", {
        "request": request,
        "flags": get_demo_flags()
    })


@router.get("/flag-panel")
async def get_flag_panel(request: Request):
    """Alias for /flags to match template expectations"""
    return templates.TemplateResponse("partials/flag_panel.html", {
        "request": request,
        "flags": get_demo_flags()
    })


# =============================================================
# COMPATIBILITY ROUTES (for template compatibility)
# =============================================================

@router.get("/test-connection/{region_id}")
async def test_connection_get(region_id: str, request: Request):
    """GET version of test connection endpoint"""
    return await test_region(region_id, request)


@router.get("/health/{region_id}")
async def health_get(region_id: str, request: Request):
    """GET version of health endpoint"""
    return await region_health(region_id, request)


@router.get("/all-results")
async def all_results_get(request: Request):
    """GET version of test all regions endpoint"""
    return await test_all_regions(request)


@router.post("/load-test/{region_id}")
async def load_test_compat(region_id: str, request: Request):
    """Compatibility route for /api/load-test/{region_id}"""
    return await load_test(region_id, request)