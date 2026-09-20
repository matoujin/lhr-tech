"""SQLite + latest JSON snapshot store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class SnapshotStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "telemetry.sqlite"
        self.latest_path = self.data_dir / "latest.json"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fetched_at TEXT NOT NULL,
                    vehicle_id TEXT,
                    vin TEXT,
                    state TEXT,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def set_meta(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            conn.commit()

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def save_poll(self, vehicles: list[dict[str, Any]], fetched_at: str | None = None) -> dict[str, Any]:
        fetched_at = fetched_at or utcnow()
        envelope = {
            "fetched_at": fetched_at,
            "vehicle_count": len(vehicles),
            "vehicles": vehicles,
        }
        self.latest_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        with self._connect() as conn:
            for vehicle in vehicles:
                vehicle_id = str(vehicle.get("id") or vehicle.get("id_s") or "")
                conn.execute(
                    "INSERT INTO snapshots(fetched_at, vehicle_id, vin, state, payload) "
                    "VALUES(?, ?, ?, ?, ?)",
                    (
                        fetched_at,
                        vehicle_id,
                        vehicle.get("vin"),
                        vehicle.get("state"),
                        json.dumps(vehicle, ensure_ascii=False),
                    ),
                )
            conn.commit()
        self.set_meta("last_ok_at", fetched_at)
        self.set_meta("last_error", "")
        return envelope

    def latest(self) -> dict[str, Any] | None:
        if self.latest_path.exists():
            return json.loads(self.latest_path.read_text(encoding="utf-8"))
        return None

    def latest_vehicle(self, vehicle_id: str) -> dict[str, Any] | None:
        latest = self.latest()
        if not latest:
            return None
        for vehicle in latest.get("vehicles") or []:
            if str(vehicle.get("id")) == vehicle_id or str(vehicle.get("id_s")) == vehicle_id:
                return vehicle
        return None

    def recent_snapshots(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, fetched_at, vehicle_id, vin, state, payload "
                "FROM snapshots ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            out.append(item)
        return out
