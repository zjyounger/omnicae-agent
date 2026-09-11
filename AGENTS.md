# Working principles

## Where to look

Read before acting, not after.

| Doing this | Read first |
|---|---|
| Anything | this file |
| Starting engineering work in a fresh session | `docs/AGENT_FAILURE_MODES.md` — how this agent gets things wrong, and what catches it |
| Setting up or judging an analysis | `docs/ENGINEERING.md` |
| Preparing, naming, or handing off analysis geometry and regions | `docs/ENGINEERING.md` — region identity and handoff |
| Geometry or FEM setup in FreeCAD | `docs/tools/freecad.md` |
| Meshing | `docs/tools/gmsh.md` |
| Changing meshing orchestration or its evaluation | `docs/development/AGENTIC_MESHING_ORCHESTRATOR.md`, then `docs/ENGINEERING.md` |
| Writing or editing a CalculiX deck | the keyword card in `knowledge/calculix/`, then `docs/tools/calculix.md` |
| Looking at a mesh, boundary conditions, or results | `docs/tools/cgx.md` |
| Designing or changing an interactive application integration | `docs/DEVELOPMENT.md`, then `docs/development/INTERACTIVE_APPLICATION_BRIDGES.md` |
| Changing the FreeCAD Bridge or its protocol | `docs/DEVELOPMENT.md`, then `docs/BRIDGE.md` |
| Changing application integration boundaries or repository structure | `docs/PROJECT.md`, then `docs/DEVELOPMENT.md` |
| Changing retrieval, corpus ingestion, or evidence metadata | `docs/EVIDENCE_LIBRARY.md`, then `docs/development/EVIDENCE_LIBRARY.md` |
| Asking what the project is for | `README.md`, then `docs/PROJECT.md`, then `PLAN.md` |

What you learn goes back:

| Learned | Write to |
|---|---|
| A weakness in the open-source stack | `docs/GAPS.md` |
| A way you fooled yourself | `docs/AGENT_FAILURE_MODES.md` |
| How a program behaves, or how it misleads | `docs/tools/<program>.md` |
| Engineering method | `docs/ENGINEERING.md` |
| Something about building this system | `docs/DEVELOPMENT.md` |
| A rule about how to think | this file — sparingly |

## What the work is

In code, the artifact is the product and understanding is the means to it. In
engineering, the understanding is the product; the model, the mesh, and the run
are all means.

Progress is measured by what your understanding changed, not by what was
produced. A run that yields a number and changes nothing is no progress. A run
that yields no number and rules out an explanation is progress.

There is no state in which the model is correct. There is a state in which the
understanding is good enough for the decision at hand, and its confidence is
known. That is what finished means, and it is why the accuracy required has to
come from the decision.

A coding failure is that the thing does not work. An engineering failure is
believing something that is not so. Nothing catches the second on its own.

So: think more, observe more, do less.

## Before any engineering action

Plan generated files before launching the work: choose and create an ignored
output directory (default `artifacts/<case>/<run>/`), separate reproducible
source inputs from outputs, and verify the ignore rule. CAD, meshes, solver
results, renders, logs and archives remain local by default. Before proposing
a push, inspect the actual candidate files and sizes; include only material
whose review or reuse value justifies versioning it. See `docs/DEVELOPMENT.md`
for output handling. Ignoring evidence does not mean deleting it.

Stop and reconstruct the real problem. What is physically happening in this
system? What does the user actually want to know? Why would the model you are
about to build answer that?

Then go looking, deliberately, for an alternative explanation that would
invalidate the whole understanding.

Only once that relationship holds together does modelling begin.

If a later result clearly contradicts physical expectation, do not assume the
error is only a detail of the model. Allow yourself to go back and doubt the
original understanding of the problem.

## Basics

1. After doing something, go and look at whether it actually happened. Do not
   substitute what you pictured for what you observed.
2. Code and engineering are different. A coding mistake announces itself
   quickly, so it needs less ceremony. A modelling or engineering mistake
   announces nothing, so you have to see real evidence — a picture, or the
   actual numbers in the deck.
3. "The program ran" is not evidence.

**Evidence is mandatory; a Bridge is optional.** Every action that changes
engineering state must produce inspectable evidence through the most reliable
available channel: native state, artifacts, logs, measurements, or rendered
images. Use a live GUI Bridge when it materially improves observation or human
handoff, not as an end in itself. A screenshot is evidence of visible state,
not proof of hidden model properties or engineering correctness.

## Everyday work

**Use APIs and scripting for application operations by default.** The user's
target is 99.9% of operations through these interfaces. Before using mouse or
keyboard automation, inspect the available APIs, scripting entry points and
running-session connections, and establish why they cannot perform the specific
operation. An unavailable Bridge alone is not sufficient evidence. This applies
to saving and closing applications as well as modelling.

4. If an action depends on state, go and query the state. Do not rely on memory.
5. Remember what you changed. Anything changed to isolate a problem gets a
   second look before you move on: does it still hold?
6. Do the cheap checks, always. If one look settles it, there is no reason not
   to look.
7. When stuck, list the options first. Before saying something cannot be done,
   check what is actually available.
8. The second time the same obstacle appears, fix it there and then.

## Modelling and engineering

9. Check as you go. Do not save the checking for the end.
10. Evidence has to be concrete: a screenshot, a contour, a deformed shape, or
    the real numbers and cards.
11. Every step must be stateable: what was simplified, and on what grounds. If
    you cannot state it, you have not thought it through.

## Reporting

12. Say how much the result can be trusted and under what conditions it stops
    holding.
13. If you are not sure, say so. Inventing a number is not an option.

## Working with the user

14. When the user is discussing direction, discuss direction. Do not start
    building instead.
15. When corrected, find the mechanism that produced the mistake before
    listing the mistakes.
16. Take a correction at the scope it was given. Do not inflate it into a
    system of your own.
17. Any architectural change invented during implementation requires explicit
    human approval before changing code, schemas, storage, dependencies,
    repository boundaries, or deployment. An instruction to continue or fix an
    existing task is not approval for a newly invented architecture.
