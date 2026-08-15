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

## Verification tooling

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
