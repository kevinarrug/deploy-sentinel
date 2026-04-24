"""Core monitoring loop for deploy-sentinel."""

from __future__ import annotations

import logging
import time
from typing import List, Optional

import docker

from deploy_sentinel.alert_policy import PolicyStore
from deploy_sentinel.config import SentinelConfig
from deploy_sentinel.container_filter import ContainerFilter, FilterConfig
from deploy_sentinel.health_check import HealthChecker
from deploy_sentinel.metrics import MetricsCollector
from deploy_sentinel.notifier import DeployEvent, EventType
from deploy_sentinel.rollback import RollbackManager
from deploy_sentinel.snapshot import SnapshotStore

log = logging.getLogger(__name__)


class DeployMonitor:
    """Polls Docker containers, checks health, and triggers rollbacks."""

    def __init__(
        self,
        config: SentinelConfig,
        client=None,
        notifier=None,
    ) -> None:
        self.config = config
        self.client = client or docker.from_env()
        self.notifier = notifier

        filter_cfg = FilterConfig(
            required_labels=config.required_labels,
            name_patterns=config.name_patterns,
            excluded_names=config.excluded_names,
        )
        self._filter = ContainerFilter(filter_cfg)
        self._health = HealthChecker(self.client)
        self._rollback = RollbackManager(self.client)
        self._snapshots = SnapshotStore()
        self._metrics = MetricsCollector()
        self._policies = PolicyStore()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> None:  # pragma: no cover
        """Block forever, polling at the configured interval."""
        log.info(
            "deploy-sentinel started (interval=%ss, rollback=%s)",
            self.config.check_interval,
            not self.config.no_rollback,
        )
        while True:
            try:
                self.check_and_act()
            except Exception:  # noqa: BLE001
                log.exception("Unexpected error during check cycle")
            time.sleep(self.config.check_interval)

    def check_and_act(self) -> None:
        """Single monitoring cycle: inspect containers and react."""
        containers = self._list_containers()
        for container in containers:
            self._process(container)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _list_containers(self) -> list:
        all_containers = self.client.containers.list()
        return self._filter.apply(all_containers)

    def _process(self, container) -> None:
        cid = container.id
        name = container.name

        health = self._health.check(container)
        self._metrics.record_health_check(cid, name, health)

        policy = self._policies.get(cid)
        if not health.is_healthy:
            policy.record_failure()
            self._metrics.record_health_failure(cid, name)
            log.warning("Container %s is unhealthy: %s", name, health.message)

            if not self.config.no_rollback and policy.should_alert():
                self._trigger_rollback(container)
        else:
            policy.reset()

    def _trigger_rollback(self, container) -> None:
        name = container.name
        log.info("Initiating rollback for %s", name)
        record = self._rollback.rollback(container)
        self._metrics.record_rollback(container.id, name)
        if self.notifier and record:
            event = DeployEvent(
                event_type=EventType.ROLLBACK,
                container_name=name,
                image=record.previous_image,
            )
            self.notifier.send(event)
