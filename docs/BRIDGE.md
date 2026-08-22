# FreeCAD Bridge

## Purpose

The Bridge is a control layer running inside the FreeCAD process. It turns
FreeCAD's `App` and `Gui` APIs into a stable external protocol so that clients
need know nothing about the FreeCAD Python process or the Qt lifecycle.

The same Bridge installs on an engineer's workstation or inside a Linux worker.
The client protocol depends on no LLM vendor.

Every machine actually running FreeCAD therefore carries a copy. It is not a
local special case but the **deployment unit of a runtime adapter**: inside
local FreeCAD on a workstation, inside a worker or container in the cloud. A
central service or agent depends only on the protocol, never on this
development machine's paths, windows, or desktop state.

## Scope

### In

- Local Unix domain socket.
- Newline-delimited JSON-RPC 2.0.
- Allowlisted FreeCAD document, CAD, FEM, and GUI operations.
- Capability discovery, versioning, structured errors.
- Per-request FreeCAD Report View message capture on success and failure.
- File path allowlist.
- External Python client and CLI.
- A shared schema-backed method registry.
- An optional stdio MCP adapter in a separate process.

### Out

- Arbitrary Python or shell execution.
- REST services and authentication.
- Cloud queues and databases.
- Multi-tenancy.
- Coordinate-based mouse automation.

## Process model

The Bridge loads as a Python module into the FreeCAD GUI process. The socket is
a Qt `QLocalServer`, so requests arrive through the Qt event loop and FreeCAD
API calls happen on the GUI main thread.

External clients do not import FreeCAD:

```text
Python/CLI ── Unix socket ── QLocalServer ── dispatcher ── FreeCAD App/Gui
```

MCP, Claude Code, Codex, or a web front end all sit on the client side and never
enter the FreeCAD plugin core:

```text
agent / CLI / web
        │
   client adapter
        │ JSON-RPC
        ▼
FreeCAD worker + Bridge
```

The Unix socket deliberately solves only the process boundary on a single
execution node. When a cloud control plane later needs network transport, a
worker service should wrap the local Bridge rather than exposing the FreeCAD
socket to a network.

## Protocol

Request:

```json
{"jsonrpc":"2.0","id":1,"method":"system.ping","params":{}}
```

Success:

```json
{"jsonrpc":"2.0","id":1,"result":{"bridge_version":"0.6.0"}}
```

Error:

```json
{
  "jsonrpc":"2.0",
  "id":1,
  "error":{"code":-32602,"message":"Invalid params","data":{"field":"length"}}
}
```

No batch requests. Maximum 1 MiB per message.

## Methods

### System

- `system.ping`
- `system.capabilities`
- `system.reload`

### Documents

- `documents.list`
- `documents.new`
- `documents.activate`
- `documents.open`
- `documents.save`
- `documents.close`

### CAD

- `objects.create` — box, sphere, cylinder, cone, torus, with placement and
  axis-angle rotation
- `objects.list`
- `objects.inspect`
- `objects.delete`
- `objects.get_properties`
- `objects.set_properties`
- `objects.transform`
- `objects.boolean` — cut, fuse, common
- `shapes.list_faces`
- `shapes.find_planar_faces`

`objects.create` covers only the dimensions each primitive requires. Everything
else — a cylinder's `Angle`, a sphere's `Angle1/2/3` — is set through
`objects.set_properties`, so a new parameter never needs a new schema.

The earlier `cad.*` names remain as hidden compatibility aliases and are not
exposed over MCP.

### FEM

- `fem.create` — analysis, solver_ccx, material_solid, mesh_gmsh, mesh_region,
  mesh_group, and the fixed / displacement / force / pressure / contact / tie /
  spring / selfweight / sectionprint / transform / rigidbody constraints
- `fem.mesh`
- `fem.solve`

One generic factory rather than a method per constraint type. FEM objects are
Python features: an object created with a bare `addObject` has no Proxy and then
silently writes nothing to the solver deck, so they must go through the
`ObjectsFem` factories.

Everything after creation is configured through `objects.set_properties`,
including which face a constraint applies to (`References`). `fem.create`
returns the object's full property list so a client can discover what to set
without a per-type schema.

`fem.solve` does not treat a failed solve as an exception: it returns `solved`,
`solver_errors` extracted from the solver's stdout, and `warnings`. A failed
solve has to be a diagnosable result.

Every Bridge response also carries `host_messages`, the Report View text added
during that exact request. This preserves `PrintMessage`, `PrintWarning`, and
`PrintError` diagnostics emitted inside FreeCAD's FEM writers and mesh tools.
If the Report View is disabled in the FreeCAD build, the field explicitly
reports `capture_available: false`; an empty captured string is never used to
claim that the host emitted nothing.

**Write units on dimensional quantities**: `{"Force": "5000 N"}`. A bare number
is interpreted in FreeCAD's internal units (mm–kg–s, so force is mN) and `5000`
silently becomes 5 N.

### File exchange

- `io.import_step`
- `io.export_step`

### GUI

- `gui.activate_workbench`
- `gui.set_view`
- `gui.fit_all`
- `gui.save_screenshot`

## Two traps in GUI calls

**Camera animation blocks the calling thread.** FreeCAD's
`UseNavigationAnimations` is on by default and the animation duration scales
with camera travel; `gui.fit_all` measured 11 s on a 20-face model against 1–2 s
on an empty document. The Bridge disables the preference around each
programmatic view change and restores it afterwards, so it depends on no local
configuration and does not alter the user's own experience. After the fix,
1–2 s.

**`Gui.updateGui()` re-enters the Qt event loop**, so a disconnection is
processed midway through a request. The Bridge keeps a dispatch depth counter to
prevent a new request being dispatched during re-entry and to defer socket
destruction until the request stack unwinds. Otherwise `deleteLater()` frees a
socket while Qt is still delivering read notifications for it, which segfaults
FreeCAD.

The client default timeout is 30 s to leave room for slow GUI calls.

## Security

- Socket file mode `0600`.
- Only the Bridge's start directory is reachable by default.
- `CAE_BRIDGE_ALLOWED_ROOTS` adds directories, separated by `:`.
- File paths are resolved and validated before any read or write.
- Methods and parameters are both allowlisted.
- No general script execution method.
- Internal exceptions become structured errors; no traceback is returned to an
  untrusted client, though it is printed to the FreeCAD console.

## Verified baseline

Exercised in the FreeCAD 1.1.3 GUI: startup, capability discovery, primitive
creation, generic property read and write, boolean operations, rotation,
volume / bounding box / face queries, FCStd save, STEP export and re-import,
view and screenshot, reconnection, hot reload, and rejection of malformed JSON,
bad parameters, out-of-root paths, unwritable properties, and arbitrary Python
methods. No mouse automation.

A multi-body verification model built step by step through `objects.create` and
`objects.boolean` matches analytic volumes exactly: a three-body fuse at
254215.47 mm³ with zero error, four Ø10 holes removing exactly 1200π mm³, and a
change to `Boss.Height` altering the top-level result by exactly
π·(25²−15²)·10 — showing that parametric changes propagate correctly through the
boolean tree.

MCP decisions and token budgeting are in [MCP_ADAPTER.md](MCP_ADAPTER.md).
