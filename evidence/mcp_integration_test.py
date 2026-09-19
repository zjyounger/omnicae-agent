#!/usr/bin/env python3
"""End-to-end MCP test for the read-only evidence adapter."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


REPO_ROOT = Path(__file__).resolve().parents[1]


def source_keys(items: list[dict]) -> set[tuple[str, str]]:
    return {(item["manual"], item["source_file"]) for item in items}


async def run_test() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(REPO_ROOT / "evidence" / "mcp_server.py")],
        cwd=str(REPO_ROOT),
        env=dict(os.environ),
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as client:
            await client.initialize()
            listed = await client.list_tools()
            await exercise_live_tools(client, listed)

    offline_environment = dict(os.environ)
    offline_environment["R2R_API_URL"] = "http://127.0.0.1:1"
    offline_server = StdioServerParameters(
        command=sys.executable,
        args=[str(REPO_ROOT / "evidence" / "mcp_server.py")],
        cwd=str(REPO_ROOT),
        env=offline_environment,
    )
    async with stdio_client(offline_server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as client:
            await client.initialize()
            offline = await client.call_tool(
                "evidence_retrieve",
                {
                    "query": "Find CLOAD",
                    "application_scope": ["calculix-ccx"],
                    "information_needs": [{"id": "cload", "query": "CLOAD"}],
                },
            )
            if not offline.isError:
                raise AssertionError("unavailable R2R did not produce an MCP tool error")
            if offline.structuredContent["error"]["type"] != "semantic_backend_unavailable":
                raise AssertionError(f"wrong offline error: {offline}")

    print(
        {
            "tool_count": 4,
            "raw_r2r_tools_hidden": True,
            "exact_lookup": "node242.html",
            "document_navigation": True,
            "authoritative_source_open": True,
            "multi_need_sources": ["node95.html", "node79.html", "node182.html"],
            "semantic_backend": "r2r",
            "schema_rejection": True,
            "offline_error": True,
        }
    )


async def exercise_live_tools(client, listed) -> None:
        tools = {tool.name: tool for tool in listed.tools}
        expected = {
            "evidence_lookup_exact",
            "evidence_get_document_map",
            "evidence_open_source",
            "evidence_retrieve",
        }
        if set(tools) != expected:
            raise AssertionError(f"unexpected MCP tools: {sorted(tools)}")
        if "rag" in tools or "search" in tools:
            raise AssertionError("raw R2R tools leaked into the project MCP surface")
        if any(tool.annotations.readOnlyHint is not True for tool in tools.values()):
            raise AssertionError("a read-only evidence annotation was lost")

        lookup = await client.call_tool(
            "evidence_lookup_exact",
            {"application": "calculix-ccx", "term": "CLOAD"},
        )
        if lookup.isError:
            raise AssertionError(f"exact lookup failed: {lookup}")
        if [item["source_file"] for item in lookup.structuredContent["matches"]] != [
            "node242.html"
        ]:
            raise AssertionError(f"CLOAD resolved incorrectly: {lookup}")

        document_map = await client.call_tool(
            "evidence_get_document_map",
            {"application": "calculix-ccx", "source_file": "node223.html"},
        )
        children = {
            item["source_file"] for item in document_map.structuredContent["children"]
        }
        if "node242.html" not in children:
            raise AssertionError("document map did not expose the CLOAD child")

        source = await client.call_tool(
            "evidence_open_source",
            {"application": "calculix-ccx", "source_file": "node242.html"},
        )
        text = " ".join(
            block["text"] for block in source.structuredContent["blocks"]
        ).casefold()
        if source.isError or "concentrated forces" not in text:
            raise AssertionError("authoritative CLOAD page did not open")

        retrieve = await client.call_tool(
            "evidence_retrieve",
            {
                "query": "Build and export a CGX surface selected by coordinate.",
                "application_scope": ["calculix-cgx"],
                "limit": 5,
                "information_needs": [
                    {
                        "id": "coordinate-selection",
                        "query": "CGX enquire nodes by rectangular coordinates and tolerance",
                    },
                    {
                        "id": "complete-faces",
                        "query": "CGX complete a set downwards to element faces comp",
                    },
                    {
                        "id": "export-surface",
                        "query": "CGX send a set as Abaqus surface",
                    },
                ],
            },
        )
        if retrieve.isError:
            raise AssertionError(f"multi-need retrieval failed: {retrieve}")
        expected_sources = ["node95.html", "node79.html", "node182.html"]
        for need, expected_source in zip(
            retrieve.structuredContent["information_needs"], expected_sources
        ):
            found = source_keys(need["routes"]["api_catalogue"])
            found.update(source_keys(need["routes"]["semantic"]))
            if ("cgx", expected_source) not in found:
                raise AssertionError(
                    f"{need['id']} did not retrieve {expected_source}: {sorted(found)}"
                )
        if retrieve.structuredContent["semantic_backend"] != "r2r":
            raise AssertionError("semantic backend provenance was lost")

        invalid = await client.call_tool(
            "evidence_lookup_exact",
            {"application": "unknown", "term": "CLOAD"},
        )
        if not invalid.isError:
            raise AssertionError("MCP schema accepted an unsupported application")


if __name__ == "__main__":
    anyio.run(run_test)
