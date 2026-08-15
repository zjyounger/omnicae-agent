# Register of the agent's own failure modes

`GAPS.md` records where the tools mislead their operator. This file records
where the operator misleads itself. It is written by the agent, about the
agent, for the next agent.

It exists because of an asymmetry. A coding mistake announces itself: the thing
does not work. An engineering mistake announces nothing — it produces a number,
a contour, and a paragraph of confident prose, all of which look exactly like
the correct version. Every entry below is a way of arriving at a wrong belief
while feeling no different than when arriving at a right one.

**A resolution does not survive a session boundary. Only artifacts do.** So a
countermeasure here is a script, a required field in a table, or a captured
log — never "be careful about this". The whole point of writing it down is that
the next agent starts with no memory of having failed, and being told to try
harder is worth nothing to it.

Each entry needs evidence from this repository, not an impression.

---

## F0 · The root: plausibility is produced faster than it is tested

Every specific failure below is a variant of one thing. Generating a coherent
account — a mechanism, a deck, a set of numbers, an explanation of a
discrepancy — is nearly free, and generating a *correct* one feels identical
from the inside. The output is fluent either way. Nothing in the act of
producing it signals which kind it is.

This is not a knowledge problem, and more care does not fix it. Fluency is the
capability; the failure is the same capability running unchecked. Which means
the correction cannot come from inside the generating step. It has to come from
an artifact outside it — a measurement, a file on disk, a second independent
route to the same number.

**The operational rule: the confidence felt while writing a sentence carries no
information about whether the sentence is true. Discount it to zero and go and
look.**

---

## F1 · A hypothesis becomes a finding the moment it is written down

**What happens.** A plausible mechanism is proposed to explain an observation.
It is recorded in prose. In the next session — or the next paragraph — it is
read back as established fact, and the investigation that would have tested it
never happens, because the question now looks answered.

**Evidence.** `GAPS.md` G2 carried this explanation of the 11.8% load
shortfall:

> The consistent load vector of a quadratic tetrahedral face is zero at the
> corner nodes … and the area weighting appears to lose the balance there.

Three things were wrong with that. The corner-zero weighting is not a defect —
for a 6-node face it sums to exactly the face area. "Appears to" was doing the
work of a measurement that had not been made. And the real cause was somewhere
else entirely (see G2 as it now stands). The entry was hedged enough to be
honest and confident enough to close the question, which is the worst
combination: it stopped the search without settling anything.

The actual cause was found later from `FemMesh.inp` and `meshtools.py` — both
of which had been sitting in the repository, unchanged, the whole time. Nothing
new was needed. The investigation had simply been called off early by a
sentence that sounded like a conclusion.

**Countermeasure.** Every causal claim carries its grade:

| Grade | Means |
|---|---|
| **observed** | I read this off an artifact; here is the number and the file |
| **derived** | it follows from something observed, and here is the step |
| **hypothesised** | it would explain the observation, and **here is the test that would kill it** |

A hypothesis without its discriminating test does not go in a document. The
words "appears to", "presumably", "likely because" are the tell — where they
occur, the grade is *hypothesised*, and the test is missing.

---

## F2 · Silence is read as success

**What happens.** No error message is taken as evidence that the intended thing
happened. It is only evidence that nothing raised.

**Evidence.** G1: a force on a cylindrical face wrote a `*CLOAD` block
containing a comment and no node loads. Exit code 0, a result file was
produced, results loaded, contours drew. Every displacement was zero. Every
component of the toolchain reported success.

**Countermeasure.** State beforehand what the artifact must contain if the step
worked — a node count, a resultant, a set that is not empty — then read the
artifact for it. `tools/inspect_deck.py` exists for exactly this. **"The program
ran" is not evidence** is rule 3 in `AGENTS.md` because of this failure.

---

## F3 · Internal consistency is mistaken for external correctness

