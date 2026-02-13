"""
Authentication dependencies for FastAPI

Supports both API key and JWT authentication.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.api.dependencies.database import get_db
from src.api.auth import decode_token
from src.db.repositories.user_repository import UserRepository
from src.db.models import User, UserRole
from src.utils.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user.
    
    Supports two authentication methods:
    1. JWT Bearer token (preferred)
    2. API key via X-API-Key header (legacy)
    
    In development mode, authentication can be bypassed if no credentials are provided.
    """
    # Development mode bypass - allow access without auth
    if not settings.api_key and not credentials and not x_api_key:
        # Return a mock admin user for development
        from src.db.models import UserRole
        return User(
            id=1,
            username="dev_user",
            email="dev@localhost",
            hashed_password="",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
    
    user_repo = UserRepository(db)
    
    # Try JWT token first
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            user_id = int(payload.get("sub"))
            
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is disabled"
                )
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
    
    # Fall back to API key authentication
    if x_api_key:
        if x_api_key == settings.api_key:
            # Return a mock admin user for API key auth
            from src.db.models import UserRole
            return User(
                id=0,
                username="api_key_user",
                email="api@localhost",
                hashed_password="",
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
    
    # No valid authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_auth(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return current_user


def require_admin(current_user: User = Depends(require_auth)) -> User:
    """Dependency that requires admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def require_user_or_admin(current_user: User = Depends(require_auth)) -> User:
    """Dependency that requires user or admin role (not just viewer)."""
    if current_user.role == UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges. User or Admin role required."
        )
    return current_user

