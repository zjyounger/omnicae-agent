# Engineering method

How to run an analysis so that the answer can be trusted. General method only —
program-specific behaviour is in `docs/tools/`.

Incomplete by design. What is written here has been exercised at least once and
is described from that evidence. What has not is listed at the end rather than
invented.

## The chain

An analysis is a chain of steps from an engineering question to a number. There
is no oracle at the end that tells you the chain was sound, so each link has to
carry its own evidence. What follows is what to look at, link by link.

### Problem

State the engineering question, the failure mode it concerns, and the decision
it supports. State the accuracy that decision needs — a pass/fail check against
an allowable is a different job from a life prediction.

### Idealisation

Write down every simplification and, with each one, the condition that would
invalidate it. See "assumption register" below. Simplifications made silently
cannot be checked afterwards.

### Geometry

Check dimensions and volume against what they should be. Check it is one solid
where you expect one solid.

### Mesh

Look at it. Check refinement where the answer is going to come from, not
uniformly. Check element count through a thickness that will carry bending.

A run that dies on element quality is the loud failure. The quiet one is a mesh
too coarse where the stress gradient is.

### Material and units

Fix the unit system before anything else and state it in the case definition.
mm–N–MPa–t is the usual choice with CalculiX. Write units on every dimensional
quantity rather than relying on a program's internal defaults.

### Boundary conditions and loads

**Read them back from the solver deck, not from the CAD model.** A constraint
that attached to nothing is indistinguishable from one that worked, until you
count nodes.

For each set: node count, coordinate extent, and the degrees of freedom
constrained. For each load: the resultant, compared against what you intended.
`tools/inspect_deck.py` does this.

Then look at the picture. Constraint symbols and load arrows show placement
mistakes that a coordinate range does not — a load on the right face pointing
the wrong way, or on the right surface at the wrong height.

Check the model is neither free to move as a rigid body nor clamped so heavily
that it invents stiffness.

### Solve

Read the convergence record and the solver's own error lines, not just the exit
status.

### Results

**Look at the deformed shape before looking at any stress number.** Wrong
boundary conditions, a reversed load, and disconnected bodies are obvious there
and nowhere else.

Then:

- Reaction against applied load. Note that this pair is not independent of each
  other — they can both be wrong in the same way — so it does not substitute for
  checking the applied load against intent.
- **Where is the peak.** A peak sitting on a constrained node, a re-entrant
  corner, or a point load is an artefact: it grows without bound as the mesh is
  refined and is not a strength result.
- Magnitudes against a hand calculation or a known solution, where one exists.

### Assumption recheck

Go back through the register and test each invalidation condition against the
result. Report the ones the result has overturned. This is the step that
converts "the run completed" into "the answer holds under stated conditions".

## Assumption register

Every simplification carries a machine-checkable condition that would break it.
Written before solving, checked after.

| Simplification | Invalidated when |
|---|---|
| Linear elastic | peak stress reaches yield |
| Small deformation | displacement / characteristic length exceeds a few percent |
| Quasi-static | kinetic energy / internal energy is not negligible |
| Frictionless | required tangential/normal ratio exceeds the assumed μ |
| Joint stays closed | contact opens anywhere |
| 2D or axisymmetric | loading or restraint varies around the axis |
| Threads not modelled | the question involves fatigue or thread-root stress |

The register serves twice: as the problem statement a person signs off, and as
the check list the machine executes.

Terminology follows ASME V&V 10 / V&V 20 rather than inventing its own.

## Working order

Confirm the cheap upstream links — geometry, units, boundary conditions, load
magnitude — before spending time on the expensive downstream ones. Refining a
mesh while the applied load is wrong buys nothing.

Start from a model whose answer is already known and add one complication at a
time. A first analysis with no reference to check against gives no way to tell a
tool problem from a modelling problem.

## Not yet written

These need to come from practice, not from reasoning:

- Mesh convergence: how many levels, what to monitor, when the study is enough.
- Acceptance tolerances per problem class — what deviation from a reference is
  acceptable for what kind of decision.
- Which quantities matter and which are noise, per problem class.
- When a coarse answer is sufficient and when it is not.
- Contact and pre-loaded joints: procedure and checks.
- Handling of assembly scatter and other real-world variability.