**What happens.** A check is run that the model passes by construction, and its
passing is taken as validation of something it cannot see.

**Evidence.** Bracket case, A3 and A4. Applied load and total reaction agreed to
seven digits — equilibrium was exact. It is also *unfalsifiable*: the solver
enforces it. Meanwhile the applied load was 11.8% below what had been asked
for. The most commonly cited check in FEA could not see the error, and its
passing was reported alongside the failure without noticing the tension.

**Countermeasure.** For every check, ask what result would have failed it. If
nothing realistic would, it is not a check. **Verify against intent, not
against the model's own bookkeeping** — deck load versus the load requested,
not deck load versus reaction.

---

## F4 · The host's own diagnostics go unread

**What happens.** The tool detects the problem, says so in plain language, and
nobody is listening on that channel.

**Evidence.** The sharpest failure on record here. FreeCAD's
`femmesh/meshtools.py` checks the very thing that was wrong and prints it:

```
Deviation sum_node_load to frc_obj.Force is more than 1% :  0.88207
  the reason could be simply a circle area --> see method get_ref_face_node_areas
```

That is the answer to a question that then stayed open across sessions. It was
printed to the FreeCAD console at the moment the deck was written. The Bridge
does not capture the host's console output, so it never reached the agent, and
nobody asked why not.

**Countermeasure.** Enumerate the channels a tool can speak on — stdout, the
GUI report view, a log file, a return code, a file on disk — and confirm each
one is actually being read *before* concluding a tool said nothing. Silence on
a channel nobody is listening to is not silence. Capturing FreeCAD's console in
the Bridge is now an open item; until it lands, read the report view directly
after any write or mesh operation.

---

## F5 · A capability is declared absent from recall instead of from enumeration

**What happens.** "This cannot be done" is produced from what the model
remembers about the tool, rather than from an inventory of what is installed.

**Evidence.** G9, since retracted. Results were declared unplottable through the
Bridge, and a gap entry was written arguing it. CalculiX's own post-processor
`cgx` was installed at `/usr/bin/cgx` and named in the first paragraph of this
repository's own CalculiX notes. The claim was refuted by a file that the
project had already documented.

**Countermeasure.** Before writing that something is impossible: list what is
installed, and read this repository's own notes on it. Rule 7 of `AGENTS.md`.
Note the shape — the correction was available *locally and for free*, as in F1
and F4. That is the pattern: the answer is usually already on disk.

---

## F6 · The idealisation is not audited against the question

**What happens.** The model gets built, meshed, and solved before anyone checks
whether it is capable of answering the question that motivated it. Each
individual modelling decision is defensible; the composition of them silently
removes the load path the question was about.

**Evidence.** Bracket case, A8. The stated question 2 was *how much load each
bolt carries* — the question that decides bolt selection. The base plate was
restrained at the four bolt holes and nothing represented the base it sits on,
so the plate-to-base compressive path — which in reality carries most of the
overturning moment — was absent. The whole moment was forced through four hole
walls instead. The bolt loads therefore could not be answered by that model at
all, and this was discovered after a 49k-node mesh had been solved and the
results read.

**Countermeasure.** Before meshing, write the question down and trace the load
path that answers it through the model as configured. Name the path. If it
cannot be named, the model does not answer the question, and no amount of mesh
refinement will change that. This belongs in `DEFINITION.md` §1 *before* §4, not
in the assumption register afterwards.

---

## F7 · Reported precision exceeds established precision

**What happens.** A solver returns many digits and they are carried into the
report, where the number of digits implies a discretisation error that was
never estimated.

**Evidence.** Bracket case: `33.65 MPa` reported to four significant figures,
alongside A6 — "mesh has converged: **not assessed**" — in the same document.
Two digits of that number are unsupported. The load feeding it was also 11.8%
wrong at the time.

