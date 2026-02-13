"""
Bugcrowd Scope Parser
Parses scope from Bugcrowd program pages via API and web scraping.
"""

import re
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from src.scope.base import BaseScopeParser, ScopeData, ScopeParserFactory
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BugcrowdParser(BaseScopeParser):
    """
    Parse scope from Bugcrowd programs.
    
    Supports both API (if token provided) and web scraping fallback.
    """
    
    BASE_URL = "https://bugcrowd.com"
    API_URL = "https://api.bugcrowd.com"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get Bugcrowd API authentication headers."""
        if not self.api_token:
            return {}
        
        return {
            "Authorization": f"Token {self.api_token}",
        }
    
    async def fetch_scope(self, program_handle: str) -> ScopeData:
        """
        Fetch scope from Bugcrowd.
        
        Args:
            program_handle: Bugcrowd program code
            
        Returns:
            ScopeData with current scope
        """
        logger.info(f"Fetching Bugcrowd scope for: {program_handle}")
        
        # Try API first if we have a token
        if self.api_token:
            try:
                return await self._fetch_via_api(program_handle)
            except Exception as e:
                logger.warning(f"API fetch failed, falling back to scraping: {e}")
        
        # Fallback to web scraping
        return await self._fetch_via_scraping(program_handle)
    
    async def _fetch_via_api(self, program_handle: str) -> ScopeData:
        """Fetch scope via Bugcrowd API."""
        url = f"{self.API_URL}/programs/{program_handle}"
        
        response = await self.client.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract scope from targets
        in_scope = []
        out_of_scope = []
        
        targets = data.get("targets", [])
        for target in targets:
            name = target.get("name", "")
            category = target.get("category", "")
            
            if not name:
                continue
            
            normalized = self.normalize_scope_item(name)
            
            # Bugcrowd uses "in scope" vs "out of scope" in target properties
            if target.get("in_scope", True):
                in_scope.append(normalized)
            else:
                out_of_scope.append(normalized)
        
        return ScopeData(
            in_scope=in_scope,
            out_of_scope=out_of_scope,
            platform="bugcrowd",
            program_handle=program_handle,
            program_name=data.get("name", program_handle),
            program_url=f"{self.BASE_URL}/{program_handle}",
            program_description=data.get("brief", ""),
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
        title_elem = soup.find("h1", class_=re.compile("program|title", re.I))
        if not title_elem:
            title_elem = soup.find("h1")
        if title_elem:
            program_name = title_elem.get_text(strip=True)
        
        # Bugcrowd uses a specific scope table structure
        in_scope = self._extract_scope_targets(soup, in_scope=True)
        out_of_scope = self._extract_scope_targets(soup, in_scope=False)
        
        return ScopeData(
            in_scope=in_scope,
            out_of_scope=out_of_scope,
            platform="bugcrowd",
            program_handle=program_handle,
            program_name=program_name,
            program_url=url,
            raw_data={"html_length": len(response.text)},
        )
    
    def _extract_scope_targets(
        self,
        soup: BeautifulSoup,
        in_scope: bool = True
    ) -> List[str]:
        """Extract scope targets from Bugcrowd page."""
        items = []
        
        # Look for targets table/list
        # Bugcrowd typically uses tables or lists with specific classes
        targets_section = soup.find(
            ["table", "div"],
            class_=re.compile("target|scope|asset", re.I)
        )
        
        if not targets_section:
            # Try finding by header
            header_text = "in scope" if in_scope else "out of scope"
            header = soup.find(
                text=re.compile(header_text, re.IGNORECASE)
            )
            if header:
                targets_section = header.find_parent(["div", "section", "table"])
        
        if not targets_section:
            return items
        
        # Extract from table rows
        for row in targets_section.find_all("tr"):
            cells = row.find_all(["td", "th"])
            for cell in cells:
                text = cell.get_text(strip=True)
                
                if self._looks_like_scope_item(text):
                    normalized = self.normalize_scope_item(text)
                    if normalized and normalized not in items:
                        items.append(normalized)
        
        # Also check for lists
        for item in targets_section.find_all("li"):
            text = item.get_text(strip=True)
            
            if self._looks_like_scope_item(text):
                normalized = self.normalize_scope_item(text)
                if normalized and normalized not in items:
                    items.append(normalized)
        
        # Check for code blocks
        for code in targets_section.find_all("code"):
            text = code.get_text(strip=True)
            
            if self._looks_like_scope_item(text):
                normalized = self.normalize_scope_item(text)
                if normalized and normalized not in items:
                    items.append(normalized)
        
        return items
    
    def _looks_like_scope_item(self, text: str) -> bool:
        """Check if text looks like a scope item."""
        # Skip common non-scope words
        skip_words = [
            "target", "scope", "asset", "type", "category", "eligible",
            "yes", "no", "priority", "points", "reward", "bounty"
        ]
        
        if any(word in text.lower() for word in skip_words):
            if not any(c in text for c in [".", "*", "/"]):
                return False
        
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
        
        # App ID patterns (mobile)
        if re.match(r'^(com|org|app|io)\.[a-z0-9\.\-_]+$', text, re.I):
            return True
        
        return False
    
    def parse_scope_item(self, item: str) -> Dict[str, any]:
        """Parse Bugcrowd scope item."""
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
        
        # Check for app ID
        elif re.match(r'^(com|org|app|io)\.[a-z0-9\.\-_]+$', normalized, re.I):
            result["type"] = "app_id"
        
        return result


# Register parser
ScopeParserFactory.register("bugcrowd", BugcrowdParser)
