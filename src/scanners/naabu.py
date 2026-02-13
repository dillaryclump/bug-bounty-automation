"""
Naabu integration - Fast port scanner.
Discovers open ports on target hosts.
"""

from typing import Any, Dict, List, Optional, Set

from src.scanners.base import BaseScanner
from src.utils.logging import get_logger

logger = get_logger(__name__)


class NaabuScanner(BaseScanner):
    """
    Naabu - Fast SYN/CONNECT port scanner.
    
    Features:
    - Extremely fast (uses raw sockets when possible)
    - Built-in service detection
    - Flexible port ranges
    - JSON output
    """

    def __init__(self) -> None:
        super().__init__("naabu")

    async def scan(
        self,
        targets: List[str],
        ports: str = "top-1000",
        rate: int = 1000,
        timeout: int = 600,
        exclude_cdn: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Scan ports on target hosts.
        
        Args:
            targets: List of hosts/IPs to scan
            ports: Port specification:
                - "top-1000" (default top 1000 ports)
                - "top-100" (top 100 ports)
                - "full" (all 65535 ports - SLOW!)
                - "80,443,8080" (specific ports)
                - "1-1024" (port range)
            rate: Packets per second (default 1000)
            timeout: Total timeout in seconds
            exclude_cdn: Exclude CDN/WAF IPs
            
        Returns:
            List of discovered ports with metadata
        """
        if not targets:
            return []

        logger.info(f"🔍 Scanning ports on {len(targets)} targets...")

        # Create temp file with targets
        targets_file = self._create_temp_file("\n".join(targets))

        try:
            args = [
                "-list", str(targets_file),
                "-json",  # JSON output
                "-silent",  # Suppress banner
                "-rate", str(rate),
                "-timeout", "5",  # Per-host timeout
            ]

            # Port selection
            if ports == "top-1000":
                args.extend(["-top-ports", "1000"])
            elif ports == "top-100":
                args.extend(["-top-ports", "100"])
            elif ports == "full":
                args.extend(["-p", "-"])  # All ports
            else:
                args.extend(["-p", ports])

            if exclude_cdn:
                args.append("-exclude-cdn")

            stdout, stderr, code = await self._run_command(args, timeout=timeout)

            if stderr:
                logger.debug(f"Naabu stderr: {stderr}")

            # Parse JSON results
            results = self._parse_json_lines(stdout)

            logger.info(f"✅ Found {len(results)} open ports")
            return self._normalize_results(results)

        finally:
            # Cleanup temp file
            targets_file.unlink(missing_ok=True)

    def _normalize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize Naabu output to internal format."""
        normalized = []

        for result in results:
            try:
                # Naabu JSON format: {"host": "example.com", "ip": "1.2.3.4", "port": 443}
                normalized.append({
                    "host": result.get("host", ""),
                    "ip": result.get("ip", ""),
                    "port": result.get("port", 0),
                    "protocol": "tcp",  # Naabu only does TCP
                })
            except Exception as e:
                logger.warning(f"Failed to normalize result: {e}")

        return normalized

    async def scan_single(
        self,
        target: str,
        ports: str = "top-1000",
    ) -> List[int]:
        """
        Scan a single target and return list of open ports.
        
        Args:
            target: Host/IP to scan
            ports: Port specification
            
        Returns:
            List of open port numbers
        """
        results = await self.scan([target], ports=ports)
        return sorted([r["port"] for r in results if r.get("port")])

    async def has_web_ports(
        self,
        targets: List[str],
    ) -> Dict[str, bool]:
        """
        Check if targets have common web ports open.
        
        Args:
            targets: List of hosts to check
            
        Returns:
            Dict mapping host -> has_web_ports
        """
        web_ports = "80,443,8080,8443,8000,8888,3000,5000"
        results = await self.scan(targets, ports=web_ports)

        # Group by host
        hosts_with_web = set()
        for result in results:
            if result.get("port"):
                hosts_with_web.add(result.get("host") or result.get("ip"))

        return {target: target in hosts_with_web for target in targets}
