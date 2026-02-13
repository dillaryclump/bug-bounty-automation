"""
DNS resolution utilities.
Wrapper around puredns/massdns for fast DNS resolution.
"""

import asyncio
from typing import Dict, List, Set

from src.scanners.base import BaseScanner, ScannerError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DnsResolver(BaseScanner):
    """
    DNS resolution using puredns (wrapper around massdns).
    
    Features:
    - Extremely fast (can resolve millions of domains)
    - Wildcard detection and filtering
    - Multiple resolver support
    - Validation of results
    """

    def __init__(self) -> None:
        try:
            super().__init__("puredns")
        except ScannerError:
            # Fallback to basic DNS resolution if puredns not available
            logger.warning("puredns not found, using fallback DNS resolution")
            self.binary_path = None

    async def resolve(
        self,
        domains: List[str],
        resolvers: str = "8.8.8.8,1.1.1.1",
        wildcard_batch: int = 1000000,
        timeout: int = 600,
    ) -> Dict[str, List[str]]:
        """
        Resolve domains to IPs.
        
        Args:
            domains: List of domains to resolve
            resolvers: Comma-separated resolver IPs
            wildcard_batch: Wildcard detection batch size
            timeout: Timeout in seconds
            
        Returns:
            Dict mapping domain -> list of IPs
        """
        if not domains:
            return {}

        if self.binary_path is None:
            return await self._fallback_resolve(domains)

        logger.info(f"🌐 Resolving {len(domains)} domains...")

        # Create temp files
        domains_file = self._create_temp_file("\n".join(domains))
        output_file = self._create_temp_file("", suffix=".resolved.txt")

        try:
            args = [
                "resolve",
                str(domains_file),
                "-r", resolvers,
                "-w", str(output_file),
                "--wildcard-batch", str(wildcard_batch),
            ]

            stdout, stderr, code = await self._run_command(args, timeout=timeout)

            if code != 0:
                logger.warning(f"puredns exited with code {code}: {stderr}")

            # Read resolved domains
            resolved_domains = set()
            if output_file.exists():
                with open(output_file) as f:
                    resolved_domains = {line.strip() for line in f if line.strip()}

            logger.info(f"✅ Resolved {len(resolved_domains)}/{len(domains)} domains")

            # Get IPs for resolved domains (basic A record lookup)
            return await self._get_ips_for_domains(list(resolved_domains))

        finally:
            # Cleanup
            domains_file.unlink(missing_ok=True)
            output_file.unlink(missing_ok=True)

    async def _get_ips_for_domains(self, domains: List[str]) -> Dict[str, List[str]]:
        """Get IP addresses for domains using asyncio DNS lookups."""
        results = {}
        
        for domain in domains:
            try:
                # Use asyncio's getaddrinfo for async DNS lookup
                loop = asyncio.get_event_loop()
                addrinfo = await loop.getaddrinfo(domain, None)
                ips = list(set(addr[4][0] for addr in addrinfo))
                results[domain] = ips
            except Exception as e:
                logger.debug(f"Failed to resolve {domain}: {e}")
                results[domain] = []

        return results

    async def _fallback_resolve(self, domains: List[str]) -> Dict[str, List[str]]:
        """Fallback DNS resolution without puredns."""
        logger.info(f"🌐 Resolving {len(domains)} domains (fallback mode)...")
        
        results = await self._get_ips_for_domains(domains)
        
        resolved_count = sum(1 for ips in results.values() if ips)
        logger.info(f"✅ Resolved {resolved_count}/{len(domains)} domains")
        
        return results

    async def filter_alive(
        self,
        domains: List[str],
    ) -> Set[str]:
        """
        Filter domains to only those that resolve.
        
        Args:
            domains: List of domains
            
        Returns:
            Set of domains that successfully resolve
        """
        resolved = await self.resolve(domains)
        return {domain for domain, ips in resolved.items() if ips}
