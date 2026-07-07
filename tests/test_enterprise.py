"""Enterprise-layer tests: config, metrics, hardened HTTP conversation service."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from almandoub.config import load_config
from almandoub.observability import Metrics, teardown_logging
from almandoub.service import Handler, create_server
from almandoub.version import __version__


class ConfigTests(unittest.TestCase):
    KEYS = ("ALMANDOUB_HOME", "ALMANDOUB_API_KEY", "ALMANDOUB_PORT")

    def setUp(self) -> None:
        self._saved = {k: os.environ.get(k) for k in self.KEYS}

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_defaults(self) -> None:
        for key in self.KEYS:
            os.environ.pop(key, None)
        cfg = load_config()
        self.assertEqual(cfg.port, 8798)
        self.assertFalse(cfg.auth_required)

    def test_env_overrides(self) -> None:
        os.environ["ALMANDOUB_API_KEY"] = "k"
        os.environ["ALMANDOUB_PORT"] = "9966"
        cfg = load_config()
        self.assertTrue(cfg.auth_required)
        self.assertEqual(cfg.port, 9966)


class MetricsTests(unittest.TestCase):
    def test_percentiles_ordered(self) -> None:
        metrics = Metrics("almandoub", __version__)
        for value in range(1, 41):
            metrics.observe_ms(float(value))
        snap = metrics.snapshot()
        self.assertLessEqual(snap["latency_ms"]["p50"], snap["latency_ms"]["p95"])
        self.assertLessEqual(snap["latency_ms"]["p95"], snap["latency_ms"]["p99"])


class ServiceTestBase(unittest.TestCase):
    api_key = ""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        os.environ["ALMANDOUB_API_KEY"] = self.api_key
        os.environ["ALMANDOUB_LOG_DIR"] = str(Path(self._tmp.name) / "logs")
        self.server = create_server(host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        for key in ("ALMANDOUB_API_KEY", "ALMANDOUB_LOG_DIR"):
            os.environ.pop(key, None)
        if Handler.logger is not None:
            teardown_logging(Handler.logger)
            Handler.logger = None
        self._tmp.cleanup()

    def request_raw(self, path: str, payload: dict | None = None, headers: dict | None = None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, headers=headers or {})
        if data is not None:
            request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read().decode("utf-8")

    def request(self, path: str, payload: dict | None = None, headers: dict | None = None):
        status, raw = self.request_raw(path, payload, headers)
        return status, json.loads(raw)


class OpenServiceTests(ServiceTestBase):
    api_key = ""

    def test_health(self) -> None:
        status, body = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["service"], "almandoub")

    def test_handle_order_message(self) -> None:
        status, body = self.request("/api/handle", {"message": "I want to place an order for two units"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertIn(body["action"], {"REPLY", "ESCALATE", "CREATE_OR_UPDATE_ORDER"})
        self.assertTrue(body["response"])

    def test_handle_sanitizes_contact_details(self) -> None:
        status, raw = self.request_raw("/api/handle", {"message": "call me on 0551234567 email me at buyer@example.com about order 8842"})
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertNotIn("buyer@example.com", body["safe_message"])
        self.assertNotIn("0551234567", body["safe_message"])

    def test_handle_missing_message(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request("/api/handle", {})
        self.assertEqual(ctx.exception.code, 400)

    def test_metrics_after_handle(self) -> None:
        self.request("/api/handle", {"message": "where is my order"})
        status, metrics = self.request("/api/metrics")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(metrics["counters"].get("http_requests_total", 0), 1)


class AuthServiceTests(ServiceTestBase):
    api_key = "mandoub-secret"

    def test_rejects_missing_key(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request("/api/metrics")
        self.assertEqual(ctx.exception.code, 401)

    def test_accepts_valid_key(self) -> None:
        status, body = self.request("/api/metrics", headers={"X-API-Key": "mandoub-secret"})
        self.assertEqual(status, 200)
        self.assertEqual(body["service"], "almandoub")

    def test_health_open_for_probes(self) -> None:
        status, body = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["auth_required"])

    def test_oversized_body_rejected(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request("/api/handle", {"message": "x" * 1_200_000}, headers={"X-API-Key": "mandoub-secret"})
        self.assertEqual(ctx.exception.code, 413)


if __name__ == "__main__":
    unittest.main()
