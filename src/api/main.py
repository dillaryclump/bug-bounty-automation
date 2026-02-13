"""
FastAPI Application
Main application instance and configuration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import settings
from src.db.session import db_manager
from src.utils.logging import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AutoBug API...")
    
    # Initialize database
    await db_manager.create_tables()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AutoBug API...")


# Create FastAPI application
app = FastAPI(
    title="AutoBug API",
    description="Automated Bug Bounty Platform API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware (optional, comment out in development if needed)
from src.api.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    burst_size=10
)

# Mount static files
try:
    app.mount(
        "/static",
        StaticFiles(directory="src/web/static"),
        name="static",
    )
except RuntimeError:
    # Static directory might not exist yet
    logger.warning("Static directory not found - skipping mount")

# Templates
templates = Jinja2Templates(directory="src/web/templates")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "autobug-api",
    }


# Root redirect
@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")


# Import and include routers
# Note: Import here to avoid circular dependencies
def setup_routes():
    """Setup API routes."""
    from src.api.routes import (
        programs,
        assets,
        vulnerabilities,
        scans,
        alerts,
        scope,
        stats,
        auth,
        websocket,
        export,
        bulk,
    )
    from src.web import routes as web_routes
    
    # Authentication routes (no tags override, using router's tags)
    app.include_router(auth.router, prefix="/api")
    
    # WebSocket routes
    app.include_router(websocket.router, prefix="/api")
    
    # API routes
    app.include_router(programs.router, prefix="/api/programs", tags=["Programs"])
    app.include_router(assets.router, prefix="/api/assets", tags=["Assets"])
    app.include_router(vulnerabilities.router, prefix="/api/vulnerabilities", tags=["Vulnerabilities"])
    app.include_router(scans.router, prefix="/api/scans", tags=["Scans"])
    app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
    app.include_router(scope.router, prefix="/api/scope", tags=["Scope"])
    app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
    app.include_router(export.router, prefix="/api")
    app.include_router(bulk.router, prefix="/api")
    
    # Web routes
    app.include_router(web_routes.router, prefix="", tags=["Web"])
    
    logger.info("Routes configured")


# Call setup after app creation
setup_routes()
