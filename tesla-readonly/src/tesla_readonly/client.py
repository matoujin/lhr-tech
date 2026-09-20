"""Tesla Owner API client: token refresh + GET telemetry only."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

DEFAULT_SSO_BASE = "https://auth.tesla.com/"
DEFAULT_OWNER_API_BASE = "https://owner-api.teslamotors.com/"
SSO_CLIENT_ID = "ownerapi"
SSO_SCOPE = "openid email offline_access"
READ_ENDPOINTS = "location_data;charge_state;climate_state;vehicle_state;gui_settings;vehicle_config;drive_state"

# Owner API paths this client is allowed to touch (GET only).
ALLOWED_GET_SUFFIXES = (
    "/api/1/vehicles",
    "/api/1/products",
)
ALLOWED_GET_TEMPLATES = (
    "/api/1/vehicles/{id}/vehicle_data",
    "/api/1/vehicles/{id}",
)

# Hard deny list — never implemented, never called.
DENIED_PATH_FRAGMENTS = (
    "/command/",
    "/wake_up",
    "/honk",
    "/flash",
    "/door_lock",
    "/door_unlock",
    "/auto_conditioning",
    "/charge_start",
    "/charge_stop",
    "/set_charge",
    "/set_temps",
    "/remote_start",
    "/actuate_trunk",
    "/sun_roof",
    "/speed_limit",
    "/sentry_mode",
    "/window_control",
)


class CommandBlockedError(RuntimeError):
    """Raised if code tries to hit a vehicle command path."""


class TeslaAuthError(RuntimeError):
    """Refresh token or access token was rejected."""


def _assert_read_only_path(path: str) -> None:
    lowered = path.lower()
    for fragment in DENIED_PATH_FRAGMENTS:
        if fragment in lowered:
            raise CommandBlockedError(f"blocked vehicle command path: {path}")


def assert_allowed_get(path: str) -> None:
    """Allowlist GET vehicle/list/data paths after command deny list."""
    _assert_read_only_path(path)
    if path.rstrip("/") == "/api/1/vehicles" or path.rstrip("/") == "/api/1/products":
        return
    if path.startswith("/api/1/vehicles/") and path.endswith("/vehicle_data"):
        return
    # GET /api/1/vehicles/{id}
    rest = path[len("/api/1/vehicles/") :] if path.startswith("/api/1/vehicles/") else ""
    if rest and "/" not in rest.rstrip("/"):
        return
    raise CommandBlockedError(f"path is not on the read-only allowlist: {path}")


class TeslaOwnerClient:
    """teslapy-compatible Owner API: refresh_token grant + vehicle_data GET."""

    def __init__(
        self,
        refresh_token: str,
        *,
        sso_base: str = DEFAULT_SSO_BASE,
        owner_api_base: str = DEFAULT_OWNER_API_BASE,
        timeout: float = 30.0,
        user_agent: str = "tesla-readonly/0.1.0",
    ) -> None:
        if not refresh_token:
            raise ValueError("TESLA_REFRESH_TOKEN is empty")
        self.refresh_token = refresh_token
        self.sso_base = sso_base if sso_base.endswith("/") else sso_base + "/"
        self.owner_api_base = (
            owner_api_base if owner_api_base.endswith("/") else owner_api_base + "/"
        )
        self.access_token: str | None = None
        self.token_type = "Bearer"
        self._timeout = timeout
        self._user_agent = user_agent
        self._http = httpx.Client(
            timeout=timeout,
            http2=True,
            headers={"Accept": "application/json", "User-Agent": user_agent},
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> TeslaOwnerClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def refresh_access_token(self) -> dict[str, Any]:
        """POST auth.tesla.com oauth2/v3/token (same grant teslapy uses)."""
        url = urljoin(self.sso_base, "oauth2/v3/token")
        data = {
            "grant_type": "refresh_token",
            "client_id": SSO_CLIENT_ID,
            "refresh_token": self.refresh_token,
            "scope": SSO_SCOPE,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = self._http.post(url, data=data, headers=headers)
        if response.status_code >= 400:
            raise TeslaAuthError(
                f"token refresh failed HTTP {response.status_code}: {response.text[:300]}"
            )
        payload = response.json()
        access = payload.get("access_token")
        if not access:
            raise TeslaAuthError("token response missing access_token")
        self.access_token = access
        self.token_type = payload.get("token_type") or "Bearer"
        # Tesla may rotate refresh tokens; keep the new one in memory only.
        if payload.get("refresh_token"):
            self.refresh_token = payload["refresh_token"]
        return payload

    def _auth_headers(self) -> dict[str, str]:
        if not self.access_token:
            self.refresh_access_token()
        return {"Authorization": f"{self.token_type} {self.access_token}"}

    def get_json(self, path: str, params: dict[str, str] | None = None) -> Any:
        assert_allowed_get(path)
        url = urljoin(self.owner_api_base, path.lstrip("/"))
        response = self._http.get(url, headers=self._auth_headers(), params=params)
        if response.status_code == 401:
            self.refresh_access_token()
            response = self._http.get(url, headers=self._auth_headers(), params=params)
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Owner API GET {path} failed HTTP {response.status_code}: {response.text[:300]}",
                request=response.request,
                response=response,
            )
        if not response.content:
            return None
        return response.json()

    def list_vehicles(self) -> list[dict[str, Any]]:
        payload = self.get_json("/api/1/vehicles")
        response = payload.get("response") if isinstance(payload, dict) else payload
        if response is None:
            return []
        if isinstance(response, list):
            return response
        return [response]

    def vehicle_data(self, vehicle_id: str | int) -> dict[str, Any]:
        path = f"/api/1/vehicles/{vehicle_id}/vehicle_data"
        payload = self.get_json(path, params={"endpoints": READ_ENDPOINTS})
        if isinstance(payload, dict) and isinstance(payload.get("response"), dict):
            return payload["response"]
        if isinstance(payload, dict):
            return payload
        return {}
