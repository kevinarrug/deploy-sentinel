"""Simple HTTP status endpoint that serves the latest StatusReport as JSON."""
from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from deploy_sentinel.status_reporter import StatusReport

log = logging.getLogger(__name__)

_current_report: Optional[StatusReport] = None
_report_lock = threading.Lock()


def update_report(report: StatusReport) -> None:
    """Thread-safe update of the shared report."""
    global _current_report
    with _report_lock:
        _current_report = report


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/status", "/"):
            self.send_response(404)
            self.end_headers()
            return

        with _report_lock:
            report = _current_report

        if report is None:
            body = json.dumps({"status": "no data yet"}).encode()
        else:
            body = json.dumps(report.to_dict()).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        log.debug("status endpoint: " + fmt, *args)


class StatusEndpoint:
    """Runs a lightweight HTTP server in a daemon thread."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._server = HTTPServer((self.host, self.port), _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True, name="status-endpoint"
        )
        self._thread.start()
        log.info("Status endpoint listening on %s:%d", self.host, self.port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            log.info("Status endpoint stopped.")
