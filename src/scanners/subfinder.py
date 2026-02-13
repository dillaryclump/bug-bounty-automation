"""
Subfinder integration - Subdomain enumeration tool.
Fast passive subdomain discovery using multiple sources.
"""

from typing import List, Optional, Set

from src.scanners.base import BaseScanner
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SubfinderScanner(BaseScanner):
    """
    Subfinder - Fast passive subdomain discovery.
    
    Features:
    - Uses 40+ sources (crt.sh, VirusTotal, SecurityTrails, etc.)
    - Passive only (no DNS queries)
    - Fast and reliable
    - JSON output support
    """

    def __init__(self) -> None:
        super().__init__("subfinder")

    async def scan(
        self,
        domain: str,
        recursive: bool = False,
        sources: Optional[List[str]] = None,
        exclude_sources: Optional[List[str]] = None,
        timeout: int = 300,
    ) -> Set[str]:
        """
        Enumerate subdomains for a domain.
        
        Args:
            domain: Target domain (e.g., 'example.com')
            recursive: Recursively find subdomains
            sources: Specific sources to use (if None, uses all)
            exclude_sources: Sources to exclude
            timeout: Timeout in seconds
            
        Returns:
            Set of discovered subdomains
        """
        logger.info(f"🔍 Enumerating subdomains for: {domain}")

        args = [
            "-d", domain,
            "-all",  # Use all sources
            "-json",  # JSON output
            "-silent",  # Suppress banner
        ]

        if recursive:
            args.append("-recursive")

        if sources:
            args.extend(["-sources", ",".join(sources)])

        if exclude_sources:
            args.extend(["-exclude-sources", ",".join(exclude_sources)])

        stdout, stderr, code = await self._run_command(args, timeout=timeout)

        if code != 0 and stderr:
            logger.warning(f"Subfinder stderr: {stderr}")

        # Parse JSON output
        results = self._parse_json_lines(stdout)
        
        subdomains = set()
        for result in results:
            # Subfinder JSON format: {"host": "subdomain.example.com", "source": "crtsh"}
            if "host" in result:
                subdomains.add(result["host"].lower())

        logger.info(f"✅ Found {len(subdomains)} subdomains for {domain}")
        return subdomains

    async def scan_multiple(
        self,
        domains: List[str],
        timeout_per_domain: int = 300,
    ) -> dict[str, Set[str]]:
        """
        Scan multiple domains.
        
        Args:
            domains: List of domains to scan
            timeout_per_domain: Timeout per domain
            
        Returns:
            Dict mapping domain -> set of subdomains
        """
        results = {}
        for domain in domains:
            try:
                subdomains = await self.scan(domain, timeout=timeout_per_domain)
                results[domain] = subdomains
            except Exception as e:
                logger.error(f"Failed to scan {domain}: {e}")
                results[domain] = set()
        
        return results
