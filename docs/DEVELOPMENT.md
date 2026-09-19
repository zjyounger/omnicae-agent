# Development notes

What building an agent-facing adapter for a large host application has taught
us. General lessons only — quirks of a particular program belong in
`docs/tools/`, engineering method in `docs/ENGINEERING.md`.

## Integration organisation

**Own integrations by application; describe them by capability.** Compatibility,
deployment, failure modes, and tests belong to FreeCAD, CalculiX, Gmsh, or
another concrete application. Categories such as CAD, FEA, CFD, meshing, and
post-processing overlap and should be discoverable manifest fields rather than
directory ownership.

**Not every integration is a Bridge.** A host application with an internal
runtime may need an in-process Bridge. A command-line solver may instead need a
runner, input reader, result reader, and inspectors. `integration` is the
general boundary; `bridge` is one implementation pattern inside it.

**Every integration has an action contract and an evidence contract.** The
action contract says what the integration can change. The evidence contract
says how the caller observes the resulting state and what independent checks
are available. Native state queries, exported artifacts, logs, measurements,
and rendered images can satisfy that contract without a live GUI Bridge. Use
the least complex interaction level that preserves adequate evidence and any
required human handoff.

**Keep integrations together until independence is real.** The monorepo is the
right default while contracts and shared tests are changing. Split an
integration only in response to a concrete independent release cycle,
maintainer, licence, dependency footprint, or stable plugin boundary.

## Interface design

**A generic channel beats a domain wrapper.** Rather than one method per object
type, provide one channel that can list, read, and write any object's
properties. When the host changes, hardcoded per-type wrappers fail together; a
generic channel does not.

**Let the adapter be interrogated.** Return the new object's property list from
the call that creates it, so the client discovers what it can set. A
self-describing interface cannot drift from its implementation the way
documentation does.

**Ask the live object for property names; do not read them out of the source.**
Source can be the wrong version. The running object cannot.

**Drive every consumer from one contract registry.** A single method table
feeding the dispatcher, capability discovery, and the external tool list turns
any omission into a startup failure rather than a runtime surprise.

**Accept units as part of the value.** A bare number is interpreted in the
host's internal units, which are frequently not the ones the caller meant. Take
`"5000 N"`, let the host parse it, and get validation for free.

## Living inside the host process

**An in-process adapter has to reload itself.** Otherwise every code change
costs a host restart, and every restart discards whatever the user had not
saved. The longer this is deferred the more it costs, while any single restart
always looks cheap.

**Make reload fail safe.** Reload the modules first and only swap the server if
every import succeeded; if the new code is broken, let the old one keep serving.
A typo must not be able to leave the host with no adapter at all.

**A GUI host re-enters its event loop.** Anything that pumps events can deliver
the next request midway through the current one, and can destroy objects that
are still in use. Keep a re-entrancy depth: dispatch nothing new while inside a
request, and defer object destruction until the stack unwinds.

**The host's error paths are often untravelled.** A stable main path says
nothing about the exception branches. Wrap calls into the host so that a bug in
the host cannot take the adapter down with it.

## Failure handling

**A failure should arrive as a diagnosis, not an exception.** A solver that
fails is ordinary operating data. Return structured status and the extracted
error lines so the caller can act on them; raising throws that information away.

**Do not return internals to the client, but do print them to the host
console.** Untrusted callers get a structured error. Debugging without a
traceback anywhere is guesswork.

**Host diagnostics are part of the operation result.** The FreeCAD Bridge
measures the Report View before and after each request and returns the delta on
both success and failure. This catches diagnostics emitted below the adapter,
including messages from FEM deck writers, without replacing FreeCAD's own
console functions.

## Verification tooling

### Generated CAE files

Choose the output location before running CAD, meshing, solving or rendering.
Create `artifacts/<case>/<run>/` for new workflows and check it with
`git check-ignore`; pass that location explicitly through the application's
output option or working directory. Keep source scripts and authored input
decks outside it. Existing mixed case directories have ignore rules in place;
do not move their files without updating and checking dependent paths.

Native models, exported geometry, meshes, solver results, generated region
catalogues, reports, screenshots, animation frames, videos, logs and archives
stay local by default, regardless of whether their format is binary or text.
Retain the evidence and reproducible instructions locally. A tracked document
linking to local evidence must say that those files require regeneration or
access to the local archive; a fresh clone will not contain them.

Before proposing a push, inspect the candidate paths, diff and sizes. Reusable
source, problem definitions and general engineering lessons normally justify
versioning; large reproducible outputs do not. Small, deliberate benchmark
fixtures may justify an explicit exception after review. Do not bypass ignore
rules with `git add -f` merely to make an example look complete.

An ignore rule does not affect files already tracked. When removing generated
files from version control, use `git rm --cached` on the reviewed file list,
verify that local copies remain, and do not rewrite history as part of cleanup.

**Verification tools need verifying too.** Both deck inspectors written here had
parsing bugs, and one of them nearly produced a false report that a load set was
empty. **A wrong verification tool is worse than none**, because it manufactures
confidence. Run a new tool against an input whose answer is already known.

## Long-lived stateful processes

**Save before any restart.** Intermediate state that was expensive to produce —
a mesh, a solution — is costly to rebuild, and the decision to restart is
usually made on the spur of the moment.

**Do not kill processes by a pattern that also matches you.** Your own shell is
in the search space. Resolve the PID, then kill the PID.

## Cooperative GUI sessions

Use this pattern only when persistent application state or live human handoff
adds value beyond an observable batch or command interface.

**Automation is not a Bridge.** A command-line switch, generated macro, or
keyboard event can automate an application without providing live state,
acknowledgement, concurrency control, or recovery. Declare the actual
interaction level instead of promoting every automation route to a native API.

**One action needs an observation barrier.** Read native state, perform one
operation, wait for the application, then read state again. Return both states
with the exact operation. Without the second observation, "the key was sent" is
being substituted for "the model changed".

**Human handoff is a write-ownership change.** A persistent GUI can be shared
only if there is one writer. Every mutation carries an actor and expected state
revision. Human activity observed between agent steps advances the revision and
invalidates stale commands.

**Run host APIs on the host's GUI thread.** The Gmsh Bridge owns the official
Python API and calls fltk.wait() on the main thread while socket readers place
requests on a serialized queue. This gives human GUI events and agent API calls
one ordering instead of racing two threads through the model.

**A GUI fallback remains weaker after careful wrapping.** Exact PID/window
binding, an exclusive lease, console deltas, and before/after screenshots make
CGX keyboard control diagnosable. They cannot reveal all hidden application
state or guarantee that a person did not press a key simultaneously. The
contract therefore returns gui-fallback, never native-cooperative.
