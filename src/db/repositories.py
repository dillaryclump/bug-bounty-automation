"""
Repository pattern for database operations.
Provides clean abstraction over database queries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, delete, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    Asset,
    AssetChange,
    ChangeType,
    Port,
    Program,
    Scan,
    ScanStatus,
    SeverityLevel,
    Vulnerability,
)


class ProgramRepository:
    """Repository for Program operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        platform: str,
        program_handle: str,
        program_name: str,
        in_scope: Optional[List[str]] = None,
        out_of_scope: Optional[List[str]] = None,
    ) -> Program:
        """Create a new program."""
        program = Program(
            platform=platform,
            program_handle=program_handle,
            program_name=program_name,
            in_scope=in_scope or [],
            out_of_scope=out_of_scope or [],
        )
        self.session.add(program)
        await self.session.flush()
        return program

    async def get_by_id(self, program_id: int) -> Optional[Program]:
        """Get program by ID."""
        result = await self.session.execute(
            select(Program).where(Program.id == program_id)
        )
        return result.scalar_one_or_none()

    async def get_by_handle(self, platform: str, program_handle: str) -> Optional[Program]:
        """Get program by platform and handle."""
        result = await self.session.execute(
            select(Program).where(
                and_(
                    Program.platform == platform,
                    Program.program_handle == program_handle,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_programs(self) -> List[Program]:
        """Get all active programs."""
        result = await self.session.execute(
            select(Program).where(Program.is_active == True)
        )
        return list(result.scalars().all())

    async def update_scope(
        self,
        program_id: int,
        in_scope: Optional[List[str]] = None,
        out_of_scope: Optional[List[str]] = None,
    ) -> None:
        """Update program scope."""
        await self.session.execute(
            update(Program)
            .where(Program.id == program_id)
            .values(
                in_scope=in_scope,
                out_of_scope=out_of_scope,
                last_scope_check=datetime.utcnow(),
            )
        )


class AssetRepository:
    """Repository for Asset operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_or_update(
        self,
        program_id: int,
        asset_type: str,
        value: str,
        **kwargs: Any,
    ) -> tuple[Asset, bool]:
        """
        Create asset or update if exists.
        Returns (asset, is_new) tuple.
        """
        # Try to find existing asset
        result = await self.session.execute(
            select(Asset).where(
                and_(
                    Asset.program_id == program_id,
                    Asset.value == value,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing asset
            for key, val in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, val)
            existing.last_seen = datetime.utcnow()
            existing.is_alive = True
            return existing, False
        else:
            # Create new asset
            asset = Asset(
                program_id=program_id,
                asset_type=asset_type,
                value=value,
                **kwargs,
            )
            self.session.add(asset)
            await self.session.flush()
            return asset, True

    async def get_by_program(self, program_id: int, alive_only: bool = True) -> List[Asset]:
        """Get all assets for a program."""
        query = select(Asset).where(Asset.program_id == program_id)
        if alive_only:
            query = query.where(Asset.is_alive == True)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_changed_assets(
        self,
        program_id: int,
        since: datetime,
    ) -> List[Asset]:
        """Get assets that changed since a specific time."""
        result = await self.session.execute(
            select(Asset).where(
                and_(
                    Asset.program_id == program_id,
                    Asset.updated_at >= since,
                )
            )
        )
        return list(result.scalars().all())

    async def mark_as_dead(self, asset_ids: List[int]) -> None:
        """Mark assets as no longer alive."""
        await self.session.execute(
            update(Asset)
            .where(Asset.id.in_(asset_ids))
            .values(is_alive=False)
        )


class AssetChangeRepository:
    """Repository for tracking asset changes (The Diff Engine)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_change(
        self,
        asset_id: int,
        change_type: ChangeType,
        field_name: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
    ) -> AssetChange:
        """Record a detected change."""
        change = AssetChange(
            asset_id=asset_id,
            change_type=change_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )
        self.session.add(change)
        await self.session.flush()
        return change

    async def get_unalerted_changes(
        self,
        severity_threshold: Optional[str] = None,
    ) -> List[AssetChange]:
        """Get changes that haven't been alerted yet."""
        query = select(AssetChange).where(AssetChange.alerted == False)
        query = query.order_by(desc(AssetChange.detected_at))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_alerted(self, change_ids: List[int]) -> None:
        """Mark changes as alerted."""
        await self.session.execute(
            update(AssetChange)
            .where(AssetChange.id.in_(change_ids))
            .values(alerted=True)
        )


class VulnerabilityRepository:
    """Repository for Vulnerability operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        asset_id: int,
        template_id: str,
        name: str,
        severity: SeverityLevel,
        matched_at: str,
        **kwargs: Any,
    ) -> Vulnerability:
        """Create a new vulnerability finding."""
        vuln = Vulnerability(
            asset_id=asset_id,
            template_id=template_id,
            name=name,
            severity=severity,
            matched_at=matched_at,
            **kwargs,
        )
        self.session.add(vuln)
        await self.session.flush()
        return vuln

    async def get_new_vulnerabilities(
        self,
        min_severity: SeverityLevel = SeverityLevel.MEDIUM,
    ) -> List[Vulnerability]:
        """Get new, unreported vulnerabilities."""
        severity_order = {
            SeverityLevel.CRITICAL: 5,
            SeverityLevel.HIGH: 4,
            SeverityLevel.MEDIUM: 3,
            SeverityLevel.LOW: 2,
            SeverityLevel.INFO: 1,
        }
        min_level = severity_order[min_severity]
        
        result = await self.session.execute(
            select(Vulnerability).where(
                and_(
                    Vulnerability.is_new == True,
                    Vulnerability.false_positive == False,
                    Vulnerability.severity.in_([
                        s for s, v in severity_order.items() if v >= min_level
                    ]),
                )
            ).order_by(desc(Vulnerability.created_at))
        )
        return list(result.scalars().all())

    async def mark_reported(self, vuln_ids: List[int]) -> None:
        """Mark vulnerabilities as reported."""
        await self.session.execute(
            update(Vulnerability)
            .where(Vulnerability.id.in_(vuln_ids))
            .values(reported=True, is_new=False)
        )


class ScanRepository:
    """Repository for Scan operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        program_id: int,
        scan_type: str,
    ) -> Scan:
        """Create a new scan job."""
        scan = Scan(
            program_id=program_id,
            scan_type=scan_type,
            status=ScanStatus.PENDING,
        )
        self.session.add(scan)
        await self.session.flush()
        return scan

    async def update_status(
        self,
        scan_id: int,
        status: ScanStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Update scan status."""
        values: Dict[str, Any] = {"status": status}
        
        if status == ScanStatus.RUNNING and not error_message:
            values["started_at"] = datetime.utcnow()
        elif status in (ScanStatus.COMPLETED, ScanStatus.FAILED):
            values["completed_at"] = datetime.utcnow()
        
        if error_message:
            values["error_message"] = error_message
        
        await self.session.execute(
            update(Scan).where(Scan.id == scan_id).values(**values)
        )

    async def get_active_scans(self) -> List[Scan]:
        """Get all currently running scans."""
        result = await self.session.execute(
            select(Scan).where(
                Scan.status.in_([ScanStatus.PENDING, ScanStatus.RUNNING])
            )
        )
        return list(result.scalars().all())
