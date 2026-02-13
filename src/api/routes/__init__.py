"""
API Routes
Route modules for API endpoints.
"""

# Import route modules to make them available
from src.api.routes import programs, assets, vulnerabilities, scans, alerts, scope, stats

__all__ = [
    "programs",
    "assets", 
    "vulnerabilities",
    "scans",
    "alerts",
    "scope",
    "stats",
]
