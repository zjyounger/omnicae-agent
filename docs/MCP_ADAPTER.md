# MCP adapter

## Decision

The project provides MCP, but MCP is neither the core of the FreeCAD Bridge nor
implemented inside the FreeCAD process.

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

## Versions and dependencies

- Bridge contract: `1.4`
- Bridge: `0.5.0`
- MCP adapter: `0.1.0`
- Official Python MCP SDK: `mcp>=2,<3`

The official SDK is used so that both the current MCP protocol and clients still
performing the older initialisation handshake are handled without this project
maintaining its own wire protocol.
