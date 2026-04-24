"""Configuration loading and validation for deploy-sentinel."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SentinelConfig:
    """Top-level configuration for the deploy sentinel."""

    # Health check settings
    health_check_interval: int = 30  # seconds
    health_check_retries: int = 3
    unhealthy_threshold: int = 2

    # Rollback settings
    rollback_enabled: bool = True
    rollback_label: str = "deploy-sentinel.previous-image"

    # Notification settings
    webhook_url: Optional[str] = None
    log_level: str = "INFO"

    # Container filter labels
    watched_labels: List[str] = field(default_factory=lambda: ["deploy-sentinel.watch=true"])

    # Metrics
    metrics_retention_hours: int = 24

    @classmethod
    def from_env(cls) -> "SentinelConfig":
        """Build a SentinelConfig from environment variables."""
        return cls(
            health_check_interval=int(os.getenv("SENTINEL_HEALTH_INTERVAL", "30")),
            health_check_retries=int(os.getenv("SENTINEL_HEALTH_RETRIES", "3")),
            unhealthy_threshold=int(os.getenv("SENTINEL_UNHEALTHY_THRESHOLD", "2")),
            rollback_enabled=os.getenv("SENTINEL_ROLLBACK_ENABLED", "true").lower() == "true",
            rollback_label=os.getenv("SENTINEL_ROLLBACK_LABEL", "deploy-sentinel.previous-image"),
            webhook_url=os.getenv("SENTINEL_WEBHOOK_URL"),
            log_level=os.getenv("SENTINEL_LOG_LEVEL", "INFO"),
            watched_labels=_parse_list(os.getenv("SENTINEL_WATCHED_LABELS", "deploy-sentinel.watch=true")),
            metrics_retention_hours=int(os.getenv("SENTINEL_METRICS_RETENTION_HOURS", "24")),
        )

    def validate(self) -> List[str]:
        """Return a list of validation error messages (empty if valid)."""
        errors: List[str] = []
        if self.health_check_interval < 5:
            errors.append("health_check_interval must be >= 5 seconds")
        if self.health_check_retries < 1:
            errors.append("health_check_retries must be >= 1")
        if self.unhealthy_threshold < 1:
            errors.append("unhealthy_threshold must be >= 1")
        if self.metrics_retention_hours < 1:
            errors.append("metrics_retention_hours must be >= 1")
        if self.webhook_url and not self.webhook_url.startswith(("http://", "https://")):
            errors.append("webhook_url must start with http:// or https://")
        return errors


def _parse_list(value: str) -> List[str]:
    """Split a comma-separated string into a stripped list."""
    return [item.strip() for item in value.split(",") if item.strip()]
