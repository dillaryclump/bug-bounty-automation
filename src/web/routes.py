"""
Web Routes
Server-side rendered pages for the dashboard.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Main dashboard page."""
    # Get dashboard stats from API
    from src.api.routes.stats import get_dashboard_stats
    
    stats = await get_dashboard_stats(db)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "page_title": "Dashboard",
        },
    )


@router.get("/programs", response_class=HTMLResponse)
async def programs_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Programs listing page."""
    from src.api.routes.programs import list_programs
    
    programs = await list_programs(db=db)
    
    return templates.TemplateResponse(
        "programs.html",
        {
            "request": request,
            "programs": programs.programs,
            "total": programs.total,
            "page_title": "Programs",
        },
    )


@router.get("/vulnerabilities", response_class=HTMLResponse)
async def vulnerabilities_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Vulnerabilities listing page."""
    from src.api.routes.vulnerabilities import list_vulnerabilities
    
    vulns = await list_vulnerabilities(db=db, new_only=False)
    
    return templates.TemplateResponse(
        "vulnerabilities.html",
        {
            "request": request,
            "vulnerabilities": vulns.vulnerabilities,
            "severity_counts": vulns.severity_counts,
            "total": vulns.total,
            "page_title": "Vulnerabilities",
        },
    )


@router.get("/assets", response_class=HTMLResponse)
async def assets_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Assets listing page."""
    from src.api.routes.assets import list_assets
    
    assets = await list_assets(db=db)
    
    return templates.TemplateResponse(
        "assets.html",
        {
            "request": request,
            "assets": assets.assets,
            "total": assets.total,
            "page_title": "Assets",
        },
    )


@router.get("/scans", response_class=HTMLResponse)
async def scans_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Scans listing page."""
    from src.api.routes.scans import list_scans
    
    scans = await list_scans(db=db)
    
    return templates.TemplateResponse(
        "scans.html",
        {
            "request": request,
            "scans": scans.scans,
            "total": scans.total,
            "page_title": "Scans",
        },
    )


@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Alerts listing page."""
    from src.api.routes.alerts import list_alerts
    
    alerts = await list_alerts(db=db)
    
    return templates.TemplateResponse(
        "alerts.html",
        {
            "request": request,
            "alerts": alerts.alerts,
            "total": alerts.total,
            "page_title": "Alerts",
        },
    )
