#!/usr/bin/env python3
"""End-to-end MCP stdio test against a running FreeCAD Bridge."""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).resolve().parent))
from freecad_bridge.contract import BRIDGE_VERSION  # noqa: E402


@asynccontextmanager
async def client_for(server):
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as client:
            await client.initialize()
            yield client


async def run_test():
    bridge_dir = Path(__file__).resolve().parent
    environment = dict(os.environ)
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(bridge_dir / "mcp_server.py")],
        cwd=str(bridge_dir.parent),
        env=environment,
    )

    async with client_for(server) as client:
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
        if tools["freecad_documents_close"].annotations.destructiveHint is not True:
            raise AssertionError("Destructive tool annotation was lost")

        ping = await client.call_tool("freecad_system_ping", {})
        if ping.isError or ping.structuredContent["bridge_version"] != BRIDGE_VERSION:
            raise AssertionError(
                "MCP ping failed or the running Bridge is stale (expected {}): {}".format(
                    BRIDGE_VERSION, ping
                )
            )
        host_messages = ping.structuredContent.get("host_messages", {})
        if host_messages.get("channel") != "freecad_report_view":
            raise AssertionError("FreeCAD host-message capture is missing: {}".format(ping))

        documents = await client.call_tool("freecad_documents_list", {})
        existing = {item["name"] for item in documents.structuredContent["documents"]}
        if "McpIntegration" in existing:
            await client.call_tool(
                "freecad_documents_close", {"document": "McpIntegration"}
            )

        created_document = await client.call_tool(
            "freecad_documents_new",
            {"name": "McpIntegration", "label": "MCP Integration"},
        )
        if created_document.isError:
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
        if box.isError or abs(box.structuredContent["volume"] - 24.0) > 1e-8:
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
        if not invalid.isError:
            raise AssertionError("MCP schema accepted invalid dimensions")

        closed = await client.call_tool(
            "freecad_documents_close", {"document": "McpIntegration"}
        )
        if closed.isError:
            raise AssertionError("Document close failed: {}".format(closed))

    async with client_for(server) as second_client:
        second_tools = await second_client.list_tools()
        if len(second_tools.tools) != len(tools):
            raise AssertionError("Second MCP handshake returned a different tool set")
        second_ping = await second_client.call_tool("freecad_system_ping", {})
        if second_ping.isError:
            raise AssertionError("Second MCP tool call failed")

    offline_environment = dict(os.environ)
    offline_environment["CAE_BRIDGE_SOCKET"] = "/tmp/opensource-cae-bridge-intentionally-missing.sock"
    offline_server = StdioServerParameters(
        command=sys.executable,
        args=[str(bridge_dir / "mcp_server.py")],
        cwd=str(bridge_dir.parent),
        env=offline_environment,
    )
    async with client_for(offline_server) as offline_client:
        offline_ping = await offline_client.call_tool("freecad_system_ping", {})
        if not offline_ping.isError:
            raise AssertionError("Unavailable Bridge did not produce an MCP tool error")
        if offline_ping.structuredContent["error"]["type"] != "bridge_unavailable":
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
                "repeat_handshake": True,
            }
        )


if __name__ == "__main__":
    anyio.run(run_test)
