"""Tests for deploy_sentinel.webhook."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from deploy_sentinel.notifier import DeployEvent, EventType
from deploy_sentinel.webhook import WebhookChannel


def _make_event(**kwargs) -> DeployEvent:
    defaults = dict(
        event_type=EventType.DEPLOY_FAILURE,
        container_id="c1",
        container_name="api",
        image="myapp:2.0",
        message="Health check failed",
    )
    defaults.update(kwargs)
    return DeployEvent(**defaults)


class TestWebhookChannel:
    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Invalid webhook URL"):
            WebhookChannel(url="ftp://bad")

    def test_send_success(self):
        channel = WebhookChannel(url="http://example.com/hook")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = channel.send(_make_event())
        assert result is True

    def test_send_http_error_returns_false(self):
        channel = WebhookChannel(url="https://example.com/hook")
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.HTTPError(
                       url="", code=500, msg="Server Error", hdrs={}, fp=None)):
            result = channel.send(_make_event())
        assert result is False

    def test_send_url_error_returns_false(self):
        channel = WebhookChannel(url="https://example.com/hook")
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError(reason="unreachable")):
            result = channel.send(_make_event())
        assert result is False

    def test_payload_contains_event_type(self):
        channel = WebhookChannel(url="http://example.com/hook")
        event = _make_event(event_type=EventType.ROLLBACK_TRIGGERED)
        payload = json.loads(channel._build_payload(event))
        assert payload["event_type"] == "rollback_triggered"
        assert payload["container_name"] == "api"

    def test_secret_header_included(self):
        channel = WebhookChannel(
            url="http://example.com/hook",
            secret_header="X-Secret",
            secret_value="tok123",
        )
        assert channel._extra_headers["X-Secret"] == "tok123"
