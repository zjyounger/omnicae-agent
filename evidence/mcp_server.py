#!/usr/bin/env python3
"""Thin stdio MCP adapter for the project-owned evidence service."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import anyio
import mcp.server.stdio
import mcp.types as types
from jsonschema import Draft202012Validator
from mcp.server.lowlevel import Server

from evidence.service import (
    EvidenceBackendUnavailable,
    EvidenceDataUnavailable,
    EvidenceService,
    EvidenceSourceNotFound,
)


ADAPTER_VERSION = "0.1.0"
APPLICATIONS = ["calculix-ccx", "calculix-cgx"]


def _schema(properties: dict, required: list[str]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


APPLICATION = {"type": "string", "enum": APPLICATIONS}
TOOLS = [
    types.Tool(
        name="evidence_lookup_exact",
        title="Look up an exact documented API term",
        description="Resolve an exact CalculiX keyword or CGX command to authoritative source pages.",
        inputSchema=_schema(
            {"application": APPLICATION, "term": {"type": "string", "minLength": 1}},
            ["application", "term"],
        ),
        annotations=types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    ),
    types.Tool(
        name="evidence_get_document_map",
        title="Navigate an evidence document",
        description="Return one authoritative page's hierarchy, children, and explicit content references.",
        inputSchema=_schema(
            {
                "application": APPLICATION,
                "source_file": {"type": "string", "minLength": 1},
            },
            ["application"],
        ),
        annotations=types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    ),
    types.Tool(
        name="evidence_open_source",
        title="Open an authoritative evidence source",
        description="Read the complete source page with section path and exact repository location.",
        inputSchema=_schema(
            {
                "application": APPLICATION,
                "source_file": {"type": "string", "minLength": 1},
            },
            ["application", "source_file"],
        ),
        annotations=types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    ),
    types.Tool(
        name="evidence_retrieve",
        title="Retrieve evidence for explicit information needs",
        description="Search exact API and R2R semantic routes independently for each stated information need.",
        inputSchema=_schema(
            {
                "query": {"type": "string", "minLength": 1},
                "application_scope": {
                    "type": "array",
                    "items": APPLICATION,
                    "minItems": 1,
                    "uniqueItems": True,
                    "description": (
                        'JSON array of applications, for example ["calculix-cgx"]; '
                        "never pass a bare string."
                    ),
                },
                "information_needs": {
                    "type": "array",
                    "minItems": 1,
                    "items": _schema(
                        {
                            "id": {"type": "string", "minLength": 1},
                            "query": {"type": "string", "minLength": 1},
                            "application_scope": {
                                "type": "array",
                                "items": APPLICATION,
                                "minItems": 1,
                                "uniqueItems": True,
                                "description": (
                                    "Optional JSON array overriding the task scope for "
                                    "this need; never pass a bare string."
                                ),
                            },
                        },
                        ["id", "query"],
                    ),
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            ["query", "application_scope", "information_needs"],
        ),
        annotations=types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    ),
]
TOOL_BY_NAME = {tool.name: tool for tool in TOOLS}
SERVER = Server(
    "omnicae-evidence",
    version=ADAPTER_VERSION,
    instructions=(
        "Use exact lookup when a term is known. For unfamiliar vocabulary, state "
        "explicit information needs and use evidence_retrieve. Treat candidates as "
        "pointers, then open the authoritative source before relying on a claim. "
        "All application_scope values are JSON arrays, never bare strings."
    ),
)


def _result(payload: dict, is_error: bool = False) -> types.CallToolResult:
    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            )
        ],
        structuredContent=payload,
        isError=is_error,
    )


def _call(name: str, arguments: dict) -> dict:
    service = EvidenceService()
    if name == "evidence_lookup_exact":
        return service.lookup_exact(arguments["application"], arguments["term"])
    if name == "evidence_get_document_map":
        return service.get_document_map(
            arguments["application"], arguments.get("source_file")
        )
    if name == "evidence_open_source":
        return service.open_source(arguments["application"], arguments["source_file"])
    if name == "evidence_retrieve":
        return service.retrieve(
            arguments["query"],
            arguments["information_needs"],
            arguments["application_scope"],
            arguments.get("limit", 5),
        )
    raise KeyError(name)


@SERVER.list_tools()
async def list_tools():
    return TOOLS


@SERVER.call_tool(validate_input=False)
async def call_tool(name: str, arguments: dict):
    tool = TOOL_BY_NAME.get(name)
    if tool is None:
        return _result(
            {"error": {"type": "unknown_tool", "message": "Unknown evidence tool"}},
            is_error=True,
        )
    arguments = arguments or {}
    errors = sorted(
        Draft202012Validator(tool.inputSchema).iter_errors(arguments), key=str
    )
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
        payload = await anyio.to_thread.run_sync(_call, name, arguments)
    except EvidenceSourceNotFound as error:
        return _result(
            {"error": {"type": "source_not_found", "message": str(error)}},
            is_error=True,
        )
    except EvidenceDataUnavailable as error:
        return _result(
            {"error": {"type": "evidence_data_unavailable", "message": str(error)}},
            is_error=True,
        )
    except EvidenceBackendUnavailable as error:
        return _result(
            {"error": {"type": "semantic_backend_unavailable", "message": str(error)}},
            is_error=True,
        )
    return _result(payload)


async def serve() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await SERVER.run(
            read_stream,
            write_stream,
            SERVER.create_initialization_options(),
        )


def main() -> int:
    try:
        anyio.run(serve)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        print(f"Evidence MCP adapter failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
