#!/usr/bin/env python3
"""End-to-end MCP stdio test against a running FreeCAD Bridge."""

import os
import sys
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters, stdio_client

sys.path.insert(0, str(Path(__file__).resolve().parent))
from freecad_bridge.contract import BRIDGE_VERSION  # noqa: E402


async def run_test():
    bridge_dir = Path(__file__).resolve().parent
    environment = dict(os.environ)
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(bridge_dir / "mcp_server.py")],
        cwd=str(bridge_dir.parent),
        env=environment,
    )

    async with Client(stdio_client(server), mode="auto") as client:
        listed = await client.list_tools()
        tools = {tool.name: tool for tool in listed.tools}
        required = {
            "freecad_system_ping",
            "freecad_documents_new",
            "freecad_objects_create",
            "freecad_objects_inspect",
            "freecad_documents_close",
        }
        missing = required - set(tools)
        if missing:
            raise AssertionError("Missing MCP tools: {}".format(sorted(missing)))
        if "freecad_cad_create_box" in tools:
            raise AssertionError("Deprecated compatibility alias leaked into MCP")
        if tools["freecad_documents_close"].annotations.destructive_hint is not True:
            raise AssertionError("Destructive tool annotation was lost")

        ping = await client.call_tool("freecad_system_ping", {})
        if ping.is_error or ping.structured_content["bridge_version"] != BRIDGE_VERSION:
            raise AssertionError(
                "MCP ping failed or the running Bridge is stale (expected {}): {}".format(
                    BRIDGE_VERSION, ping
                )
            )

        documents = await client.call_tool("freecad_documents_list", {})
        existing = {item["name"] for item in documents.structured_content["documents"]}
        if "McpIntegration" in existing:
            await client.call_tool(
                "freecad_documents_close", {"document": "McpIntegration"}
            )

        created_document = await client.call_tool(
            "freecad_documents_new",
            {"name": "McpIntegration", "label": "MCP Integration"},
        )
        if created_document.is_error:
            raise AssertionError("Document creation failed: {}".format(created_document))

        box = await client.call_tool(
            "freecad_objects_create",
            {
                "document": "McpIntegration",
                "name": "McpBox",
                "kind": "box",
                "parameters": {"length": 4, "width": 3, "height": 2},
            },
        )
        if box.is_error or abs(box.structured_content["volume"] - 24.0) > 1e-8:
            raise AssertionError("Object creation failed: {}".format(box))

        invalid = await client.call_tool(
            "freecad_objects_create",
            {
                "document": "McpIntegration",
                "name": "Invalid",
                "kind": "box",
                "parameters": {"length": -1, "width": 3, "height": 2},
            },
        )
        if not invalid.is_error:
            raise AssertionError("MCP schema accepted invalid dimensions")

        closed = await client.call_tool(
            "freecad_documents_close", {"document": "McpIntegration"}
        )
        if closed.is_error:
            raise AssertionError("Document close failed: {}".format(closed))

    async with Client(stdio_client(server), mode="legacy") as legacy_client:
        legacy_tools = await legacy_client.list_tools()
        if len(legacy_tools.tools) != len(tools):
            raise AssertionError("Legacy MCP handshake returned a different tool set")
        legacy_ping = await legacy_client.call_tool("freecad_system_ping", {})
        if legacy_ping.is_error:
            raise AssertionError("Legacy MCP tool call failed")

    offline_environment = dict(os.environ)
    offline_environment["CAE_BRIDGE_SOCKET"] = "/tmp/opensource-cae-bridge-intentionally-missing.sock"
    offline_server = StdioServerParameters(
        command=sys.executable,
        args=[str(bridge_dir / "mcp_server.py")],
        cwd=str(bridge_dir.parent),
        env=offline_environment,
    )
    async with Client(stdio_client(offline_server), mode="auto") as offline_client:
        offline_ping = await offline_client.call_tool("freecad_system_ping", {})
        if not offline_ping.is_error:
            raise AssertionError("Unavailable Bridge did not produce an MCP tool error")
        if offline_ping.structured_content["error"]["type"] != "bridge_unavailable":
            raise AssertionError("Unavailable Bridge returned the wrong error type")

        print(
            {
                "tool_count": len(tools),
                "dynamic_registry": True,
                "legacy_alias_hidden": True,
                "risk_annotations": True,
                "structured_result": True,
                "schema_rejection": True,
                "live_freecad_call": True,
                "offline_error": True,
                "modern_and_legacy_mcp": True,
            }
        )


if __name__ == "__main__":
    anyio.run(run_test)
