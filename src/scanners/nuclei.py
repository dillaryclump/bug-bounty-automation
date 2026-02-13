"""
Nuclei integration - Fast and customizable vulnerability scanner.
The industry standard for automated vulnerability detection.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.scanners.base import BaseScanner
from src.utils.logging import get_logger

logger = get_logger(__name__)


class NucleiScanner(BaseScanner):
    """
    Nuclei - Fast vulnerability scanner with YAML-based templates.
    
    Features:
    - 5000+ vulnerability templates
    - Custom template support
    - Rate limiting
    - Severity filtering
    - JSON output
    - Interactsh OOB support
    """

    def __init__(self) -> None:
        super().__init__("nuclei")
        self.templates_path = self._get_templates_path()

    def _get_templates_path(self) -> Optional[Path]:
        """Get Nuclei templates directory."""
        # Try common locations
        common_paths = [
            Path.home() / "nuclei-templates",
            Path.home() / ".local" / "nuclei-templates",
            Path("/root/nuclei-templates"),
        ]
        
        for path in common_paths:
            if path.exists():
                return path
        
        return None

    async def scan(
        self,
        targets: List[str],
        templates: Optional[List[str]] = None,
        severity: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        rate_limit: int = 150,
        timeout: int = 5,
        retries: int = 1,
        interactsh_url: Optional[str] = None,
        max_host_error: int = 30,
        scan_timeout: int = 3600,
    ) -> List[Dict[str, Any]]:
        """
        Scan targets with Nuclei.
        
        Args:
            targets: List of URLs to scan
            templates: Specific templates to use (e.g., ['cves/', 'exposures/'])
            severity: Filter by severity (critical, high, medium, low, info)
            tags: Include only templates with these tags
            exclude_tags: Exclude templates with these tags
            rate_limit: Requests per second
            timeout: Request timeout in seconds
            retries: Number of retries per request
            interactsh_url: Interactsh server URL for OOB detection
            max_host_error: Max errors before skipping host
            scan_timeout: Total scan timeout in seconds
            
        Returns:
            List of vulnerability findings
        """
        if not targets:
            return []

        logger.info(f"🔍 Scanning {len(targets)} targets with Nuclei...")

        # Create temp file with targets
        targets_file = self._create_temp_file("\n".join(targets))

        try:
            args = [
                "-list", str(targets_file),
                "-json",  # JSON output
                "-silent",  # Suppress banner
                "-rate-limit", str(rate_limit),
                "-timeout", str(timeout),
                "-retries", str(retries),
                "-max-host-error", str(max_host_error),
                "-stats",  # Show progress stats
            ]

            # Template selection
            if templates:
                for template in templates:
                    args.extend(["-t", template])
            elif not severity and not tags:
                # Default: all templates
                args.append("-nt")  # Use all templates from nuclei-templates

            # Severity filtering
            if severity:
                args.extend(["-severity", ",".join(severity)])

            # Tag filtering
            if tags:
                args.extend(["-tags", ",".join(tags)])
            
            if exclude_tags:
                args.extend(["-exclude-tags", ",".join(exclude_tags)])

            # Interactsh for OOB detection
            if interactsh_url:
                args.extend(["-interactsh-url", interactsh_url])

            stdout, stderr, code = await self._run_command(args, timeout=scan_timeout)

            if stderr:
                logger.debug(f"Nuclei stderr: {stderr}")

            # Parse JSON results
            results = self._parse_json_lines(stdout)

            logger.info(f"✅ Found {len(results)} vulnerabilities")
            return self._normalize_results(results)

        finally:
            # Cleanup temp file
            targets_file.unlink(missing_ok=True)

    def _normalize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize Nuclei output to internal format."""
        normalized = []

        for result in results:
            try:
                # Extract info
                template_id = result.get("template-id", "")
                info = result.get("info", {})
                
                normalized.append({
                    # Template info
                    "template_id": template_id,
                    "name": info.get("name", ""),
                    "severity": info.get("severity", "info").lower(),
                    "tags": info.get("tags", []),
                    "description": info.get("description", ""),
                    "reference": info.get("reference", []),
                    "author": info.get("author", ""),
                    "classification": info.get("classification", {}),
                    
                    # Finding details
                    "matched_at": result.get("matched-at", result.get("host", "")),
                    "matcher_name": result.get("matcher-name", ""),
                    "type": result.get("type", ""),
                    "extracted_results": result.get("extracted-results", []),
                    "ip": result.get("ip", ""),
                    "timestamp": result.get("timestamp", datetime.utcnow().isoformat()),
                    
                    # Request/response evidence
                    "request": result.get("request", ""),
                    "response": result.get("response", ""),
                    "curl_command": result.get("curl-command", ""),
                    
                    # Metadata
                    "metadata": result.get("meta", {}),
                })
            except Exception as e:
                logger.warning(f"Failed to normalize result: {e}")

        return normalized

    async def scan_by_severity(
        self,
        targets: List[str],
        min_severity: str = "medium",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scan and group results by severity.
        
        Args:
            targets: List of URLs to scan
            min_severity: Minimum severity to include
            
        Returns:
            Dict mapping severity -> list of findings
        """
        severity_order = ["info", "low", "medium", "high", "critical"]
        min_index = severity_order.index(min_severity.lower())
        severities = severity_order[min_index:]

        results = await self.scan(targets, severity=severities)

        # Group by severity
        grouped: Dict[str, List[Dict[str, Any]]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": [],
        }

        for result in results:
            severity = result.get("severity", "info")
            if severity in grouped:
                grouped[severity].append(result)

        return grouped

    async def scan_new_assets_only(
        self,
        targets: List[str],
        full_templates: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Scan new assets with appropriate template set.
        
        Args:
            targets: New asset URLs
            full_templates: Use all templates (slower but comprehensive)
            
        Returns:
            List of findings
        """
        logger.info(f"🆕 Scanning {len(targets)} NEW assets")

        if full_templates:
            # Full scan for new assets
            return await self.scan(
                targets,
                severity=["critical", "high", "medium"],
                rate_limit=150,
            )
        else:
            # Quick scan with high-value templates only
            return await self.scan(
                targets,
                templates=["cves/", "exposures/", "vulnerabilities/"],
                severity=["critical", "high"],
                rate_limit=200,
            )

    async def scan_changed_assets(
        self,
        targets: List[str],
        changed_fields: Set[str],
    ) -> List[Dict[str, Any]]:
        """
        Scan modified assets with targeted templates based on what changed.
        
        Args:
            targets: Changed asset URLs
            changed_fields: Set of fields that changed (e.g., 'technologies')
            
        Returns:
            List of findings
        """
        logger.info(f"🔄 Scanning {len(targets)} MODIFIED assets")
        
        # Build targeted template list based on changes
        templates = []
        tags = []

        if "technologies" in changed_fields:
            # Tech stack changed - scan for tech-specific vulns
            templates.extend(["cves/", "vulnerabilities/"])
            logger.info("Tech stack changed - running CVE/vulnerability templates")
        
        if "http_status" in changed_fields:
            # Status changed - check for new exposures
            templates.extend(["exposures/", "misconfiguration/"])
            logger.info("Status changed - checking exposures")

        if "content_length" in changed_fields:
            # Content changed - check for new endpoints
            templates.extend(["exposures/", "default-logins/"])

        if not templates:
            # Generic rescan with medium+ severity
            return await self.scan(
                targets,
                severity=["critical", "high", "medium"],
                rate_limit=200,
            )

        return await self.scan(
            targets,
            templates=list(set(templates)),  # Deduplicate
            severity=["critical", "high", "medium"],
            rate_limit=200,
        )

    async def update_templates(self) -> bool:
        """Update Nuclei templates to latest version."""
        logger.info("Updating Nuclei templates...")
        
        try:
            stdout, stderr, code = await self._run_command(
                ["-update-templates"],
                timeout=300,
            )
            
            if code == 0:
                logger.info("✅ Templates updated successfully")
                return True
            else:
                logger.error(f"Failed to update templates: {stderr}")
                return False
        except Exception as e:
            logger.error(f"Template update failed: {e}")
            return False

    async def get_template_stats(self) -> Dict[str, Any]:
        """Get statistics about available templates."""
        if not self.templates_path or not self.templates_path.exists():
            return {"error": "Templates path not found"}

        # Count templates by category
        stats = {
            "total": 0,
            "categories": {},
        }

        try:
            for category_dir in self.templates_path.iterdir():
                if category_dir.is_dir() and not category_dir.name.startswith("."):
                    templates = list(category_dir.glob("**/*.yaml"))
                    count = len(templates)
                    stats["categories"][category_dir.name] = count
                    stats["total"] += count

            return stats
        except Exception as e:
            logger.error(f"Failed to get template stats: {e}")
            return {"error": str(e)}
