# Plan

Target state is in [docs/PROJECT.md](docs/PROJECT.md). This file records only
where things stand and what the current front is. It does not lay out a full
path.

## Done

### FreeCAD Bridge

- In-process service inside FreeCAD, Unix domain socket, newline-delimited
  JSON-RPC 2.0.
- Socket restricted to the current user, path allowlist, no arbitrary Python or
  shell.
- Duplicate-start protection, stale socket cleanup, reconnection.
- CAD and GUI calls run on the Qt main thread; no new request is dispatched
  while a slow GUI call has re-entered the event loop.
- `system.reload` reloads the Bridge in place, and keeps the running Bridge
  serving if the new code fails to import.

### CAD API

- System capabilities and versions.
- Documents: new, open, activate, save, close.
- Primitives: box, sphere, cylinder, cone, torus, with placement and axis-angle
  rotation.
- Generic property read and write, so a new primitive parameter needs no new
  schema.
- Boolean operations (cut, fuse, common), transform, list, delete.
- Object, bounding box, volume, and face queries.
- STEP import and export.
- Workbench, view, fit all, screenshot.

### FEM

- One generic object factory over `ObjectsFem` covering analysis, solver,
  material, mesh, and the constraint types the CalculiX writer supports.
- Everything after creation is configured through the same generic property API,
  including geometry references and unit-bearing quantities.
- Gmsh meshing and CalculiX solving driven through the Bridge; a failed solve
  returns a diagnosis rather than an exception.

### Client and MCP adapter

- Dependency-free Python client and a general CLI.
- Structured errors, configurable socket and timeout.
- A single schema-backed contract registry driving the dispatcher,
  `system.capabilities`, and the MCP tool list.

### Verification

Volumes of a 16-object, 5-boolean model match analytic values exactly, and
parametric changes propagate correctly through the boolean tree. Integration
tests cover protocol errors, path escapes, unwritable properties, rejection of
arbitrary Python methods, a client disconnecting during a slow GUI call, and
hot reload in the same process.

Two deck inspectors exist: `tools/inspect_deck.py` reports where constraints and
loads actually landed plus the load resultant, and `tools/inspect_frd.py`
reports result extremes and their locations, flagging peaks on constrained
nodes.

## Current front

Structural static, implicit, with CalculiX, starting from an existing mesh, and
closing the loop against an analytical solution.

Three small things first:

1. ~~**Fix the 11.8% load shortfall in `cases/bracket_static/`.**~~ **Diagnosed**
   (2026-08-12). Not a distribution-weighting defect as first recorded: with
   `SecondOrderLinear=true`, mid-side nodes on the concave bore edge land
   outside the face, FreeCAD's face-node query drops them, and the resulting
   5-node element faces fall through every branch of the area weighting —
   22 faces, 136.24 mm², contributing no load at all. Reproduced offline to five
   decimals by `tools/check_face_load.py`; see [GAPS.md](docs/GAPS.md) G2.
   **What remains:** re-run the bracket so the deck actually reaches 5000 N.
   The obvious routes are now closed: pressure is normal to the face and the
   load is radial, and cgx's traction card is rejected by ccx ([GAPS.md](docs/GAPS.md)
   G11). So the `*CLOAD` block has to be computed and written directly, with
   the total checked against intent. Defining the surface in cgx is verified to
   work — `enq` + `send abq sur` recovers all 224 faces, and a 1 MPa pressure
   run returns 1256.619 N against 1256.637 mm² analytic.
2. **What gets recorded.** Decide what a single analysis must write down — the
   problem definition, the assumptions with their invalidation conditions, and
   the record of a person overruling the agent. This part cannot be reconstructed
   later.
3. **An [Engineering Evidence Library](docs/EVIDENCE_LIBRARY.md) over official
   documentation**, CalculiX first. It is useful on its own: answering what a
   keyword means and why an error occurred already saves a great deal of time.
   The interface is backend-independent; R2R is the initial lightweight
   candidate and RAGFlow an optional enterprise adapter. Repository files
   remain authoritative, and code and visual evidence follow only after
   measured text retrieval works. Implementation details are in
   [the development plan](docs/development/EVIDENCE_LIBRARY.md).
4. **A first benchmark**, starting from `calculix/cantilever.inp`, reporting the
   deviation from the analytical answer.

Two things fell out of that diagnosis and are worth doing before the next
analysis, because both are about not losing information that already exists:

- **Capture FreeCAD's console in the Bridge** ([GAPS.md](docs/GAPS.md) S5).
  FreeCAD printed the cause of the shortfall, in plain language, at the moment
  the deck was written. Nothing was listening. Any `PrintError` /
  `PrintMessage` raised during a mesh or write operation should come back with
  the call result.
- **Read [`docs/AGENT_FAILURE_MODES.md`](docs/AGENT_FAILURE_MODES.md).** The
  register of how the agent misleads itself, with the evidence from this
  repository. The G2 root cause sat in files already on disk for the whole time
  the question stayed open; that pattern is the subject of the document.

## Later

Meshing, geometry pre-processing, other solvers, the procedure library, and
autonomy levels all wait until the first loop closes.
