"""Webhook notification channel for deploy-sentinel."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Optional

from deploy_sentinel.notifier import DeployEvent, NotificationChannel

logger = logging.getLogger(__name__)


class WebhookChannel:
    """Sends deployment events as JSON POST requests to a webhook URL."""

    def __init__(
        self,
        url: str,
        timeout: int = 5,
        secret_header: Optional[str] = None,
        secret_value: Optional[str] = None,
    ) -> None:
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid webhook URL: {url!r}")
        self.url = url
        self.timeout = timeout
        self._extra_headers: dict[str, str] = {}
        if secret_header and secret_value:
            self._extra_headers[secret_header] = secret_value

    def _build_payload(self, event: DeployEvent) -> bytes:
        data = {
            "event_type": event.event_type.value,
            "container_id": event.container_id,
            "container_name": event.container_name,
            "image": event.image,
            "message": event.message,
            "previous_image": event.previous_image,
            "metadata": event.metadata,
        }
        return json.dumps(data).encode("utf-8")

    def send(self, event: DeployEvent) -> bool:
        payload = self._build_payload(event)
        headers = {"Content-Type": "application/json", **self._extra_headers}
        req = urllib.request.Request(self.url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                logger.debug("Webhook %s responded with HTTP %s", self.url, status)
                return 200 <= status < 300
        except urllib.error.HTTPError as exc:
            logger.warning("Webhook HTTP error %s: %s", exc.code, exc.reason)
            return False
        except urllib.error.URLError as exc:
            logger.warning("Webhook connection error: %s", exc.reason)
            return False
