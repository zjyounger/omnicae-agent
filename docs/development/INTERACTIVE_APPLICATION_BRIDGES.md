# Interactive application bridges

## Objective

The objective is an observable engineering session, not a Bridge for its own
sake. A native Bridge is preferred when persistent application state, live
inspection, or human handoff materially improves the evidence. A batch or
command integration is sufficient when it can expose the resulting state and
verification artifacts without a live GUI.

Every interaction level follows the same loop:

```text
observe -> propose one action -> execute -> wait for acknowledgement
        -> observe again -> verify -> record -> continue or hand off
```

A generated script may be the primary control path for a deterministic
workflow, but execution alone is not verification. While a model is being
understood, keep actions small enough that the resulting state can be observed
and a failed assumption can be traced to a particular step.

## When a Bridge is warranted

Use a live Bridge when one or more of these are needed:

- native state exists only inside a long-lived application process;
- the user and agent need to inspect or edit the same session;
- selections, application events, or incremental visual changes are part of
  the engineering evidence;
- restarting or reconstructing state between actions is materially costly.

Do not require a Bridge when a CLI, file exchange, or native batch API can
provide the same action acknowledgement, inspectable state, artifacts, and
independent checks. In either case, screenshots supplement structured evidence;
they do not establish hidden properties or engineering correctness.

## Non-negotiable behaviour

- One application process and one writer at a time.
- Every mutation carries an actor and the state revision it was based on.
- A mutation is rejected when the live state changed since that observation.
- Every action returns before/after state, exact operation, status, artifacts,
  and verification data available from the application.
- A person can take the write lease; the agent then observes but does not write.
- Returning control requires a fresh observation of native state.
- Screenshots are visual evidence, not proof of hidden values such as material,
  load, or element properties.
- Native APIs and application events are preferred. GUI keyboard automation is
  an explicitly reported fallback and requires an exclusive write lease.

## Capability levels

| Level | Meaning | Permitted operation |
|---|---|---|
| native-cooperative | Native API, live state query, persistent GUI | Agent and human hand off in one session |
| native-exclusive | Native command channel but no reliable user-change events | One writer; reconcile before every action |
| gui-fallback | Window/keyboard automation only | Explicit exclusive lease, screenshot and process checks after every command |
| batch | Files and subprocess only | No claim of live GUI interaction |

The level is declared by each integration and returned by capability discovery.

## Application plan

### Gmsh

- [x] Own the official `gmsh` Python API and FLTK GUI in one long-lived process.
- [x] Run every API call on the GUI main thread through a serialized command queue.
- [x] Expose model open/clear, entity inventory and bounding boxes.
- [x] Expose mesh options, generation, clearing, statistics, quality and export.
- [x] Expose physical groups and interactive entity selection.
- [x] Detect native-state changes between agent actions.
- [x] Capture a GUI image and structured state after requested steps.
- [x] Provide JSON-RPC client, CLI, MCP adapter and integration tests.

Installation is pip-first: the official `gmsh` wheel contains the application
and SDK. A matching system package remains an optional deployment choice.

### CalculiX ccx

- [x] Treat the solver as batch, not as a GUI Bridge.
- [x] Start one job without blocking the control service.
- [x] Report PID, files, convergence/error lines and terminal state.
- [x] Support list, status polling and explicit cancellation.
- [x] Preserve the exact deck and solver log as evidence.
- [x] Provide JSON-RPC client, CLI, MCP adapter and tests.

### CalculiX GraphiX (CGX)

- [x] Confirm and document that upstream exposes no supported socket/API.
- [x] Own one persistent CGX process and identify its exact window and PID.
- [x] Prefer command files for reproducible operations.
- [x] Use GUI keyboard control only as a declared `gui-fallback` capability.
- [x] Require an exclusive lease before fallback input.
- [x] Verify each command from process state, console output, generated files,
  and a captured window image; never infer success from keystrokes alone.
- [x] Support explicit human takeover and state reconciliation.
- [x] Provide JSON-RPC client, CLI, MCP adapter and tests.

## Step record

Every bridge mutation produces a record with these conceptual fields:

```yaml
action_id: stable identifier
application: application and version
actor: agent or human lease owner
operation: exact project-owned method and arguments
revision_before: observed state revision
revision_after: state revision after acknowledgement
before: native structured state
after: native structured state
status: succeeded, failed, rejected, or uncertain
verification: native return data and independent checks available at this step
artifacts: paths and hashes of files or images produced
started_at: UTC timestamp
finished_at: UTC timestamp
```

Raw step records are evidence. A reusable procedure is derived from multiple
records only after its applicability and invalidation conditions are reviewed.

## Implementation order

1. Shared session coordination, revisions, step records and local JSON-RPC.
2. Gmsh native-cooperative Bridge.
3. CalculiX batch job service.
4. CGX controlled process and explicit GUI fallback.
5. [x] MCP exposure and live application-level handoff demonstrations.
