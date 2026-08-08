"""MCP transport tests: one thin adapter, stdio and streamable HTTP."""
from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from target_agent.mcp_server import _serve, create_mcp_server


class StubServer:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run(self, **kwargs) -> None:
        self.calls.append(kwargs)


def test_serve_uses_stdio_transport():
    server = StubServer()
    _serve(server, transport="stdio", host="127.0.0.1", port=8000, path="/mcp")
    assert server.calls == [{"transport": "stdio"}]


def test_serve_uses_streamable_http_transport():
    server = StubServer()
    _serve(server, transport="streamable-http", host="0.0.0.0", port=9000, path="/mcp")
    assert server.calls == [{
        "transport": "streamable-http",
        "host": "0.0.0.0",
        "port": 9000,
        "streamable_http_path": "/mcp",
    }]


def test_created_server_exposes_run_transport():
    server = create_mcp_server()
    assert callable(server.run)