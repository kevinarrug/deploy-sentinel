"""Rollback automation for Docker containers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import docker
from docker.models.containers import Container

logger = logging.getLogger(__name__)


@dataclass
class RollbackRecord:
    """Represents a single rollback event."""

    container_name: str
    previous_image: str
    rolled_back_at: datetime = field(default_factory=datetime.utcnow)
    success: bool = False
    error: Optional[str] = None


class RollbackManager:
    """Manages rollback operations for Docker containers."""

    def __init__(self, client: Optional[docker.DockerClient] = None) -> None:
        self._client = client or docker.from_env()
        self._history: list[RollbackRecord] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_previous_image(self, container: Container) -> Optional[str]:
        """Return the image tag/id that preceded the current one, if available."""
        labels = container.labels or {}
        return labels.get("deploy-sentinel.previous-image")

    def rollback(self, container_name: str) -> RollbackRecord:
        """Stop the running container and restart it from its previous image."""
        record = RollbackRecord(container_name=container_name, previous_image="")
        try:
            container: Container = self._client.containers.get(container_name)
            previous_image = self.get_previous_image(container)

            if not previous_image:
                raise ValueError(
                    f"No previous image label found on container '{container_name}'. "
                    "Cannot perform rollback."
                )

            record.previous_image = previous_image
            logger.info(
                "Rolling back '%s' to image '%s'", container_name, previous_image
            )

            env = container.attrs.get("Config", {}).get("Env") or []
            ports = container.attrs.get("HostConfig", {}).get("PortBindings") or {}

            container.stop(timeout=10)
            container.remove()

            self._client.containers.run(
                image=previous_image,
                name=container_name,
                environment=env,
                ports=ports,
                detach=True,
            )

            record.success = True
            logger.info("Rollback of '%s' completed successfully.", container_name)
        except Exception as exc:  # noqa: BLE001
            record.error = str(exc)
            logger.error("Rollback of '%s' failed: %s", container_name, exc)

        self._history.append(record)
        return record

    def history(self) -> list[RollbackRecord]:
        """Return a copy of the rollback history."""
        return list(self._history)
