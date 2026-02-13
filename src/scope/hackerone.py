"""
HackerOne Scope Parser
Parses scope from HackerOne program pages via API and web scraping.
"""

import re
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from src.scope.base import BaseScopeParser, ScopeData, ScopeParserFactory
from src.utils.logging import get_logger

logger = get_logger(__name__)


class HackerOneParser(BaseScopeParser):
    """
    Parse scope from HackerOne programs.
    
    Supports both API (if token provided) and web scraping fallback.
    """
    
    BASE_URL = "https://hackerone.com"
    API_URL = "https://api.hackerone.com/v1"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get HackerOne API authentication headers."""
        if not self.api_token:
            return {}
        
        # HackerOne uses API token format: username:token
        return {
            "Authorization": f"Basic {self.api_token}",
        }
    
    async def fetch_scope(self, program_handle: str) -> ScopeData:
        """
        Fetch scope from HackerOne.
        
        First tries API if token available, falls back to web scraping.
        
        Args:
            program_handle: HackerOne program handle
            
        Returns:
            ScopeData with current scope
        """
        logger.info(f"Fetching HackerOne scope for: {program_handle}")
        
        # Try API first if we have a token
        if self.api_token:
            try:
                return await self._fetch_via_api(program_handle)
            except Exception as e:
                logger.warning(f"API fetch failed, falling back to scraping: {e}")
        
        # Fallback to web scraping
        return await self._fetch_via_scraping(program_handle)
    
    async def _fetch_via_api(self, program_handle: str) -> ScopeData:
        """Fetch scope via HackerOne API."""
        url = f"{self.API_URL}/programs/{program_handle}"
        
        response = await self.client.get(url)
        response.raise_for_status()
        
        data = response.json()
        program_data = data.get("data", {}).get("attributes", {})
        
        # Extract scope from structured targets
        in_scope = []
        out_of_scope = []
        
        for target in program_data.get("in_scope", []):
            asset_type = target.get("asset_type", "")
            asset_identifier = target.get("asset_identifier", "")
            
            if asset_identifier:
                in_scope.append(self.normalize_scope_item(asset_identifier))
        
        for target in program_data.get("out_of_scope", []):
            asset_type = target.get("asset_type", "")
            asset_identifier = target.get("asset_identifier", "")
            
            if asset_identifier:
                out_of_scope.append(self.normalize_scope_item(asset_identifier))
        
        return ScopeData(
            in_scope=in_scope,
            out_of_scope=out_of_scope,
            platform="hackerone",
            program_handle=program_handle,
            program_name=program_data.get("name", program_handle),
            program_url=f"{self.BASE_URL}/{program_handle}",
            program_description=program_data.get("policy", ""),
            raw_data=data,
        )
    
    async def _fetch_via_scraping(self, program_handle: str) -> ScopeData:
        """Fetch scope via web scraping (fallback)."""
        url = f"{self.BASE_URL}/{program_handle}"
        
        response = await self.client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract program name
        program_name = program_handle
        title_elem = soup.find("h1", class_=re.compile("program.*title", re.I))
        if title_elem:
            program_name = title_elem.get_text(strip=True)
        
        # Extract scope sections
        in_scope = self._extract_scope_section(soup, "in scope")
        out_of_scope = self._extract_scope_section(soup, "out of scope")
        
        return ScopeData(
            in_scope=in_scope,
            out_of_scope=out_of_scope,
            platform="hackerone",
            program_handle=program_handle,
            program_name=program_name,
            program_url=url,
            raw_data={"html_length": len(response.text)},
        )
    
    def _extract_scope_section(
        self,
        soup: BeautifulSoup,
        section_name: str
    ) -> List[str]:
        """Extract scope items from a section."""
        items = []
        
        # Look for section header
        section_header = soup.find(
            text=re.compile(section_name, re.IGNORECASE)
        )
        
        if not section_header:
            return items
        
        # Find parent section
        section = section_header.find_parent(
            ["div", "section", "article"],
            class_=re.compile("scope|asset|target", re.I)
        )
        
        if not section:
            section = section_header.find_parent(["div", "section"])
        
        if not section:
            return items
        
        # Extract all links and code blocks (common patterns)
        for elem in section.find_all(["a", "code", "li", "td"]):
            text = elem.get_text(strip=True)
            
            # Filter out obvious non-scope items
            if not text or len(text) < 3:
                continue
            
            if any(skip in text.lower() for skip in [
                "learn more", "read more", "click here", "submit",
                "example", "guidelines", "rules", "policy"
            ]):
                continue
            
            # Check if looks like a scope item
            if self._looks_like_scope_item(text):
                normalized = self.normalize_scope_item(text)
                if normalized and normalized not in items:
                    items.append(normalized)
        
        return items
    
    def _looks_like_scope_item(self, text: str) -> bool:
        """Check if text looks like a scope item."""
        # Domain patterns
        if re.match(r'^[\*\w][\w\-\.]*\.[a-z]{2,}', text, re.I):
            return True
        
        # IP patterns
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', text):
            return True
        
        # CIDR patterns
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}', text):
            return True
        
        # Wildcard domains
        if text.startswith("*."):
            return True
        
        return False
    
    def parse_scope_item(self, item: str) -> Dict[str, any]:
        """Parse HackerOne scope item."""
        normalized = self.normalize_scope_item(item)
        
        result = {
            "value": normalized,
            "wildcard": False,
            "type": "other",
        }
        
        # Check for wildcard
        if normalized.startswith("*."):
            result["wildcard"] = True
            result["type"] = "wildcard"
            result["pattern"] = re.escape(normalized.replace("*.", ""))
        
        # Check for domain/subdomain
        elif re.match(r'^[\w][\w\-\.]*\.[a-z]{2,}$', normalized, re.I):
            if normalized.count(".") == 1:
                result["type"] = "domain"
            else:
                result["type"] = "subdomain"
        
        # Check for IP
        elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', normalized):
            result["type"] = "ip"
        
        # Check for CIDR
        elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$', normalized):
            result["type"] = "cidr"
        
        return result


# Register parser
ScopeParserFactory.register("hackerone", HackerOneParser)
