"""Call the sruqy-daily-updates MCP over streamable HTTP JSON-RPC."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any

DEFAULT_ENDPOINT = "http://116.198.229.83:9986/mcp"


class McpError(RuntimeError):
    pass


def _rpc(endpoint: str, method: str, params: dict[str, Any] | None = None, req_id: int = 1) -> Any:
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params or {},
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise McpError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise McpError(f"连接失败: {exc.reason}") from exc

    if "error" in body:
        raise McpError(json.dumps(body["error"], ensure_ascii=False))
    return body.get("result")


def get_daily_updates(
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    date: str | None = None,
    limit: int | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    _rpc(
        endpoint,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "sruqy-mcp-client", "version": "0.1.0"},
        },
        req_id=1,
    )

    arguments: dict[str, Any] = {}
    if date:
        arguments["date"] = date
    if limit is not None:
        arguments["limit"] = limit
    if source:
        arguments["source"] = source

    result = _rpc(
        endpoint,
        "tools/call",
        {"name": "get_daily_updates", "arguments": arguments},
        req_id=2,
    )

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured

    content = result.get("content") or []
    for item in content:
        if item.get("type") == "text":
            return json.loads(item["text"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="获取思如泉涌每日市场信号（MCP）")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="MCP 端点 URL")
    parser.add_argument("--date", help="日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--limit", type=int, help="返回条数，默认 30，最大 100")
    parser.add_argument("--source", help="按来源名称过滤")
    args = parser.parse_args()

    data = get_daily_updates(
        endpoint=args.endpoint,
        date=args.date,
        limit=args.limit,
        source=args.source,
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
