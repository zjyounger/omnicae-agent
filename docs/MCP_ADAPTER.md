# MCP adapters

## Decision

The project provides separate MCP servers for separate capabilities. MCP is a
replaceable agent-facing transport, not the owner of application or evidence
logic.

## FreeCAD control

```text
Claude Code / other MCP host
            │ stdio MCP
            ▼
      thin MCP adapter
            │ Bridge JSON-RPC
            ▼
FreeCAD GUI process + Bridge
```

The MCP adapter is a replaceable agent adapter. The Bridge remains directly
usable from a CLI, from Python, from a worker service, or from some future
protocol.

## No duplicated wrappers

Each controlled operation is registered exactly once, in
`freecad_bridge/contract.py`:

- Bridge method name
- short description
- JSON Schema
- read-only, destructive, idempotent, open-world annotations
- whether it is exposed over MCP

The FreeCAD dispatcher checks its handlers against the same registry,
`system.capabilities` returns the same registry, MCP's `tools/list` is generated
from it, and `tools/call` forwards uniformly to the Bridge.

There is therefore no `freecad_create_box()` calling `cad.create_box()` — no
duplicated business logic.

## Interface granularity

The public surface does not grow one tool per geometry type. It favours stable,
controlled domain operations:

- `objects.*`
- `shapes.*`
- `documents.*`
- `fem.*`
- `io.*`
- `gui.*`

`objects.create` extends to new object types through `kind` and a matching
parameter schema; everything else is set through `objects.set_properties`. This
is not arbitrary FreeCAD Python execution: types, parameters, and file paths
remain under the Bridge's allowlist.

Older experimental methods survive as compatibility aliases that are not exposed
over MCP, so they do not consume an agent's tool space.

## Tokens and agent load

- Descriptions stay short; parameters are expressed as JSON Schema.
- No repeated help text in results.
- Results carry both structured data and compact JSON text, for old and new
  clients.
- `tools/list` sets a private cache hint, so tool definitions are not
  regenerated on every call.
- Compatibility aliases and internal capability discovery are not exposed to
  agents.
- `system.reload` is not exposed either: a developer operation does not belong
  in an agent's tool space.
- No generic `call(method, params)` tool that would force an agent to keep
  consulting documentation.

Claude Code can load MCP tools lazily. As the count grows, adapters or servers
can be split by CAD, mesh, and solver without touching the Bridge core.

## Lifecycle

The FreeCAD Bridge must be running first. Claude Code starts the stdio MCP
adapter automatically from the project's `.mcp.json`; no separate terminal is
needed.

If FreeCAD is not running the tools are still discoverable, calls return a
structured `bridge_unavailable` error, and the MCP process does not exit.

The adapter caches its tool table in its own process. After adding or changing a
Bridge method, a Bridge hot reload takes effect immediately but the MCP adapter
must be restarted to see it.

## Gmsh, CalculiX, and CGX

Three additional stdio MCP adapters are registered independently:

| MCP server | Local owner | Interaction level |
|---|---|---|
| gmsh-bridge | persistent Gmsh Python/FLTK Bridge | native-cooperative |
| calculix-service | persistent ccx job service | batch |
| cgx-bridge | one exact CGX PID/window controller | gui-fallback |

The MCP processes do not start application GUIs. They connect to the user-only
local sockets owned by the application services. This prevents each coding
agent from launching a second Gmsh or CGX window.

Every state-changing tool requires actor and expected_revision. The normal
sequence is observe, acquire, execute one operation, inspect the returned step,
then continue at revision_after or release control to a person. CGX tool
results additionally state that xdotool was the transport and whether the
command was acknowledged by console output, visual change only, or remained
uncertain.

The official Gmsh wheel contains the application and native SDK, so the Python
and MCP dependencies install with:

    .venv-mcp/bin/pip install -r requirements.txt

## Engineering evidence

The knowledge system uses the open-source
[R2R framework](https://github.com/SciPhi-AI/R2R) as its semantic retrieval
foundation. The project-owned MCP below is a CAE-specific interface over R2R,
not a replacement for, fork of, or claim of ownership over R2R.

The `evidence-library` stdio server wraps the project-owned, read-only
`EvidenceService`:

```text
MCP host
   │ stdio MCP
   ▼
evidence/mcp_server.py
   ▼
evidence/service.py
   ├── exact API catalogue
   ├── document map and explicit references
   ├── authoritative source opening
   └── explicit multi-need retrieval
             │ semantic route only
             ▼
            R2R REST API
```

It exposes four tools: `evidence_lookup_exact`, `evidence_get_document_map`,
`evidence_open_source`, and `evidence_retrieve`. All are read-only. Ingestion,
index rebuilding, database access, and R2R's answer-generating `rag` operation
are not exposed.

Search results preserve short summaries or matched excerpts and include exact
`open_arguments`. Cross-references are expanded only after a source is selected,
through the document-map tool; pre-expanding every candidate made the MCP result
too large and caused the agent to wander between pages.

R2R 3.6.5 contains an upstream `/app/r2r/mcp.py`, but it is not the project's
MCP interface. That script exposes only raw `search` and `rag`, does not know the
project API catalogue, document map, source-location sidecar, or multi-need
contract, and its container does not include its MCP runtime dependency.

The two project MCP servers are registered separately for each coding-agent
host: `.mcp.json` is read by Claude Code, and `.codex/config.toml` is read by
Codex for trusted copies of this repository. Both configurations launch the
same server implementations; neither is a second knowledge backend.

The Codex project configuration explicitly forwards `XDG_RUNTIME_DIR` and
`CAE_BRIDGE_SOCKET` to the FreeCAD MCP process. Without that forwarding, a
Codex-launched adapter falls back to `/tmp` and reports the Bridge unavailable
even while FreeCAD is serving its real socket under `/run/user/<uid>`.

## Versions and dependencies

- Bridge contract: `1.4`
- Bridge: `0.5.0`
- MCP adapter: `0.1.0`
- Official Python MCP SDK: `mcp>=1.27,<2`

The 1.x line is pinned because it connects to the installed Claude Code host and
retains the `FastMCP` import expected by R2R 3.6.5's upstream example. Installing
the unbounded current package selected MCP SDK 2.0, which removed that import and
timed out when the installed Claude Code host attempted the stdio handshake.
