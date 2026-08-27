# src/calendarr/health.py
"""Stdlib health endpoint keeping the /health contract on port 5000."""

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger("health")

PORT = 5000


@dataclass
class Status:
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    scheduler_running: bool = False
    last_run_at: str = ""
    last_run_outcome: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_run(self, outcome: str) -> None:
        with self._lock:
            self.last_run_at = datetime.now(UTC).isoformat()
            self.last_run_outcome = outcome

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "status": "healthy" if self.scheduler_running else "starting",
                "scheduler": "active" if self.scheduler_running else "stopped",
                "started_at": self.started_at,
                "last_run_at": self.last_run_at or None,
                "last_run_outcome": self.last_run_outcome or None,
                "timestamp": datetime.now(UTC).isoformat(),
            }


class _Handler(BaseHTTPRequestHandler):
    status: Status

    def do_GET(self):  # noqa: N802
        if self.path in ("/", "/health"):
            body = json.dumps(self.status.to_dict()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


def start_health_server(status: Status, port: int = PORT) -> ThreadingHTTPServer:
    handler = type("Handler", (_Handler,), {"status": status})
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="health")
    thread.start()
    logger.info("Health endpoint listening on port %s", port)
    return server
