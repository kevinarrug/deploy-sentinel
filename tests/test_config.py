"""Tests for deploy_sentinel.config."""

import pytest

from deploy_sentinel.config import SentinelConfig, _parse_list


# ---------------------------------------------------------------------------
# _parse_list helper
# ---------------------------------------------------------------------------

class TestParseList:
    def test_single_item(self):
        assert _parse_list("foo=bar") == ["foo=bar"]

    def test_multiple_items(self):
        assert _parse_list("a=1, b=2, c=3") == ["a=1", "b=2", "c=3"]

    def test_empty_string_returns_empty(self):
        assert _parse_list("") == []

    def test_strips_whitespace(self):
        assert _parse_list("  x=1  ,  y=2  ") == ["x=1", "y=2"]


# ---------------------------------------------------------------------------
# SentinelConfig defaults
# ---------------------------------------------------------------------------

class TestSentinelConfigDefaults:
    def test_default_interval(self):
        cfg = SentinelConfig()
        assert cfg.health_check_interval == 30

    def test_rollback_enabled_by_default(self):
        cfg = SentinelConfig()
        assert cfg.rollback_enabled is True

    def test_default_watched_labels(self):
        cfg = SentinelConfig()
        assert cfg.watched_labels == ["deploy-sentinel.watch=true"]


# ---------------------------------------------------------------------------
# SentinelConfig.from_env
# ---------------------------------------------------------------------------

class TestFromEnv:
    def test_reads_interval_from_env(self, monkeypatch):
        monkeypatch.setenv("SENTINEL_HEALTH_INTERVAL", "60")
        cfg = SentinelConfig.from_env()
        assert cfg.health_check_interval == 60

    def test_rollback_disabled_via_env(self, monkeypatch):
        monkeypatch.setenv("SENTINEL_ROLLBACK_ENABLED", "false")
        cfg = SentinelConfig.from_env()
        assert cfg.rollback_enabled is False

    def test_webhook_url_from_env(self, monkeypatch):
        monkeypatch.setenv("SENTINEL_WEBHOOK_URL", "https://example.com/hook")
        cfg = SentinelConfig.from_env()
        assert cfg.webhook_url == "https://example.com/hook"

    def test_watched_labels_from_env(self, monkeypatch):
        monkeypatch.setenv("SENTINEL_WATCHED_LABELS", "app=web, app=worker")
        cfg = SentinelConfig.from_env()
        assert cfg.watched_labels == ["app=web", "app=worker"]

    def test_missing_webhook_url_is_none(self, monkeypatch):
        monkeypatch.delenv("SENTINEL_WEBHOOK_URL", raising=False)
        cfg = SentinelConfig.from_env()
        assert cfg.webhook_url is None


# ---------------------------------------------------------------------------
# SentinelConfig.validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_valid_config_returns_no_errors(self):
        cfg = SentinelConfig()
        assert cfg.validate() == []

    def test_interval_too_small(self):
        cfg = SentinelConfig(health_check_interval=0)
        errors = cfg.validate()
        assert any("interval" in e.lower() for e in errors)

    def test_interval_negative(self):
        cfg = SentinelConfig(health_check_interval=-5)
        errors = cfg.validate()
        assert any("interval" in e.lower() for e in errors)

    def test_empty_watched_labels_returns_error(self):
        cfg = SentinelConfig(watched_labels=[])
        errors = cfg.validate()
        assert any("label" in e.lower() for e in errors)

    def test_invalid_webhook_url_returns_error(self):
        cfg = SentinelConfig(webhook_url="not-a-valid-url")
        errors = cfg.validate()
        assert any("webhook" in e.lower() for e in errors)
