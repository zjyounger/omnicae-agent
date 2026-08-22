#!/usr/bin/env python3
"""Thin MCP adapter for the native Gmsh Bridge."""

import anyio

from integrations.common.mcp_adapter import build_mcp_server, serve
from integrations.gmsh import BRIDGE_VERSION
from integrations.gmsh.contract import METHOD_SPECS, SCHEMAS
from integrations.gmsh.server import default_socket_path


SERVER = build_mcp_server(
    "omnicae-gmsh", BRIDGE_VERSION, METHOD_SPECS, SCHEMAS, default_socket_path(),
    "Operate one persistent native Gmsh session. Observe, acquire a lease at that revision, perform one action, inspect its step record, then continue or release for human control.",
)


def main():
    anyio.run(serve, SERVER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
