import json
from http.client import HTTPConnection

from tesla_readonly.fixtures import MOCK_VEHICLES
from tesla_readonly.poller import poll_forever
from tesla_readonly.server import make_server
from tesla_readonly.store import SnapshotStore


def test_store_roundtrip(tmp_path) -> None:
    store = SnapshotStore(tmp_path)
    store.save_poll(MOCK_VEHICLES)
    latest = store.latest()
    assert latest is not None
    assert latest["vehicle_count"] == 1
    vehicle = store.latest_vehicle("1001")
    assert vehicle is not None
    assert vehicle["charge_state"]["battery_level"] == 67
    assert store.recent_snapshots(limit=1)[0]["vin"] == "MOCKVIN0000000001"


def test_http_read_only_endpoints(tmp_path) -> None:
    store = SnapshotStore(tmp_path)
    store.save_poll(MOCK_VEHICLES)
    store.set_meta("status", "mock")
    httpd = make_server(store, "127.0.0.1", 0)
    host, port = httpd.server_address[:2]
    from threading import Thread

    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health")
        health = json.loads(conn.getresponse().read())
        assert health["ok"] is True
        assert health["read_only"] is True

        conn.request("GET", "/vehicles/1001/charge")
        charge = json.loads(conn.getresponse().read())
        assert charge["charge_state"]["battery_level"] == 67

        conn.request("GET", "/vehicles/1001/location")
        loc = json.loads(conn.getresponse().read())
        assert loc["drive_state"]["latitude"] == 37.3947

        conn.request("POST", "/vehicles/1001/charge", body="{}", headers={"Content-Type": "application/json"})
        denied = conn.getresponse()
        assert denied.status == 405
    finally:
        httpd.shutdown()


def test_mock_poll_writes_snapshot(tmp_path) -> None:
    store = SnapshotStore(tmp_path)
    poll_forever(
        store,
        refresh_token=None,
        mock=True,
        interval_seconds=0,
        sso_base="https://auth.tesla.com/",
        owner_api_base="https://owner-api.teslamotors.com/",
        stop_after=1,
    )
    assert store.get_meta("status") == "mock"
    assert store.latest()["vehicles"][0]["vin"] == "MOCKVIN0000000001"
