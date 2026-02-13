"""
Reconnaissance Workflow - The main automation pipeline.

This workflow orchestrates the full reconnaissance process:
1. Subdomain enumeration (Subfinder)
2. DNS resolution (filter dead domains)
3. Port scanning (Naabu)
4. HTTP probing (httpx)
5. Diff engine analysis (detect changes)
6. Database updates

This is where the magic happens! 🎯
"""

from datetime import datetime
from typing import Any, Dict, List, Set

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

from src.core.diff_engine import DiffEngine
from src.db.models import ChangeType
from src.db.repositories import AssetRepository, ProgramRepository
from src.db.session import db_manager
from src.scanners.dns_resolver import DnsResolver
from src.scanners.httpx_scanner import HttpxScanner
from src.scanners.naabu import NaabuScanner
from src.scanners.subfinder import SubfinderScanner
from src.utils.logging import get_logger

logger = get_logger(__name__)


@task(name="enumerate_subdomains", retries=2, retry_delay_seconds=60)
async def enumerate_subdomains_task(domains: List[str]) -> Set[str]:
    """Task: Enumerate subdomains using Subfinder."""
    scanner = SubfinderScanner()
    all_subdomains = set()
    
    for domain in domains:
        try:
            subdomains = await scanner.scan(domain, recursive=False)
            all_subdomains.update(subdomains)
        except Exception as e:
            logger.error(f"Subdomain enumeration failed for {domain}: {e}")
    
    return all_subdomains


@task(name="resolve_dns", retries=2, retry_delay_seconds=30)
async def resolve_dns_task(domains: List[str]) -> Dict[str, List[str]]:
    """Task: Resolve domains to IPs using DNS."""
    resolver = DnsResolver()
    try:
        return await resolver.resolve(domains)
    except Exception as e:
        logger.error(f"DNS resolution failed: {e}")
        return {}


@task(name="scan_ports", retries=1, retry_delay_seconds=60)
async def scan_ports_task(targets: List[str]) -> List[Dict[str, Any]]:
    """Task: Scan ports using Naabu."""
    scanner = NaabuScanner()
    try:
        return await scanner.scan(targets, ports="top-1000")
    except Exception as e:
        logger.error(f"Port scanning failed: {e}")
        return []


@task(name="probe_http", retries=2, retry_delay_seconds=30)
async def probe_http_task(targets: List[str]) -> List[Dict[str, Any]]:
    """Task: Probe HTTP endpoints using httpx."""
    scanner = HttpxScanner()
    try:
        return await scanner.probe(targets, threads=50, tech_detect=True)
    except Exception as e:
        logger.error(f"HTTP probing failed: {e}")
        return []


@task(name="update_assets")
async def update_assets_task(
    program_id: int,
    probe_results: List[Dict[str, Any]],
    dns_results: Dict[str, List[str]],
) -> Dict[str, Any]:
    """
    Task: Update assets in database using Diff Engine.
    
    This is where we detect changes and decide what to scan next!
    """
    stats = {
        "new_assets": 0,
        "modified_assets": 0,
        "unchanged_assets": 0,
        "total_changes": 0,
        "changed_fields": {},
    }

    async with db_manager.get_session() as session:
        diff_engine = DiffEngine(session)
        
        for result in probe_results:
            host = result.get("host") or result.get("input", "")
            if not host:
                continue

            # Prepare asset data
            asset_data = {
                "http_status": result.get("status_code"),
                "content_length": result.get("content_length"),
                "page_title": result.get("title"),
                "technologies": result.get("technologies", []),
                "response_hash": result.get("response_hash"),
                "resolved_ips": dns_results.get(host, []),
            }

            try:
                # Run diff engine analysis
                asset, is_new, changed_fields = await diff_engine.compare_and_update(
                    program_id=program_id,
                    asset_type="subdomain",
                    value=host,
                    new_data=asset_data,
                )

                # Update statistics
                if is_new:
                    stats["new_assets"] += 1
                elif changed_fields:
                    stats["modified_assets"] += 1
                    stats["total_changes"] += len(changed_fields)
                    for field in changed_fields:
                        stats["changed_fields"][field] = stats["changed_fields"].get(field, 0) + 1
                else:
                    stats["unchanged_assets"] += 1

            except Exception as e:
                logger.error(f"Failed to update asset {host}: {e}")

    return stats


@task(name="save_ports")
async def save_ports_task(program_id: int, port_results: List[Dict[str, Any]]) -> int:
    """Task: Save discovered ports to database."""
    saved_count = 0
    
    async with db_manager.get_session() as session:
        asset_repo = AssetRepository(session)
        
        # Group ports by host
        ports_by_host: Dict[str, List[int]] = {}
        for result in port_results:
            host = result.get("host") or result.get("ip", "")
            port = result.get("port")
            if host and port:
                if host not in ports_by_host:
                    ports_by_host[host] = []
                ports_by_host[host].append(port)
        
        # TODO: Update ports in database (requires Port repository methods)
        saved_count = len(port_results)
        logger.info(f"Discovered ports on {len(ports_by_host)} hosts")
    
    return saved_count


