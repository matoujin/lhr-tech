"""Process entry: HTTP read API + optional poller thread."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from tesla_readonly.client import DEFAULT_OWNER_API_BASE, DEFAULT_SSO_BASE
from tesla_readonly.poller import poll_forever
from tesla_readonly.server import make_server
from tesla_readonly.store import SnapshotStore


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    data_dir = Path(os.environ.get("DATA_DIR", "./data"))
    host = os.environ.get("HTTP_HOST", "0.0.0.0")
    port = int(os.environ.get("HTTP_PORT", "8080"))
    interval = float(os.environ.get("TESLA_POLL_SECONDS", "120"))
    mock = _bool_env("TESLA_MOCK", default=False)
    refresh_token = os.environ.get("TESLA_REFRESH_TOKEN", "").strip()
    sso_base = os.environ.get("TESLA_SSO_BASE_URL", DEFAULT_SSO_BASE)
    owner_api = os.environ.get("TESLA_OWNER_API_BASE", DEFAULT_OWNER_API_BASE)

    store = SnapshotStore(data_dir)
    store.set_meta("status", "starting")

    poller = threading.Thread(
        target=poll_forever,
        kwargs={
            "store": store,
            "refresh_token": refresh_token or None,
            "mock": mock,
            "interval_seconds": interval,
            "sso_base": sso_base,
            "owner_api_base": owner_api,
        },
        name="tesla-poller",
        daemon=True,
    )
    poller.start()

    httpd = make_server(store, host, port)
    logging.getLogger(__name__).info(
        "read-only HTTP on %s:%s (mock=%s, token_set=%s)",
        host,
        port,
        mock,
        bool(refresh_token),
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
