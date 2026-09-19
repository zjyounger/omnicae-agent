#!/usr/bin/env python3
"""MCP handshakes and live pings for the application integrations."""

import os
import sys
from contextlib import asynccontextmanager

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def connect(module, environment):
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        cwd=os.getcwd(),
        env=environment,
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as client:
            await client.initialize()
            yield client


async def check(module, socket_variable, socket_path, ping_tool, required_tools):
    environment = dict(os.environ)
    environment[socket_variable] = socket_path
    async with connect(module, environment) as client:
        listed = await client.list_tools()
        tools = {tool.name: tool for tool in listed.tools}
        missing = set(required_tools) - set(tools)
        if missing:
            raise AssertionError("{} missing tools {}".format(module, sorted(missing)))
        ping = await client.call_tool(ping_tool, {})
        if ping.isError:
            raise AssertionError("{} live ping failed: {}".format(module, ping))
        invalid = await client.call_tool(required_tools[-1], {"unexpected": True})
        if not invalid.isError or invalid.structuredContent["error"]["type"] != "invalid_arguments":
            raise AssertionError("{} did not reject invalid schema input".format(module))
        return len(tools), ping.structuredContent["interaction_level"]


async def run_test():
    checks = [
        (
            "integrations.gmsh.mcp_server",
            "CAE_GMSH_BRIDGE_SOCKET",
            "/tmp/omnicae-gmsh-test.sock",
            "gmsh_system_ping",
            ["gmsh_session_observe", "gmsh_mesh_generate", "gmsh_groups_create"],
        ),
        (
            "integrations.calculix.mcp_server",
            "CAE_CALCULIX_BRIDGE_SOCKET",
            "/tmp/omnicae-calculix-test.sock",
            "calculix_system_ping",
            ["calculix_session_observe", "calculix_jobs_start", "calculix_jobs_cancel"],
        ),
        (
            "integrations.cgx.mcp_server",
            "CAE_CGX_BRIDGE_SOCKET",
            "/tmp/omnicae-cgx-test.sock",
            "cgx_system_ping",
            ["cgx_session_observe", "cgx_command_execute", "cgx_process_stop"],
        ),
    ]
    results = {}
    for check_args in checks:
        count, level = await check(*check_args)
        results[check_args[0]] = {"tools": count, "interaction_level": level}
    print(results)


if __name__ == "__main__":
    anyio.run(run_test)