@flow(
    name="reconnaissance_flow",
    description="Full reconnaissance pipeline with diff engine analysis",
    task_runner=ConcurrentTaskRunner(),
)
async def reconnaissance_flow(program_id: int, force_full_scan: bool = False) -> Dict[str, Any]:
    """
    Main reconnaissance workflow.
    
    This orchestrates the entire recon process:
    1. Get program scope from database
    2. Enumerate subdomains
    3. Resolve DNS
    4. Scan ports
    5. Probe HTTP endpoints
    6. Run diff engine
    7. Update database
    
    Args:
        program_id: Database ID of the program to scan
        force_full_scan: Force full scan even for unchanged assets
        
    Returns:
        Dict with scan statistics and results
    """
    logger.info(f"🚀 Starting reconnaissance for program ID: {program_id}")
    start_time = datetime.utcnow()

    # Step 1: Get program scope
    async with db_manager.get_session() as session:
        program_repo = ProgramRepository(session)
        program = await program_repo.get_by_id(program_id)
        
        if not program:
            raise ValueError(f"Program {program_id} not found")
        
        if not program.in_scope:
            raise ValueError(f"Program {program_id} has no in-scope targets")
        
        root_domains = program.in_scope
        logger.info(f"📋 Scope: {len(root_domains)} root domain(s)")

    # Step 2: Enumerate subdomains
    logger.info("🔍 Phase 1: Subdomain Enumeration")
    subdomains = await enumerate_subdomains_task(root_domains)
    logger.info(f"✅ Found {len(subdomains)} total subdomains")

    if not subdomains:
        logger.warning("No subdomains found, ending workflow")
        return {"error": "No subdomains discovered"}

    # Step 3: Resolve DNS
    logger.info("🌐 Phase 2: DNS Resolution")
    dns_results = await resolve_dns_task(list(subdomains))
    alive_domains = [d for d, ips in dns_results.items() if ips]
    logger.info(f"✅ {len(alive_domains)} domains are alive")

    if not alive_domains:
        logger.warning("No alive domains, ending workflow")
        return {"error": "No domains resolved"}

    # Step 4: Port scanning (optional, can be slow)
    logger.info("🔍 Phase 3: Port Scanning")
    port_results = await scan_ports_task(alive_domains[:100])  # Limit to first 100 for speed
    await save_ports_task(program_id, port_results)

    # Step 5: HTTP probing (THE CRITICAL STEP)
    logger.info("🌐 Phase 4: HTTP Probing")
    probe_results = await probe_http_task(alive_domains)
    logger.info(f"✅ {len(probe_results)} endpoints responded")

    # Step 6: Diff Engine + Database Update (THE MAGIC!)
    logger.info("🎯 Phase 5: Diff Engine Analysis")
    stats = await update_assets_task(program_id, probe_results, dns_results)

    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Final report
    report = {
        "program_id": program_id,
        "duration_seconds": duration,
        "subdomains_found": len(subdomains),
        "alive_domains": len(alive_domains),
        "http_endpoints": len(probe_results),
        "ports_discovered": len(port_results),
        "new_assets": stats["new_assets"],
        "modified_assets": stats["modified_assets"],
        "unchanged_assets": stats["unchanged_assets"],
        "total_changes": stats["total_changes"],
        "changed_fields": stats["changed_fields"],
        "timestamp": datetime.utcnow().isoformat(),
    }

    logger.info("=" * 60)
    logger.info("📊 RECONNAISSANCE COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"⏱️  Duration: {duration:.1f} seconds")
    logger.info(f"🆕 New Assets: {stats['new_assets']}")
    logger.info(f"🔄 Modified Assets: {stats['modified_assets']}")
    logger.info(f"✔️  Unchanged Assets: {stats['unchanged_assets']}")
    logger.info(f"📝 Total Changes: {stats['total_changes']}")
    if stats["changed_fields"]:
        logger.info(f"🔍 Changed Fields: {stats['changed_fields']}")
    logger.info("=" * 60)

    return report


@flow(name="quick_recon_flow")
async def quick_recon_flow(program_id: int) -> Dict[str, Any]:
    """
    Quick reconnaissance - HTTP probing only.
    
    Use this for fast change detection without full subdomain enumeration.
    Useful for hourly/frequent scans.
    """
    logger.info(f"⚡ Quick recon for program ID: {program_id}")

    # Get existing assets from database
    async with db_manager.get_session() as session:
        asset_repo = AssetRepository(session)
        assets = await asset_repo.get_by_program(program_id, alive_only=True)
        
        if not assets:
            logger.warning("No existing assets, run full recon first")
            return {"error": "No existing assets"}
        
        targets = [asset.value for asset in assets]
        logger.info(f"📋 Probing {len(targets)} known assets")

    # Probe HTTP
    probe_results = await probe_http_task(targets)
    
    # Update database
    dns_results = {}  # We already have DNS data from previous scans
    stats = await update_assets_task(program_id, probe_results, dns_results)

    return {
        "program_id": program_id,
        "mode": "quick",
        "assets_probed": len(targets),
        "modified_assets": stats["modified_assets"],
        "total_changes": stats["total_changes"],
    }
