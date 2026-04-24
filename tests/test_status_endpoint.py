"""Tests for the StatusEndpoint HTTP server."""
from __future__ import annotations

import json
import time
import urllib.request

import pytest

from deploy_sentinel.status_endpoint import StatusEndpoint, update_report
from deploy_sentinel.status_reporter import StatusReport


TEST_PORT = 18765


@pytest.fixture(autouse=True)
def _reset_report():
    """Ensure shared state is cleared between tests."""
    import deploy_sentinel.status_endpoint as mod
    mod._current_report = None
    yield
    mod._current_report = None


@pytest.fixture()
def endpoint():
    ep = StatusEndpoint(host="127.0.0.1", port=TEST_PORT)
    ep.start()
    time.sleep(0.05)  # allow thread to start
    yield ep
    ep.stop()


def _get(path: str = "/status") -> tuple[int, dict]:
    url = f"http://127.0.0.1:{TEST_PORT}{path}"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, {}


class TestStatusEndpoint:
    def test_returns_no_data_when_report_is_none(self, endpoint):
        status, body = _get("/status")
        assert status == 200
        assert body["status"] == "no data yet"

    def test_returns_report_after_update(self, endpoint):
        report = StatusReport(entries=[])
        update_report(report)
        status, body = _get("/status")
        assert status == 200
        assert "total" in body
        assert body["total"] == 0

    def test_root_path_also_works(self, endpoint):
        status, body = _get("/")
        assert status == 200

    def test_unknown_path_returns_404(self, endpoint):
        status, _ = _get("/unknown")
        assert status == 404

    def test_update_report_is_thread_safe(self, endpoint):
        import threading
        reports = [StatusReport(entries=[]) for _ in range(20)]
        threads = [threading.Thread(target=update_report, args=(r,)) for r in reports]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        status, body = _get("/status")
        assert status == 200
