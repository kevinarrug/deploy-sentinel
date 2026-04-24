"""Command-line entry point for deploy-sentinel."""

from __future__ import annotations

import argparse
import logging
import sys
import time

import docker

from deploy_sentinel.config import SentinelConfig
from deploy_sentinel.health_check import HealthChecker
from deploy_sentinel.metrics import MetricsCollector
from deploy_sentinel.monitor import DeployMonitor
from deploy_sentinel.notifier import LoggingChannel
from deploy_sentinel.rollback import RollbackManager
from deploy_sentinel.webhook import WebhookChannel


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deploy-sentinel",
        description="Lightweight deployment monitoring and rollback automation.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Override health-check interval (seconds).",
    )
    parser.add_argument(
        "--no-rollback",
        action="store_true",
        default=False,
        help="Disable automatic rollback.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override log level.",
    )
    return parser


def setup_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=getattr(logging, level, logging.INFO),
    )


def run(argv: list[str] | None = None) -> int:  # pragma: no cover
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    cfg = SentinelConfig.from_env()

    # Apply CLI overrides
    if args.interval is not None:
        cfg.health_check_interval = args.interval
    if args.no_rollback:
        cfg.rollback_enabled = False
    if args.log_level:
        cfg.log_level = args.log_level

    errors = cfg.validate()
    if errors:
        for err in errors:
            print(f"[config error] {err}", file=sys.stderr)
        return 1

    setup_logging(cfg.log_level)
    logger = logging.getLogger("deploy_sentinel.cli")
    logger.info("Starting deploy-sentinel (interval=%ds)", cfg.health_check_interval)

    client = docker.from_env()
    channels = [LoggingChannel()]
    if cfg.webhook_url:
        channels.append(WebhookChannel(cfg.webhook_url))

    monitor = DeployMonitor(
        client=client,
        health_checker=HealthChecker(client),
        rollback_manager=RollbackManager(client),
        metrics_collector=MetricsCollector(),
        channels=channels,
        rollback_enabled=cfg.rollback_enabled,
        unhealthy_threshold=cfg.unhealthy_threshold,
    )

    try:
        while True:
            monitor.check_and_act()
            time.sleep(cfg.health_check_interval)
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    return 0


def main() -> None:  # pragma: no cover
    sys.exit(run())


if __name__ == "__main__":  # pragma: no cover
    main()
