"""
Rate Limiting Middleware

Protects API endpoints from abuse with configurable rate limits.
"""

import time
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    
    For production, use Redis for distributed rate limiting.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_size = 60  # 1 minute in seconds
        
        # Storage: {client_id: [(timestamp, count), ...]}
        self.request_history = defaultdict(list)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier (IP address or API key)."""
        # Try to get API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key[:8]}"  # Use first 8 chars
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get first IP in case of multiple proxies
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    def _cleanup_old_requests(self, client_id: str, current_time: float):
        """Remove requests older than the time window."""
        cutoff_time = current_time - self.window_size
        self.request_history[client_id] = [
            (ts, count) for ts, count in self.request_history[client_id]
            if ts > cutoff_time
        ]
    
    def _check_rate_limit(self, client_id: str) -> tuple[bool, dict]:
        """
        Check if the client has exceeded rate limits.
        
        Returns:
            (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        
        # Clean up old requests
        self._cleanup_old_requests(client_id, current_time)
        
        # Count requests in current window
        total_requests = sum(count for _, count in self.request_history[client_id])
        
        # Get recent burst (last 5 seconds)
        burst_cutoff = current_time - 5
        burst_requests = sum(
            count for ts, count in self.request_history[client_id]
            if ts > burst_cutoff
        )
        
        # Rate limit info
        rate_limit_info = {
            "limit": self.requests_per_minute,
            "remaining": max(0, self.requests_per_minute - total_requests),
            "reset": int(current_time + self.window_size)
        }
        
        # Check limits
        if total_requests >= self.requests_per_minute:
            rate_limit_info["retry_after"] = int(
                min(ts for ts, _ in self.request_history[client_id]) + self.window_size - current_time
            )
            return False, rate_limit_info
        
        if burst_requests >= self.burst_size:
            rate_limit_info["retry_after"] = 5  # Wait 5 seconds for burst
            return False, rate_limit_info
        
        return True, rate_limit_info
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with rate limiting."""
        # Skip rate limiting for certain paths
        if request.url.path in ["/health", "/", "/api/docs", "/api/redoc", "/api/openapi.json"]:
            return await call_next(request)
        
        # Skip rate limiting for static files
        if request.url.path.startswith("/static/"):
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        is_allowed, rate_limit_info = self._check_rate_limit(client_id)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {client_id}")
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests. Please try again in {rate_limit_info.get('retry_after', 60)} seconds."
                },
                headers={
                    "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_limit_info["reset"]),
                    "Retry-After": str(rate_limit_info.get("retry_after", 60))
                }
            )
        
        # Record this request
        current_time = time.time()
        self.request_history[client_id].append((current_time, 1))
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"] - 1)
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])
        
        return response
