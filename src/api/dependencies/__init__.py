"""
FastAPI Dependencies
Dependency injection for FastAPI endpoints.
"""

from src.api.dependencies.database import get_db
from src.api.dependencies.auth import get_current_user, require_auth

__all__ = [
    "get_db",
    "get_current_user",
    "require_auth",
]
