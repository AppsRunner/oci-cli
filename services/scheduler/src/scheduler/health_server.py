import json
import logging
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    get_status: Callable[[], Dict]  # injected by HealthServer

    def do_GET(self) -> None:
        if self.path not in ("/health", "/healthz", "/ready"):
            self.send_response(404)
            self.end_headers()
            return

        try:
            status = self.__class__.get_status()
            body = json.dumps(status).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            error_body = json.dumps({"status": "error", "error": str(exc)}).encode()
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error_body)

    def log_message(self, fmt: str, *args) -> None:  # suppress access logs
        pass


class HealthServer:
    def __init__(self, port: int, get_status: Callable[[], Dict]) -> None:
        self._port = port
        handler = type("Handler", (_HealthHandler,), {"get_status": staticmethod(get_status)})
        self._server = HTTPServer(("0.0.0.0", port), handler)
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Health server listening on port %d", self._port)

    def stop(self) -> None:
        self._server.shutdown()
        logger.info("Health server stopped")

    def build_status(
        self,
        scheduler_running: bool,
        worker_status: Dict,
        queue_lengths: Dict,
    ) -> Dict:
        return {
            "status": "healthy" if scheduler_running else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scheduler": {"running": scheduler_running},
            "workers": worker_status,
            "queues": queue_lengths,
        }
