#!/usr/bin/env python3
"""Thin MCP adapter for the CalculiX job service."""

import anyio

from integrations.common.mcp_adapter import build_mcp_server, serve
from integrations.calculix import BRIDGE_VERSION
from integrations.calculix.contract import METHOD_SPECS, SCHEMAS
from integrations.calculix.server import default_socket_path


SERVER = build_mcp_server(
    "omnicae-calculix", BRIDGE_VERSION, METHOD_SPECS, SCHEMAS, default_socket_path(),
    "Run CalculiX as a batch solver service. Observe, acquire the job lease, start one deck, and poll structured status and evidence files.",
)


def main():
    anyio.run(serve, SERVER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
