import httpx

from tesla_readonly.client import TeslaAuthError, TeslaOwnerClient


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or ("" if payload is None else str(payload))

    def json(self):
        return self._payload


def test_refresh_sends_teslapy_ownerapi_form(monkeypatch) -> None:
    client = TeslaOwnerClient("exported-from-auth-for-tesla")
    captured = {}

    def fake_post(url, data=None, headers=None):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        return _FakeResponse(
            200,
            {
                "access_token": "access-abc",
                "token_type": "Bearer",
                "expires_in": 28800,
                "refresh_token": "rotated",
            },
        )

    monkeypatch.setattr(client._http, "post", fake_post)
    token = client.refresh_access_token()
    assert token["access_token"] == "access-abc"
    assert captured["url"] == "https://auth.tesla.com/oauth2/v3/token"
    assert captured["data"]["grant_type"] == "refresh_token"
    assert captured["data"]["client_id"] == "ownerapi"
    assert captured["data"]["refresh_token"] == "exported-from-auth-for-tesla"
    assert "openid" in captured["data"]["scope"]
    assert captured["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert client.refresh_token == "rotated"
    client.close()


def test_refresh_maps_public_401_shape(monkeypatch) -> None:
    client = TeslaOwnerClient("invalid-probe")

    def fake_post(url, data=None, headers=None):
        return _FakeResponse(
            401,
            {"error": "login_required", "error_description": "The refresh_token is invalid"},
            text='{"error":"login_required","error_description":"The refresh_token is invalid"}',
        )

    monkeypatch.setattr(client._http, "post", fake_post)
    try:
        client.refresh_access_token()
        raise AssertionError("expected TeslaAuthError")
    except TeslaAuthError as exc:
        assert "401" in str(exc)
        assert "login_required" in str(exc) or "invalid" in str(exc)
    client.close()


def test_list_vehicles_get_only(monkeypatch) -> None:
    client = TeslaOwnerClient("tok")
    client.access_token = "access-abc"

    def fake_get(url, headers=None, params=None):
        assert url.endswith("/api/1/vehicles")
        assert headers["Authorization"] == "Bearer access-abc"
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={"response": [{"id": 1, "id_s": "1", "state": "asleep", "vin": "VIN1"}]},
            request=request,
        )

    monkeypatch.setattr(client._http, "get", fake_get)
    vehicles = client.list_vehicles()
    assert vehicles[0]["state"] == "asleep"
    client.close()
