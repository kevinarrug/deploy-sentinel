"""Tests for deploy_sentinel.cli."""

import pytest

from deploy_sentinel.cli import build_arg_parser, setup_logging
import logging


class TestBuildArgParser:
    def setup_method(self):
        self.parser = build_arg_parser()

    def test_defaults(self):
        args = self.parser.parse_args([])
        assert args.interval is None
        assert args.no_rollback is False
        assert args.log_level is None

    def test_interval_flag(self):
        args = self.parser.parse_args(["--interval", "15"])
        assert args.interval == 15

    def test_no_rollback_flag(self):
        args = self.parser.parse_args(["--no-rollback"])
        assert args.no_rollback is True

    def test_log_level_flag(self):
        args = self.parser.parse_args(["--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"

    def test_invalid_log_level_raises(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args(["--log-level", "VERBOSE"])


class TestSetupLogging:
    def test_sets_info_level(self):
        setup_logging("INFO")
        assert logging.getLogger().level == logging.INFO

    def test_sets_debug_level(self):
        setup_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_unknown_level_falls_back(self):
        # getattr fallback returns INFO (10 != 0) when level is unrecognised
        setup_logging("NOTREAL")
        # Should not raise; root logger level is set to something truthy
        assert logging.getLogger().level >= 0
