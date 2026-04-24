"""Tests for deploy_sentinel.notifier."""

from __future__ import annotations

import logging
import pytest

from deploy_sentinel.notifier import (
    DeployEvent,
    EventType,
    LoggingChannel,
    Notifier,
)


def _make_event(**kwargs) -> DeployEvent:
    defaults = dict(
        event_type=EventType.DEPLOY_SUCCESS,
        container_id="abc123",
        container_name="web",
        image="nginx:1.25",
        message="Deployment succeeded",
    )
    defaults.update(kwargs)
    return DeployEvent(**defaults)


class TestLoggingChannel:
    def test_send_returns_true(self):
        channel = LoggingChannel()
        assert channel.send(_make_event()) is True

    def test_send_logs_message(self, caplog):
        channel = LoggingChannel(level=logging.INFO)
        with caplog.at_level(logging.INFO):
            channel.send(_make_event(message="hello"))
        assert "hello" in caplog.text

    def test_send_logs_event_type(self, caplog):
        channel = LoggingChannel()
        with caplog.at_level(logging.INFO):
            channel.send(_make_event(event_type=EventType.ROLLBACK_TRIGGERED))
        assert "rollback_triggered" in caplog.text


class TestNotifier:
    def test_default_channel_is_logging(self):
        notifier = Notifier()
        assert len(notifier._channels) == 1
        assert isinstance(notifier._channels[0], LoggingChannel)

    def test_add_channel(self):
        notifier = Notifier(channels=[])
        ch = LoggingChannel()
        notifier.add_channel(ch)
        assert ch in notifier._channels

    def test_notify_returns_results(self):
        notifier = Notifier(channels=[LoggingChannel()])
        results = notifier.notify(_make_event())
        assert results == [True]

    def test_notify_handles_channel_exception(self):
        class BrokenChannel:
            def send(self, event):
                raise RuntimeError("boom")

        notifier = Notifier(channels=[BrokenChannel()])
        results = notifier.notify(_make_event())
        assert results == [False]

    def test_notify_rollback_success(self, caplog):
        notifier = Notifier(channels=[LoggingChannel()])
        with caplog.at_level(logging.INFO):
            notifier.notify_rollback(
                container_name="web",
                container_id="abc",
                image="nginx:1.25",
                previous_image="nginx:1.24",
                success=True,
            )
        assert "nginx:1.24" in caplog.text
        assert "rollback_success" in caplog.text

    def test_notify_rollback_failure(self, caplog):
        notifier = Notifier(channels=[LoggingChannel()])
        with caplog.at_level(logging.INFO):
            notifier.notify_rollback(
                container_name="web",
                container_id="abc",
                image="nginx:1.25",
                previous_image="nginx:1.24",
                success=False,
            )
        assert "rollback_failure" in caplog.text
