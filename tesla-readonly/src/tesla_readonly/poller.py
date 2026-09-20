"""Background poll loop: list vehicles + vehicle_data. Never sends commands."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from tesla_readonly.client import TeslaAuthError, TeslaOwnerClient
from tesla_readonly.fixtures import MOCK_VEHICLES
from tesla_readonly.store import SnapshotStore, utcnow

logger = logging.getLogger(__name__)


def summarize_vehicle(summary: dict[str, Any], data: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(summary)
    if data:
        for key in (
            "charge_state",
            "drive_state",
            "climate_state",
            "vehicle_state",
            "vehicle_config",
            "gui_settings",
        ):
            if key in data:
                merged[key] = data[key]
        merged["state"] = data.get("state") or summary.get("state")
        merged["vin"] = data.get("vin") or summary.get("vin")
        merged["display_name"] = data.get("display_name") or summary.get("display_name")
    return merged


def collect_once(client: TeslaOwnerClient) -> list[dict[str, Any]]:
    vehicles = []
    for summary in client.list_vehicles():
        vehicle_id = summary.get("id_s") or summary.get("id")
        state = (summary.get("state") or "").lower()
        data = None
        if vehicle_id and state == "online":
            try:
                data = client.vehicle_data(vehicle_id)
            except httpx.HTTPStatusError as exc:
                logger.warning("vehicle_data skipped for %s: %s", vehicle_id, exc)
                summary = dict(summary)
                summary["telemetry_error"] = str(exc)[:300]
        elif vehicle_id:
            summary = dict(summary)
            summary["telemetry_skipped"] = f"vehicle is {state or 'unknown'}; not waking"
        vehicles.append(summarize_vehicle(summary, data))
    return vehicles


def poll_forever(
    store: SnapshotStore,
    *,
    refresh_token: str | None,
    mock: bool,
    interval_seconds: float,
    sso_base: str,
    owner_api_base: str,
    stop_after: int | None = None,
) -> None:
    cycles = 0
    client: TeslaOwnerClient | None = None
    if not mock:
        cached = store.get_meta("rotated_refresh_token")
        effective = cached or refresh_token
        if not effective:
            store.set_meta("status", "unconfigured")
            store.set_meta(
                "last_error",
                "TESLA_REFRESH_TOKEN is empty; set it in .env or enable TESLA_MOCK=1",
            )
            logger.warning("no refresh token; HTTP API stays up, polling is idle")
            return
        client = TeslaOwnerClient(
            effective,
            sso_base=sso_base,
            owner_api_base=owner_api_base,
        )

    try:
        while True:
            try:
                if mock:
                    vehicles = MOCK_VEHICLES
                    store.set_meta("status", "mock")
                else:
                    assert client is not None
                    vehicles = collect_once(client)
                    store.set_meta("status", "ok")
                    if client.refresh_token and client.refresh_token != (refresh_token or ""):
                        store.set_meta("rotated_refresh_token", client.refresh_token)
                store.save_poll(vehicles)
                logger.info("saved %s vehicle snapshot(s) at %s", len(vehicles), utcnow())
            except TeslaAuthError as exc:
                store.set_meta("status", "auth_error")
                store.set_meta("last_error", str(exc))
                logger.error("auth error: %s", exc)
            except Exception as exc:  # noqa: BLE001 — poller must keep running
                store.set_meta("status", "error")
                store.set_meta("last_error", str(exc))
                logger.exception("poll failed")
            cycles += 1
            if stop_after is not None and cycles >= stop_after:
                return
            time.sleep(interval_seconds)
    finally:
        if client is not None:
            client.close()
