"""Thin MCP adapter factory for a local application Bridge contract."""

import json

import anyio
import mcp.server.stdio
import mcp.types as types
from jsonschema import Draft202012Validator
from mcp.server.lowlevel import Server

from .client import LocalBridgeClient, LocalBridgeError


def build_mcp_server(server_name, version, specs, schemas, socket_path, instructions):
    spec_by_tool = {spec.mcp_name: spec for spec in specs}
    server = Server(server_name, version=version, instructions=instructions)
    tools = []
    for spec in specs:
        if spec.name == "system.capabilities":
            continue
        annotations = spec.as_dict()["annotations"]
        tools.append(
            types.Tool(
                name=spec.mcp_name,
                title=getattr(spec, "title", spec.name),
                description=spec.description,
                inputSchema=schemas[spec.name],
                annotations=types.ToolAnnotations(
                    readOnlyHint=annotations["read_only"],
                    destructiveHint=annotations["destructive"],
                    idempotentHint=annotations.get("idempotent", False),
                    openWorldHint=False,
                ),
            )
        )

    def result(payload, is_error=False):
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text)],
            structuredContent=payload,
            isError=is_error,
        )

    @server.list_tools()
    async def list_tools():
        return tools

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        spec = spec_by_tool.get(name)
        if spec is None:
            return result({"error": {"type": "unknown_tool", "message": "Unknown tool"}}, True)
        arguments = arguments or {}
        errors = sorted(Draft202012Validator(schemas[spec.name]).iter_errors(arguments), key=str)
        if errors:
            error = errors[0]
            return result(
                {"error": {"type": "invalid_arguments", "message": error.message, "path": list(error.absolute_path)}},
                True,
            )
        try:
            payload = await anyio.to_thread.run_sync(
                LocalBridgeClient(socket_path).call, spec.name, arguments
            )
        except LocalBridgeError as exc:
            return result(
                {"error": {"type": "bridge_error", "code": exc.code, "message": exc.message, "data": exc.data}},
                True,
            )
        except (OSError, TimeoutError, RuntimeError) as exc:
            return result({"error": {"type": "bridge_unavailable", "message": str(exc)}}, True)
        return result(payload)

    return server


async def serve(server):
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
