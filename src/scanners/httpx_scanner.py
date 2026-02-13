"""
httpx integration - Fast HTTP toolkit for web probing.
Captures HTTP metadata for diff engine analysis.
"""

from typing import Any, Dict, List, Optional, Set
import hashlib

from src.scanners.base import BaseScanner
from src.utils.logging import get_logger

logger = get_logger(__name__)


class HttpxScanner(BaseScanner):
    """
    httpx - Fast and multi-purpose HTTP toolkit.
    
    Captures critical metadata:
    - HTTP status code
    - Content length
    - Page title
    - Technologies
    - Response hash (for diff detection)
    - Server headers
    """

    def __init__(self) -> None:
        super().__init__("httpx")

    async def probe(
        self,
        targets: List[str],
        threads: int = 50,
        timeout: int = 10,
        follow_redirects: bool = True,
        tech_detect: bool = True,
        screenshot: bool = False,
        timeout_total: int = 600,
    ) -> List[Dict[str, Any]]:
        """
        Probe HTTP/HTTPS endpoints and gather metadata.
        
        Args:
            targets: List of domains/URLs to probe
            threads: Number of concurrent threads
            timeout: Timeout per request (seconds)
            follow_redirects: Follow HTTP redirects
            tech_detect: Detect technologies (Wappalyzer)
            screenshot: Take screenshots (requires -screenshot flag support)
            timeout_total: Total timeout for all targets
            
        Returns:
            List of probe results with metadata
        """
        if not targets:
            return []

        logger.info(f"🌐 Probing {len(targets)} targets with httpx...")

        # Create temp file with targets
        targets_file = self._create_temp_file("\n".join(targets))

        try:
            args = [
                "-list", str(targets_file),
                "-json",  # JSON output
                "-silent",  # Suppress progress
                "-status-code",  # Include status code
                "-content-length",  # Include content length
                "-title",  # Extract page title
                "-server",  # Server header
                "-tech-detect" if tech_detect else "",  # Technology detection
                "-follow-redirects" if follow_redirects else "",
                "-threads", str(threads),
                "-timeout", str(timeout),
                "-retries", "2",
                "-hash", "sha256",  # Response hash for diff detection
            ]

            # Remove empty args
            args = [arg for arg in args if arg]

            stdout, stderr, code = await self._run_command(args, timeout=timeout_total)

            if stderr:
                logger.debug(f"httpx stderr: {stderr}")

            # Parse JSON results
            results = self._parse_json_lines(stdout)

            logger.info(f"✅ Probed {len(results)} live targets")
            return self._normalize_results(results)

        finally:
            # Cleanup temp file
            targets_file.unlink(missing_ok=True)

    def _normalize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize httpx output to our internal format."""
        normalized = []

        for result in results:
            try:
                normalized.append({
                    "url": result.get("url", ""),
                    "input": result.get("input", ""),
                    "host": result.get("host", ""),
                    "port": result.get("port", 0),
                    "scheme": result.get("scheme", ""),
                    "status_code": result.get("status_code", 0),
                    "content_length": result.get("content_length", 0),
                    "title": result.get("title", ""),
                    "server": result.get("server", ""),
                    "technologies": result.get("technologies", []) or result.get("tech", []),
                    "response_hash": result.get("hash", {}).get("body_sha256", ""),
                    "final_url": result.get("final_url", result.get("url", "")),
                    "chain_status_codes": result.get("chain_status_codes", []),
                    "time": result.get("time", ""),
                    "lines": result.get("lines", 0),
                    "words": result.get("words", 0),
                })
            except Exception as e:
                logger.warning(f"Failed to normalize result: {e}")

        return normalized

    async def probe_single(
        self,
        target: str,
        timeout: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """
        Probe a single target.
        
        Args:
            target: Domain or URL
            timeout: Timeout in seconds
            
        Returns:
            Probe result or None if failed
        """
        results = await self.probe([target], threads=1, timeout=timeout, timeout_total=timeout + 5)
        return results[0] if results else None

    async def filter_live(
        self,
        targets: List[str],
        status_codes: Optional[List[int]] = None,
    ) -> Set[str]:
        """
        Filter targets to only live ones.
        
        Args:
            targets: List of targets
            status_codes: Acceptable status codes (default: any 2xx/3xx/4xx)
            
        Returns:
            Set of live URLs
        """
        results = await self.probe(targets)
        
        live = set()
        for result in results:
            status = result.get("status_code", 0)
            
            if status_codes:
                if status in status_codes:
                    live.add(result["url"])
            elif 200 <= status < 500:  # Consider 2xx, 3xx, 4xx as "live"
                live.add(result["url"])
        
        return live
