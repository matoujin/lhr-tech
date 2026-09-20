from tesla_readonly.client import CommandBlockedError, TeslaOwnerClient, assert_allowed_get


def test_allowlist_accepts_vehicle_reads() -> None:
    assert_allowed_get("/api/1/vehicles")
    assert_allowed_get("/api/1/vehicles/123")
    assert_allowed_get("/api/1/vehicles/123/vehicle_data")


def test_denies_command_paths() -> None:
    blocked = [
        "/api/1/vehicles/1/command/door_lock",
        "/api/1/vehicles/1/command/honk_horn",
        "/api/1/vehicles/1/command/flash_lights",
        "/api/1/vehicles/1/command/auto_conditioning_start",
        "/api/1/vehicles/1/command/charge_start",
        "/api/1/vehicles/1/command/charge_stop",
        "/api/1/vehicles/1/wake_up",
    ]
    for path in blocked:
        try:
            assert_allowed_get(path)
        except CommandBlockedError:
            continue
        raise AssertionError(f"expected block for {path}")


def test_client_get_json_refuses_commands(monkeypatch) -> None:
    client = TeslaOwnerClient("dummy-refresh")
    called = {"n": 0}

    def boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("HTTP must not run for command paths")

    monkeypatch.setattr(client._http, "get", boom)
    monkeypatch.setattr(client._http, "post", boom)
    try:
        client.get_json("/api/1/vehicles/1/command/door_lock")
        raise AssertionError("expected CommandBlockedError")
    except CommandBlockedError:
        pass
    assert called["n"] == 0
    client.close()
