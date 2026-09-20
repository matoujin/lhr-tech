"""Read-only HTTP surface over the latest snapshots."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from tesla_readonly.store import SnapshotStore


def _pick(vehicle: dict[str, Any], key: str) -> dict[str, Any]:
    return {"vehicle_id": vehicle.get("id_s") or vehicle.get("id"), key: vehicle.get(key)}


class Handler(BaseHTTPRequestHandler):
    store: SnapshotStore

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _json(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path == "/health":
            latest = self.store.latest()
            self._json(
                200,
                {
                    "ok": True,
                    "status": self.store.get_meta("status", "starting"),
                    "last_ok_at": self.store.get_meta("last_ok_at"),
                    "last_error": self.store.get_meta("last_error") or None,
                    "has_snapshot": latest is not None,
                    "read_only": True,
                },
            )
            return

        if path == "/latest" or path == "/vehicles":
            latest = self.store.latest()
            if latest is None:
                self._json(404, {"error": "no snapshot yet"})
                return
            self._json(200, latest)
            return

        if path == "/snapshots":
            limit = int((query.get("limit") or ["20"])[0])
            self._json(200, {"snapshots": self.store.recent_snapshots(limit=min(limit, 200))})
            return

        parts = path.split("/")
        # /vehicles/{id} or /vehicles/{id}/{section}
        if len(parts) >= 3 and parts[1] == "vehicles":
            vehicle = self.store.latest_vehicle(parts[2])
            if vehicle is None:
                self._json(404, {"error": "vehicle not in latest snapshot", "id": parts[2]})
                return
            if len(parts) == 3:
                self._json(200, vehicle)
                return
            section = parts[3]
            mapping = {
                "charge": "charge_state",
                "drive": "drive_state",
                "climate": "climate_state",
                "vehicle": "vehicle_state",
                "battery": "charge_state",
                "location": "drive_state",
            }
            if section in mapping:
                self._json(200, _pick(vehicle, mapping[section]))
                return

        self._json(
            404,
            {
                "error": "unknown path",
                "endpoints": [
                    "GET /health",
                    "GET /latest",
                    "GET /vehicles",
                    "GET /vehicles/{id}",
                    "GET /vehicles/{id}/charge",
                    "GET /vehicles/{id}/drive",
                    "GET /vehicles/{id}/climate",
                    "GET /vehicles/{id}/vehicle",
                    "GET /vehicles/{id}/battery",
                    "GET /vehicles/{id}/location",
                    "GET /snapshots?limit=20",
                ],
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        self._json(405, {"error": "read-only server; POST is disabled"})

    def do_PUT(self) -> None:  # noqa: N802
        self._json(405, {"error": "read-only server; PUT is disabled"})

    def do_DELETE(self) -> None:  # noqa: N802
        self._json(405, {"error": "read-only server; DELETE is disabled"})


def make_server(store: SnapshotStore, host: str, port: int) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"store": store})
    return ThreadingHTTPServer((host, port), handler)
