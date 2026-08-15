#!/usr/bin/env python3
"""Thin stdio MCP adapter for the FreeCAD Bridge contract."""

import json
import sys

import anyio
import mcp.server.stdio
import mcp.types as types
from jsonschema import Draft202012Validator
from mcp.server.lowlevel import Server

from client import BridgeClient, BridgeClientError, BridgeRemoteError
from freecad_bridge.contract import MCP_SPEC_BY_NAME


ADAPTER_VERSION = "0.1.0"


def _mcp_tool(spec):
    annotations = spec.as_capability()["annotations"]
    return types.Tool(
        name=spec.mcp_name,
        title=spec.title,
        description=spec.description,
        inputSchema=spec.input_schema,
        annotations=types.ToolAnnotations(
            readOnlyHint=annotations["read_only"],
            destructiveHint=annotations["destructive"],
            idempotentHint=annotations["idempotent"],
            openWorldHint=annotations["open_world"],
        ),
    )


TOOLS = [_mcp_tool(spec) for spec in MCP_SPEC_BY_NAME.values()]


def _result(payload, is_error=False):
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        structuredContent=payload,
        isError=is_error,
    )


def _bridge_call(spec, arguments):
    with BridgeClient() as client:
        return client.call(spec.name, arguments)


async def list_tools(_context, _params):
    return types.ListToolsResult(
        tools=TOOLS,
        ttlMs=300000,
        cacheScope="private",
    )


async def call_tool(_context, params):
    spec = MCP_SPEC_BY_NAME.get(params.name)
    if spec is None:
        return _result(
            {"error": {"type": "unknown_tool", "message": "Unknown FreeCAD tool"}},
            is_error=True,
        )

    arguments = params.arguments or {}
    errors = sorted(Draft202012Validator(spec.input_schema).iter_errors(arguments), key=str)
    if errors:
        error = errors[0]
        return _result(
            {
                "error": {
                    "type": "invalid_arguments",
                    "message": error.message,
                    "path": list(error.absolute_path),
                }
            },
            is_error=True,
        )

    try:
        result = await anyio.to_thread.run_sync(_bridge_call, spec, arguments)
    except BridgeRemoteError as exc:
        return _result(
            {
                "error": {
                    "type": "bridge_error",
                    "code": exc.code,
                    "message": exc.message,
                    "data": exc.data,
                }
            },
            is_error=True,
        )
    except (BridgeClientError, OSError, TimeoutError) as exc:
        return _result(
            {
                "error": {
                    "type": "bridge_unavailable",
                    "message": str(exc),
                }
            },
            is_error=True,
        )
    return _result(result)


async def serve():
    server = Server(
        "opensource-cae-freecad",
        version=ADAPTER_VERSION,
        title="Open Source CAE FreeCAD Bridge",
        description="Dynamic, schema-backed MCP adapter for a local FreeCAD Bridge.",
        instructions=(
            "Use these tools for FreeCAD document, CAD object, topology, file exchange, "
            "and GUI operations. Start the FreeCAD Bridge before calling a tool."
        ),
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    try:
        anyio.run(serve)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print("FreeCAD MCP adapter failed: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
