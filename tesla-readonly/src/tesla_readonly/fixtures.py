"""Offline fixture telemetry so the stack can start without a real token."""

from __future__ import annotations

from typing import Any

MOCK_VEHICLES: list[dict[str, Any]] = [
    {
        "id": 1001,
        "id_s": "1001",
        "vehicle_id": 2002,
        "vin": "MOCKVIN0000000001",
        "display_name": "Mock Model Y",
        "state": "online",
        "in_service": False,
        "charge_state": {
            "battery_level": 67,
            "battery_range": 210.4,
            "charging_state": "Stopped",
            "charge_limit_soc": 80,
            "charger_power": 0,
        },
        "drive_state": {
            "latitude": 37.3947,
            "longitude": -122.1503,
            "heading": 90,
            "speed": 0,
            "shift_state": "P",
            "power": 0,
        },
        "climate_state": {
            "inside_temp": 22.5,
            "outside_temp": 18.0,
            "is_climate_on": False,
            "driver_temp_setting": 21.0,
        },
        "vehicle_state": {
            "odometer": 12345.6,
            "locked": True,
            "car_version": "2025.32.6",
            "sentry_mode": False,
        },
        "vehicle_config": {"car_type": "modely", "exterior_color": "PearlWhite"},
        "gui_settings": {"gui_distance_units": "km/hr", "gui_temperature_units": "C"},
    }
]
