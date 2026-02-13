"""
AutoBug - Automated Bug Bounty Platform
Core application configuration using Pydantic Settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="AutoBug", description="Application name")
    environment: str = Field(default="development", description="Environment (dev/staging/prod)")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    database_url: PostgresDsn = Field(
        description="PostgreSQL connection URL",
        default="postgresql+asyncpg://autobug:password@localhost:5432/autobug_db",
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Max overflow connections")

    # Redis
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_cache_ttl: int = Field(default=3600, description="Redis cache TTL in seconds")

    # Prefect
    prefect_api_url: str = Field(
        default="http://localhost:4200/api",
        description="Prefect API endpoint"
    )
    prefect_logging_level: str = Field(default="INFO")

    # DigitalOcean (Axiom Fleet)
    do_api_token: Optional[str] = Field(default=None, description="DigitalOcean API token")
    do_region: str = Field(default="nyc3", description="Default region for droplets")
    do_size: str = Field(default="s-2vcpu-4gb", description="Default droplet size")

    # Platform APIs
    hackerone_api_token: Optional[str] = Field(default=None)
    bugcrowd_api_token: Optional[str] = Field(default=None)

    # Alerting
    discord_webhook_url: Optional[str] = Field(default=None)
    pushover_user_key: Optional[str] = Field(default=None)
    pushover_app_token: Optional[str] = Field(default=None)
    slack_webhook_url: Optional[str] = Field(default=None)
    
    # Alert Configuration
    alert_min_severity: str = Field(
        default="high",
        description="Minimum severity to trigger alerts (critical/high/medium/low/info)"
    )
    alert_critical_channel: str = Field(
        default="discord",
        description="Channel for critical alerts (discord/slack/both)"
    )
    alert_default_channel: str = Field(
        default="discord",
        description="Default channel for alerts (discord/slack/both)"
    )
    alert_batch_window: int = Field(
        default=300,
        description="Seconds to batch multiple alerts together"
    )
    enable_daily_summary: bool = Field(
        default=True,
        description="Send daily summary reports"
    )
    daily_summary_time: str = Field(
        default="09:00",
        description="Time to send daily summary (HH:MM UTC)"
    )
    enable_weekly_digest: bool = Field(
        default=True,
        description="Send weekly digest reports"
    )
    weekly_digest_day: str = Field(
        default="monday",
        description="Day for weekly digest"
    )

    # Interactsh (OOB Detection)
    interactsh_server_url: str = Field(default="https://interact.sh")
    interactsh_token: Optional[str] = Field(default=None)

    # Scanning Configuration
    max_concurrent_scans: int = Field(default=5, description="Max concurrent scan jobs")
    scan_timeout: int = Field(default=3600, description="Scan timeout in seconds")
    nuclei_rate_limit: int = Field(default=150, description="Nuclei requests per second")
    httpx_threads: int = Field(default=50, description="httpx concurrent threads")

    # Fleet Management
    axiom_fleet_size: int = Field(default=10, description="Default fleet size")
    axiom_max_fleet_size: int = Field(default=50, description="Maximum fleet size")
    auto_scale_enabled: bool = Field(default=True, description="Enable auto-scaling")
    
    # API Configuration
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    @property
    def database_url_str(self) -> str:
        """Get database URL as string."""
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
