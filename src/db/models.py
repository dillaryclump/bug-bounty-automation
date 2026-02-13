"""
Database models for AutoBug platform.
Using SQLAlchemy 2.x with async support.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class SeverityLevel(str, enum.Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScanStatus(str, enum.Enum):
    """Scan job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class AlertType(str, enum.Enum):
    """Alert notification types."""

    NEW_VULNERABILITY = "new_vulnerability"
    CRITICAL_FINDING = "critical_finding"
    NEW_ASSET = "new_asset"
    SCOPE_CHANGE = "scope_change"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_DIGEST = "weekly_digest"
    SCAN_COMPLETE = "scan_complete"
    SCAN_FAILED = "scan_failed"


class ChangeType(str, enum.Enum):
    """Type of change detected."""

    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"


class ScopeChangeType(str, enum.Enum):
    """Type of scope change."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class Program(Base):
    """Bug bounty program."""

    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # hackerone, bugcrowd
    program_handle: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Scope management
    in_scope: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    out_of_scope: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_scope_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    assets: Mapped[List["Asset"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    scans: Mapped[List["Scan"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="program", cascade="all, delete-orphan")
    scope_history: Mapped[List["ScopeHistory"]] = relationship(back_populates="program", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_program_platform_handle", "platform", "program_handle"),
    )


class Asset(Base):
    """Discovered assets (subdomains, IPs, etc.)."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    
    # Asset identification
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)  # subdomain, ip, etc.
    value: Mapped[str] = mapped_column(String(500), nullable=False)  # The actual subdomain/IP
    
    # DNS & Network info
    resolved_ips: Mapped[Optional[List[str]]] = mapped_column(JSON)
    cnames: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # HTTP Info (from httpx)
    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    content_length: Mapped[Optional[int]] = mapped_column(BigInteger)
    page_title: Mapped[Optional[str]] = mapped_column(String(500))
    technologies: Mapped[Optional[List[str]]] = mapped_column(JSON)
    response_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA256 of response
    
    # State tracking
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # Flexible storage
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="assets")
    ports: Mapped[List["Port"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    changes: Mapped[List["AssetChange"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    vulnerabilities: Mapped[List["Vulnerability"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_asset_program_value", "program_id", "value"),
        Index("idx_asset_type", "asset_type"),
        UniqueConstraint("program_id", "value", name="uq_program_asset"),
    )


class Port(Base):
    """Open ports discovered on assets."""

    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    
    port_number: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str] = mapped_column(String(10), default="tcp", nullable=False)
    service_name: Mapped[Optional[str]] = mapped_column(String(100))
    service_version: Mapped[Optional[str]] = mapped_column(String(200))
    
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="ports")

    __table_args__ = (
        Index("idx_port_asset", "asset_id", "port_number"),
        UniqueConstraint("asset_id", "port_number", "protocol", name="uq_asset_port"),
    )


class Scan(Base):
    """Scan jobs executed."""

    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False)  # recon, vuln, full
    status: Mapped[ScanStatus] = mapped_column(Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False)
    
    # Execution details
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Results summary
    assets_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vulnerabilities_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    changes_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Fleet info
    fleet_size: Mapped[Optional[int]] = mapped_column(Integer)
    fleet_droplet_ids: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    program: Mapped["Program"] = relationship(back_populates="scans")

    __table_args__ = (
        Index("idx_scan_program_status", "program_id", "status"),
        Index("idx_scan_created", "created_at"),
    )


class AssetChange(Base):
    """Track changes detected in assets (the "Diff Engine")."""

    __tablename__ = "asset_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    
    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'http_status', 'technologies'
    
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Alert status
    alerted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="changes")

    __table_args__ = (
        Index("idx_change_asset_detected", "asset_id", "detected_at"),
        Index("idx_change_alerted", "alerted", "detected_at"),
    )


class Vulnerability(Base):
    """Vulnerabilities discovered."""

    __tablename__ = "vulnerabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    
    # Vulnerability details
    template_id: Mapped[str] = mapped_column(String(200), nullable=False)  # Nuclei template ID
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[SeverityLevel] = mapped_column(Enum(SeverityLevel), nullable=False)
    
    # Technical details
    matched_at: Mapped[str] = mapped_column(String(1000), nullable=False)  # URL where vuln was found
    matcher_name: Mapped[Optional[str]] = mapped_column(String(200))
    extracted_results: Mapped[Optional[List[str]]] = mapped_column(JSON)
    request: Mapped[Optional[str]] = mapped_column(Text)
    response: Mapped[Optional[str]] = mapped_column(Text)
    
    # Curl reproduction
    curl_command: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    reference: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # State tracking
    is_new: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    false_positive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="vulnerabilities")

    __table_args__ = (
        Index("idx_vuln_asset_severity", "asset_id", "severity"),
        Index("idx_vuln_new_severity", "is_new", "severity", "created_at"),
        Index("idx_vuln_template", "template_id"),
    )


class Alert(Base):
    """Alert notification history."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Alert details
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    severity: Mapped[Optional[SeverityLevel]] = mapped_column(
        Enum(SeverityLevel, native_enum=False, length=20),
        nullable=True,
        index=True
    )
    
    # Related entities
    program_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    vulnerability_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"),
        nullable=True
    )
    asset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Delivery
    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # discord, slack, email, etc.
    destination: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Status
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    program: Mapped[Optional["Program"]] = relationship(back_populates="alerts")
    vulnerability: Mapped[Optional["Vulnerability"]] = relationship()
    asset: Mapped[Optional["Asset"]] = relationship()

    __table_args__ = (
        Index("idx_alert_type_created", "alert_type", "created_at"),
        Index("idx_alert_sent_success", "sent", "success"),
        Index("idx_alert_channel_sent", "channel", "sent_at"),
    )


class ScopeHistory(Base):
    """Historical record of program scope changes."""

    __tablename__ = "scope_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Program relationship
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Scope data at this point in time
    in_scope: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    out_of_scope: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # What changed from previous version
    changes: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    # Example: [{"type": "added", "scope_type": "in_scope", "value": "*.example.com"}]
    
    # Change summary
    added_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    removed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    modified_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Source of scope data
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )  # "api", "web_scrape", "manual"
    
    # Metadata
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 of scope
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class User(Base):
    """
    User model for authentication and authorization
    
    Roles:
    - admin: Full access to all operations
    - user: Can manage programs, trigger scans, mark vulnerabilities
    - viewer: Read-only access
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False),
        default=UserRole.USER,
        nullable=False
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


    # Relationships
    program: Mapped["Program"] = relationship(back_populates="scope_history")

    __table_args__ = (
        Index("idx_scope_program_created", "program_id", "created_at"),
        Index("idx_scope_checksum", "checksum"),
    )
