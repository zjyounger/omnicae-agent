#!/usr/bin/env python3
"""Thin MCP adapter for the explicitly limited CGX GUI fallback."""

import anyio

from integrations.common.mcp_adapter import build_mcp_server, serve
from integrations.cgx import BRIDGE_VERSION
from integrations.cgx.contract import METHOD_SPECS, SCHEMAS
from integrations.cgx.server import default_socket_path


SERVER = build_mcp_server(
    "omnicae-cgx", BRIDGE_VERSION, METHOD_SPECS, SCHEMAS, default_socket_path(),
    "CGX has no native command API. This adapter controls one exact window through a declared GUI fallback. Require an exclusive lease, one command per call, and inspect acknowledgement and screenshots.",
)


def main():
    anyio.run(serve, SERVER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
