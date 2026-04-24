"""Health check module for monitoring Docker container status."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import docker
from docker.errors import DockerException, NotFound

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    UNKNOWN = "unknown"
    NOT_FOUND = "not_found"


@dataclass
class ContainerHealth:
    container_id: str
    container_name: str
    status: HealthStatus
    checked_at: datetime = field(default_factory=datetime.utcnow)
    exit_code: Optional[int] = None
    error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY


class HealthChecker:
    """Checks the health of Docker containers."""

    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        self._client = docker_client or docker.from_env()

    def check(self, container_name: str) -> ContainerHealth:
        """Check the health status of a container by name."""
        try:
            container = self._client.containers.get(container_name)
            return self._evaluate(container)
        except NotFound:
            logger.warning("Container '%s' not found.", container_name)
            return ContainerHealth(
                container_id="",
                container_name=container_name,
                status=HealthStatus.NOT_FOUND,
                error="Container not found",
            )
        except DockerException as exc:
            logger.error("Docker error checking '%s': %s", container_name, exc)
            return ContainerHealth(
                container_id="",
                container_name=container_name,
                status=HealthStatus.UNKNOWN,
                error=str(exc),
            )

    def _evaluate(self, container) -> ContainerHealth:
        """Evaluate container state and map to HealthStatus."""
        attrs = container.attrs
        state = attrs.get("State", {})
        health = state.get("Health", {})
        health_status = health.get("Status", "").lower()
        running = state.get("Running", False)
        exit_code = state.get("ExitCode")

        if health_status == "healthy":
            status = HealthStatus.HEALTHY
        elif health_status == "unhealthy":
            status = HealthStatus.UNHEALTHY
        elif health_status == "starting":
            status = HealthStatus.STARTING
        elif running:
            status = HealthStatus.HEALTHY  # No HEALTHCHECK defined but running
        else:
            status = HealthStatus.UNHEALTHY

        return ContainerHealth(
            container_id=container.id,
            container_name=container.name,
            status=status,
            exit_code=exit_code,
        )