**Countermeasure.** A number gets as many digits as the coarsest step in the
chain supports. With no convergence study, that is one or two. Where the error
bar is unknown, write the number with the missing study named beside it, as
`~34 MPa (no convergence study; discretisation error unknown)`.

---

## F8 · Recall substitutes for reading exactly where the corpus is thin

**What happens.** Confidence is uniform across tools, but accuracy is not. It
tracks how well each tool is represented in training data, and that correlation
is invisible from the inside.

**Evidence.** Measured in G5. Nearly every API-level error in the first FEM
session was on the CalculiX side, where no documentation was installed; the
FreeCAD side was mostly right first time. Reading one `*PRE-TENSION SECTION`
card then corrected two things recall would have got wrong, one of which fails
*silently* (a pre-tension surface adjacent to quadratic contact faces raises no
error and produces spurious stress concentrations).

**Countermeasure.** CalculiX keywords are written by reading the card in
`knowledge/calculix/` — every time, including the ones that feel familiar.
Where no local corpus exists for a tool, treat every recalled detail as
*hypothesised* under F1.

---

## F9 · A countermeasure is treated as free

**What happens.** A fix for one problem is adopted as a default, and its own
side effects are never registered — because it is filed as a solution, and
solutions are not looked at again.

**Evidence.** G3's countermeasure was `SecondOrderLinear=true`, which stops
Gmsh projecting mid-side nodes onto curved geometry and cures the nonpositive
jacobian. It is also, on present evidence, the cause of G2: straightening a
mid-side node on a *concave* boundary edge moves it off the face and into the
hole, so FreeCAD's face-node query no longer returns it, so the element face is
one node short, so its area — and the load on it — is silently dropped. The
loud failure was traded for a quiet one, and the trade was recorded as a clean
win in the same document that carried the unexplained shortfall.

**Countermeasure.** When a workaround is adopted, write what it changes
*besides* the symptom, and where that would show up. A countermeasure gets an
entry, not just a status of `filled`. Rule 5 of `AGENTS.md` — anything changed
to isolate a problem gets a second look — applies to fixes that worked, not
only to ones that did not.

---

## F10 · The session pulls toward narrative closure

**What happens.** Work tends to end on a result, because a result reads as
completion. This biases against the two most valuable honest endings: *this
explanation is dead* and *this number cannot be trusted yet*.

**Evidence.** The bracket case was carried to a reported peak stress, a safety
factor and a hand-calculation cross-check while A3 (load 11.8% wrong), A6 (no
convergence study) and A8 (missing load path) were all open and known. The
document is honest about each — and still concludes with a number, because the
shape of a finished analysis demands one.

**Countermeasure.** `AGENTS.md` already states it: a run that yields a number
and changes nothing is no progress; a run that yields no number and rules out an
explanation is progress. In practice — when a report is about to end on a
figure, check whether any open assumption feeds it. If one does, the figure is
not the conclusion; the open assumption is.

---

## What actually works

Ranked by what has caught real errors in this repository:

1. **Reading the artifact instead of the intention** — the deck, the `.frd`,
   the node coordinates. G1, G2, G4 and A7 were all caught this way, and G2's
   root cause came entirely from files already on disk.
2. **Two independent routes to the same number.** Deck sum against solver
   reaction; FEA stress against a beam hand-calculation. Where they agree,
   confidence is earned; where they agree *by construction*, see F3.
3. **A script rather than an inspection.** `tools/inspect_deck.py`,
   `inspect_frd.py`, `check_face_load.py` — each was written after the second
   time the same check was needed by hand, and each now runs in seconds against
   any case. A script survives the session; an intention does not.
4. **The assumption register with an invalidation condition.** Forcing "this
   stops holding when X" makes A7 and A8 findable at all.

What does not work: resolving to be careful, longer checklists that must be
applied by the same judgment that just failed, and re-reading one's own prose
for errors. The prose is the output of the process that made the mistake, and
it reads as correct from the inside — that is F0, and it is why the checks have
to live outside the writing.
