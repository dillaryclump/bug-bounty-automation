"""
Base Scope Parser
Abstract base class for platform-specific scope parsers.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ScopeData:
    """Structured scope data from a bug bounty program."""
    
    in_scope: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)
    platform: str = ""
    program_handle: str = ""
    program_name: str = ""
    
    # Additional metadata
    bounty_table: Optional[Dict] = None
    program_description: Optional[str] = None
    program_url: Optional[str] = None
    last_updated: Optional[str] = None
    
    # Raw data for debugging
    raw_data: Optional[Dict] = None
    
    def calculate_checksum(self) -> str:
        """Calculate SHA256 checksum of scope for change detection."""
        # Sort for consistent checksums
        scope_repr = {
            "in_scope": sorted(self.in_scope),
            "out_of_scope": sorted(self.out_of_scope),
        }
        scope_json = json.dumps(scope_repr, sort_keys=True)
        return hashlib.sha256(scope_json.encode()).hexdigest()
    
    def __str__(self) -> str:
        return (
            f"ScopeData({self.platform}/{self.program_handle}: "
            f"{len(self.in_scope)} in scope, {len(self.out_of_scope)} out of scope)"
        )


class BaseScopeParser(ABC):
    """
    Abstract base class for scope parsers.
    
    Each platform (HackerOne, Bugcrowd, etc.) implements their own parser.
    """
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize parser.
        
        Args:
            api_token: Optional API token for authenticated requests
            timeout: HTTP request timeout in seconds
        """
        self.api_token = api_token
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=self._get_headers(),
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests."""
        headers = {
            "User-Agent": "AutoBug/1.0 (Bug Bounty Automation)",
            "Accept": "application/json",
        }
        
        if self.api_token:
            headers.update(self._get_auth_headers())
        
        return headers
    
    @abstractmethod
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get platform-specific authentication headers."""
        pass
    
    @abstractmethod
    async def fetch_scope(self, program_handle: str) -> ScopeData:
        """
        Fetch current scope for a program.
        
        Args:
            program_handle: Program identifier (handle/slug)
            
        Returns:
            ScopeData object with current scope
            
        Raises:
            ValueError: If program not found
            httpx.HTTPError: If request fails
        """
        pass
    
    @abstractmethod
    def parse_scope_item(self, item: str) -> Dict[str, any]:
        """
        Parse a scope item into structured data.
        
        Args:
            item: Raw scope item string
            
        Returns:
            Dictionary with parsed components:
            - type: subdomain, domain, ip, range, etc.
            - value: normalized value
            - wildcard: boolean
            - pattern: regex pattern if applicable
        """
        pass
    
    def normalize_scope_item(self, item: str) -> str:
        """
        Normalize scope item for consistent comparison.
        
        Args:
            item: Raw scope item
            
        Returns:
            Normalized scope item
        """
        # Remove protocol
        item = item.replace("https://", "").replace("http://", "")
        
        # Remove trailing slash
        item = item.rstrip("/")
        
        # Convert to lowercase
        item = item.lower().strip()
        
        return item
    
    def categorize_scope_items(
        self,
        items: List[str]
    ) -> Dict[str, List[str]]:
        """
        Categorize scope items by type.
        
        Args:
            items: List of scope items
            
        Returns:
            Dictionary mapping type to items
        """
        categories = {
            "wildcard": [],
            "domain": [],
            "subdomain": [],
            "ip": [],
            "cidr": [],
            "other": [],
        }
        
        for item in items:
            parsed = self.parse_scope_item(item)
            item_type = parsed.get("type", "other")
            
            if item_type in categories:
                categories[item_type].append(parsed["value"])
            else:
                categories["other"].append(parsed["value"])
        
        return categories
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class ScopeParserFactory:
    """Factory for creating platform-specific scope parsers."""
    
    _parsers = {}
    
    @classmethod
    def register(cls, platform: str, parser_class):
        """Register a parser for a platform."""
        cls._parsers[platform.lower()] = parser_class
    
    @classmethod
    def create(cls, platform: str, **kwargs) -> BaseScopeParser:
        """
        Create a parser instance for a platform.
        
        Args:
            platform: Platform name (hackerone, bugcrowd, etc.)
            **kwargs: Arguments to pass to parser constructor
            
        Returns:
            Parser instance
            
        Raises:
            ValueError: If platform not supported
        """
        platform = platform.lower()
        
        if platform not in cls._parsers:
            raise ValueError(
                f"Unsupported platform: {platform}. "
                f"Supported: {', '.join(cls._parsers.keys())}"
            )
        
        parser_class = cls._parsers[platform]
        return parser_class(**kwargs)
    
    @classmethod
    def supported_platforms(cls) -> List[str]:
        """Get list of supported platforms."""
        return list(cls._parsers.keys())
