"""
The Diff Engine - Core change detection logic.
Compares current state with historical state to detect changes.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Asset, ChangeType
from src.db.repositories import AssetChangeRepository, AssetRepository
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DiffEngine:
    """
    The "Secret Weapon" - Detects changes in assets over time.
    
    This is what separates this platform from simple scanners that have no memory.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.asset_repo = AssetRepository(session)
        self.change_repo = AssetChangeRepository(session)

    async def compare_and_update(
        self,
        program_id: int,
        asset_type: str,
        value: str,
        new_data: Dict[str, Any],
    ) -> tuple[Asset, bool, List[str]]:
        """
        Compare new data with existing asset and detect changes.
        
        Returns:
            (asset, is_new, changed_fields)
        """
        # Get or create asset
        asset, is_new = await self.asset_repo.create_or_update(
            program_id=program_id,
            asset_type=asset_type,
            value=value,
        )

        if is_new:
            logger.info(f"🆕 New asset discovered: {value}")
            # Update with new data
            for key, val in new_data.items():
                if hasattr(asset, key):
                    setattr(asset, key, val)
            return asset, True, []

        # Detect changes
        changed_fields = await self._detect_changes(asset, new_data)

        # Update asset with new data
        for key, val in new_data.items():
            if hasattr(asset, key):
                setattr(asset, key, val)

        return asset, False, changed_fields

    async def _detect_changes(
        self,
        asset: Asset,
        new_data: Dict[str, Any],
    ) -> List[str]:
        """
        Detect what changed in an asset.
        
        Critical fields to monitor:
        - http_status: 403 -> 200 could mean access control bypass
        - content_length: Significant change might indicate new content
        - technologies: Tech stack changes require re-testing
        - resolved_ips: Infrastructure changes
        """
        changed_fields = []

        # HTTP Status Change
        if "http_status" in new_data:
            old_status = asset.http_status
            new_status = new_data["http_status"]
            if old_status != new_status:
                await self._record_change(
                    asset=asset,
                    field_name="http_status",
                    old_value=str(old_status) if old_status else None,
                    new_value=str(new_status) if new_status else None,
                    change_type=ChangeType.MODIFIED,
                )
                changed_fields.append("http_status")
                logger.warning(
                    f"🔄 Status change: {asset.value} "
                    f"({old_status} → {new_status})"
                )

        # Content Length Change (>10% difference is significant)
        if "content_length" in new_data:
            old_length = asset.content_length or 0
            new_length = new_data["content_length"] or 0
            if old_length > 0:
                change_pct = abs(new_length - old_length) / old_length
                if change_pct > 0.1:  # 10% threshold
                    await self._record_change(
                        asset=asset,
                        field_name="content_length",
                        old_value=str(old_length),
                        new_value=str(new_length),
                        change_type=ChangeType.MODIFIED,
                    )
                    changed_fields.append("content_length")
                    logger.warning(
                        f"📏 Content size change: {asset.value} "
                        f"({old_length} → {new_length}, {change_pct:.1%})"
                    )

        # Technology Stack Change
        if "technologies" in new_data:
            old_tech = set(asset.technologies or [])
            new_tech = set(new_data["technologies"] or [])
            if old_tech != new_tech:
                added = new_tech - old_tech
                removed = old_tech - new_tech
                if added or removed:
                    await self._record_change(
                        asset=asset,
                        field_name="technologies",
                        old_value=",".join(sorted(old_tech)),
                        new_value=",".join(sorted(new_tech)),
                        change_type=ChangeType.MODIFIED,
                    )
                    changed_fields.append("technologies")
                    logger.warning(
                        f"🔧 Tech stack change: {asset.value}\n"
                        f"  Added: {added}\n"
                        f"  Removed: {removed}"
                    )

        # Page Title Change
        if "page_title" in new_data:
            old_title = asset.page_title
            new_title = new_data["page_title"]
            if old_title != new_title:
                await self._record_change(
                    asset=asset,
                    field_name="page_title",
                    old_value=old_title,
                    new_value=new_title,
                    change_type=ChangeType.MODIFIED,
                )
                changed_fields.append("page_title")

        # Response Hash Change (entire response changed)
        if "response_hash" in new_data:
            old_hash = asset.response_hash
            new_hash = new_data["response_hash"]
            if old_hash and new_hash and old_hash != new_hash:
                await self._record_change(
                    asset=asset,
                    field_name="response_hash",
                    old_value=old_hash,
                    new_value=new_hash,
                    change_type=ChangeType.MODIFIED,
                )
                changed_fields.append("response_hash")
                logger.info(f"🔀 Response changed: {asset.value}")

        # IP Resolution Changes
        if "resolved_ips" in new_data:
            old_ips = set(asset.resolved_ips or [])
            new_ips = set(new_data["resolved_ips"] or [])
            if old_ips != new_ips:
                await self._record_change(
                    asset=asset,
                    field_name="resolved_ips",
                    old_value=",".join(sorted(old_ips)),
                    new_value=",".join(sorted(new_ips)),
                    change_type=ChangeType.MODIFIED,
                )
                changed_fields.append("resolved_ips")
                logger.info(
                    f"🌐 IP change: {asset.value} "
                    f"({len(old_ips)} → {len(new_ips)} IPs)"
                )

        return changed_fields

    async def _record_change(
        self,
        asset: Asset,
        field_name: str,
        old_value: Optional[str],
        new_value: Optional[str],
        change_type: ChangeType,
    ) -> None:
        """Record a change in the database."""
        await self.change_repo.record_change(
            asset_id=asset.id,
            change_type=change_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )

    @staticmethod
    def compute_response_hash(content: bytes) -> str:
        """Compute SHA256 hash of response content."""
        return hashlib.sha256(content).hexdigest()

    async def should_scan(
        self,
        asset: Asset,
        force: bool = False,
    ) -> tuple[bool, str]:
        """
        Decide if an asset should be scanned based on change detection.
        
        Returns:
            (should_scan, reason)
        """
        if force:
            return True, "Force scan requested"

        # Always scan if it's the first time we've seen it
        time_since_first_seen = datetime.utcnow() - asset.first_seen
        if time_since_first_seen.total_seconds() < 300:  # 5 minutes
            return True, "New asset (first scan)"

        # Check for recent changes
        time_since_update = datetime.utcnow() - asset.updated_at
        if time_since_update.total_seconds() < 3600:  # 1 hour
            return True, "Recently modified asset"

        # Check if asset died (was alive, now dead)
        if not asset.is_alive:
            return False, "Asset is no longer alive"

        # Periodic scan (every 24 hours for unchanged assets)
        time_since_last_seen = datetime.utcnow() - asset.last_seen
        if time_since_last_seen.total_seconds() > 86400:  # 24 hours
            return True, "Periodic scan (24h)"

        return False, "No changes detected, skip scan"
