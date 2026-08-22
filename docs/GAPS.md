# Register of gaps in the open-source stack

This is why the project exists: find the places where open-source CAE trips
people (and agents) up, record them, and fill them.

Every entry needs **evidence**, not an impression. The column that matters most
is **whether it fails silently**. A problem that raises an error is an
inconvenience; a problem that returns a plausible answer instead is the
dangerous kind, and it is the principal risk in agent-driven CAE.

Status: `filled` — worked around or fixed here | `recorded` — known, with a
countermeasure | `open` — unresolved.

---

## G1 · A force on a cylindrical face silently applies nothing ⚠️ silent

**What happens.** When FreeCAD FEM's `ConstraintForce` references a cylindrical
face, the `*CLOAD` block it writes contains a comment and no node loads.
CalculiX exits normally, the `.frd` is produced, FreeCAD loads the results, and
everything reads as success — but every displacement and stress is zero.

**Evidence** (bracket case in this repository):

```
*CLOAD
** node loads on shape: Bracket:Face12      <- the face was found
                                            <- and not one node load followed
```

Moving the same constraint to the planar `Face16` produced 486 node loads
immediately.

**Why it is dangerous.** The textbook quiet wrong answer: exit code 0, a result
file, a contour that draws — all zero. An unguarded workflow takes it as valid.

**Countermeasure.** Before solving, check that the node loads in the deck sum to
the intended load. This check is now in the case's assumption register.

**Status:** open (in FreeCAD) / recorded (catchable by a check)

---

## G2 · Distributed force totals 11.8% less than requested ⚠️ silent

**What happens.** A 5000 N request produced node loads totalling 4410.35 N.

**Evidence.** Two independent sources agree on the shortfall:

- summing the `*CLOAD` values in the deck: 4410.349 N
- CalculiX's total reaction at the bolt holes: −4410.349 N (equilibrium itself
  is exact)
- reading the property back: `Force = 5.0e6` internal units = 5000 N

**Root cause — found, and it is not what this entry first claimed.** The
earlier explanation (corner-node weighting losing the balance) was wrong: for a
6-node face the weighting sums to exactly the face area. The real chain is
mechanical, and every step is measured from `cases/bracket_static/solve/FemMesh.inp`
by `tools/check_face_load.py`:

FreeCAD spreads a face force by area-weighting the *mesh* faces lying on the
reference face, then scaling by the *CAD* face area
(`femmesh/meshtools.py`, `get_force_obj_face_nodeload_table`):

```
Σ node loads = (mesh facet area counted) × Force / (CAD face area)
```

| Quantity | Value | How known |
|---|---|---|
| CAD face area, π(25²−15²) | 1256.637 mm² | analytic |
| **True mesh surface, 224 faces** | **1256.619 mm²** | cgx `enq`+`send abq sur`, and a 1 MPa pressure run whose reaction is 1256.619 N |
| Mesh facet area FreeCAD counted (200 faces) | 1108.442 mm² | summed from the deck |
| Silently dropped (24 faces) | 148.178 mm² | difference, face by face |

```
0.882070 = 1108.442 / 1256.637   (counted mesh area / CAD area)
```

exactly the observed 4410.349 / 5000 = 0.882070. **The whole 11.79 % is dropped
faces.** Chord faceting contributes essentially nothing here: on an annulus the
inscribed outer polygon loses area and the inscribed inner polygon gives it
back, so the true faceted surface is within 0.0014 % of the analytic area.

> An earlier version of this entry split the shortfall as
> `(1 − 10.95 %) × (1 − 0.95 % faceting)`. That was wrong — it was derived from
> an incomplete face list (222 of the 224 faces) reconstructed from the deck
> alone, and the residual was attributed to faceting without measuring it.
> The pressure-reaction test settled it. See `AGENT_FAILURE_MODES.md` F1; this
> is the second instance of the same habit in two days.

The defect itself:

1. `SecondOrderLinear=true` (this repository's G3 countermeasure) puts each
   mid-side node at the **chord midpoint** instead of on the curved geometry.
2. On the **concave** inner boundary — the Ø30 bore — that point falls
   *outside* the annulus. The absent mid-side nodes sit at exactly
   r = 14.871673 mm = 15·cos(7.5°), i.e. inside the hole. On the convex outer
   boundary the same straightening moves nodes *into* the face (r = 24.923),
   so they are still found and nothing is lost there.
3. `femmesh.getNodesByFace()` therefore does not return them. Of the **512**
   mesh nodes that lie on the annulus (cgx finds them all with one `enq` on
   z = 72), FreeCAD's set has **486**.
4. `get_ref_facenodes_areas()` branches on the node count of each face and
   handles only **3, 4, 6 and 8**. The 224 real surface faces land as:

   | Nodes present | Faces | Area | Fate |
   |---|---|---|---|
   | 6 | 200 | 1108.442 mm² | weighted correctly |
   | 5 | 22 | 136.243 mm² | falls through every branch — nothing appended |
   | 3 | 2 | 11.935 mm² | hits the 3-node branch, but the three surviving nodes are collinear, so the triangle area is 0 |

   The same collinearity is why the 220 elements that merely touch the face
   with an edge do no harm: they too are read as degenerate triangles. The
   defect is not that unhandled cases are dropped loudly — it is that both the
   dropped and the degenerate cases return silently.

**Scope.** Any face force whose reference face is bounded by a hole, wherever
the boundary is curved and the mesh is second-order-linear. That is the common
case: washer faces, bolt-hole faces, bore end faces. The loss scales with hole
perimeter relative to face area, so it is **worst on small annuli**.

**Why it is dangerous.** The equilibrium check **passes**: applied equals
reaction. The most commonly used check cannot see this. Only comparing the deck
against **intent** reveals it. And FreeCAD *does* detect it — `meshtools.py`
prints `Deviation sum_node_load to frc_obj.Force is more than 1% : 0.88207`
together with the hint `the reason could be simply a circle area`. That message
goes to the FreeCAD console, which the Bridge does not capture, so it never
reached the agent. See S5 below and `AGENT_FAILURE_MODES.md` F4.

**Countermeasures.**

- Check "deck load vs the load that was asked for", never "deck load vs
  reaction". `tools/check_face_load.py <deck> <intended N>` reports the ratio
  exactly, and the dropped faces as a **lower bound** — working from the deck
  alone it can only see faces whose corner nodes are all in the load set, so it
  found 222 of the 224 faces here. The remaining two are invisible without the
  geometry.
- **Define the loaded surface in cgx instead.** `enq` selects the nodes by
  coordinate, `comp <set> f` completes the element faces, and
  `send <set> abq sur` writes a proper `*SURFACE`. On this model that recovers
  all 224 faces, and a 1 MPa pressure run returns a reaction of 1256.619 N
  against an analytic 1256.637 mm² — 14 ppm, versus FreeCAD's 11.8 %. This is
  the route that works today; see `tools/cgx.md` and
  `cases/bracket_static/cgx_proper/`.
- Where the load is **normal** to the face, use a pressure constraint instead.
  `write_constraint_pressure` emits `*DLOAD` per element face
  (`elem,P<n>,value`) and never touches the node-area table, so it is immune by
  construction. It cannot represent a tangential load.
- Upstream fix: `get_ref_facenodes_areas()` must not silently ignore an
  unhandled node count, and `get_ref_facenodes_table()` should keep the
  boundary mid-side nodes of the face.

**Untested prediction, for whoever picks this up:** with
`SecondOrderLinear=false` the inner-circle mid-side nodes lie exactly on r = 15,
should be returned by `getNodesByFace`, all 222 faces should be weighted, and
the ratio should rise to ≈ 0.99. That experiment would confirm the link to G3 —
and would have to be run against G3's jacobian failures.

**Status:** root cause identified and reproduced offline; worth reporting
upstream. Not yet fixed in FreeCAD, and the workaround (pressure, or the
deck check) is what protects a run today.

---

## G3 · Second-order tetrahedra invert on small features ⚠️ loud

**What happens.** Gmsh projects mid-side nodes onto the curved geometry by
default; on small fillets, grooves, and intersecting holes this inverts
elements. CalculiX reports `*ERROR in e_c3d: nonpositive jacobian`, exits 201,
and writes a `.frd` containing a mesh and no results.

**Evidence.** The bracket (R3 retaining-ring groove, Ø12 cross hole) fails every
time at a uniform 6 mm; it disappears with `SecondOrderLinear=true` at 4 mm.

**Countermeasure.** Take `SecondOrderLinear=true` as the default starting point
for second-order solid meshes.

**⚠️ This countermeasure is not free.** Straightening the mid-side nodes is what
causes G2: on a concave boundary the straightened node falls outside its face
and the element face's load is silently dropped. A loud failure was traded for a
quiet one. Any mesh carrying `SecondOrderLinear=true` and a face force must be
checked with `tools/check_face_load.py`.

**Status:** filled for the jacobian failure; see G2 for what it costs

---

## G4 · Bare numbers on dimensional properties use internal units ⚠️ silent

**What happens.** FreeCAD's internal units are mm–kg–s, so force is
kg·mm/s² = mN. Assigning `5000` to a force property gives **5 N**, not 5000 N,
with no error.

**Evidence.** `Force = 5000` → deck total 4.41 N. `Force = "5000 N"` → internal
value 5.0e6 → deck total 4410 N.

**Why it is dangerous.** Inconsistent units are the number one real-world CAE
error, and this is a silent factor of 1000.

**Countermeasure.** The Bridge property API now accepts unit-bearing strings
(`"5000 N"`), which FreeCAD parses and validates. **Convention: always write the
unit.**

**Status:** filled

---

## G5 · The CalculiX package ships no manual

**What happens.** Ubuntu's `calculix-ccx` installs a changelog and a copyright
file and nothing else. `gmsh-doc` ships a complete PDF.

**Why it matters.** This decides whether an agent writes keywords by reading or
by recalling. CalculiX keywords are low-frequency, differ between versions, and
a wrong one often fails silently — G1 and G2 are exactly that kind of failure.

**Countermeasure.** `knowledge/calculix/` now holds the official ccx 2.23 HTML
manual (534 pages, 143 keyword cards indexed in `keyword_index.txt`). HTML
rather than PDF because it is searchable. Note the version spread: the system
`ccx` is 2.21, FreeCAD bundles 2.23, and the manual is taken at 2.23.

**Measured benefit.** Reading the `*PRE-TENSION SECTION` card corrected two
things recall would certainly have got wrong: (a) the `ELEMENT` parameter lets a
single B31 beam element represent an entire bolt; (b) a pre-tension surface must
not be adjacent to quadratic elements whose faces belong to a contact surface —
violating that raises no error, it produces spurious stress concentrations.

**Update — the same is true of cgx, and worse.** Its man page refers to a
`calculix-cgx-doc` package that **does not exist** in the Ubuntu archive; only
`calculix-cgx-examples` does. The official 2.23 manual (218 commands) is now in
`knowledge/calculix/CalculiX/cgx_2.23/`, indexed by `cgx_command_index.txt` and
readable with `tools/cgxdoc.py`. This paid for itself immediately: `enq`'s
coordinate selection, `comp <set> f`, and the `send … abq sur` / `nam` / `spc`
forms are all positional and none of them are guessable — and they are what
makes a properly-defined deck possible at all (G2 countermeasure).

**Status:** filled (first body of source material)

---

## G6 · FreeCAD FEM does not support bolt pre-tension

**What happens.** There is no `PRE-TENSION` anywhere in the Fem module. The ccx
writer covers fixed, displacement, force, pressure, contact, tie, rigid body,
section print, self weight, centrif, transform and plane rotation — not
pre-tension.

**Impact.** A pre-loaded bolted joint — one of the commonest static problems in
mechanical engineering — cannot be expressed through the pre-processor alone.

**Countermeasure.** Let the pre-processor do what it can and insert only the
pre-tension block by hand, checking every line against the manual. CalculiX's
beam-element pre-tension (see G5) makes that block smaller than expected.

**Status:** open (next piece of work)

---

## G7 · An empty .dat file makes result loading throw

**What happens.** Without a `*NODE PRINT` request the `.dat` file is nearly
empty, yet `load_results_ccxdat()` still creates a text object and dereferences
`dat_text_obj.ViewObject`, giving
`AttributeError: 'NoneType' object has no attribute 'ViewObject'`. The solve
itself has already succeeded at that point.

**Countermeasure.** The Bridge's `fem.solve` wraps `ccx_run` and `load_results`
separately, degrading a failure to a `warning` rather than an exception, and
returns `solved` plus `solver_errors` extracted from stdout. **A failed solve
has to arrive as a diagnosis, not a crash.**

**Status:** filled

---

## G8 · An in-process Bridge needed a host restart for every code change

**What happens.** The Bridge loads as a module inside the FreeCAD process, so a
one-line change meant a restart, and a restart discarded all unsaved state. This
cost about ten restarts in one session, one of which lost a freshly generated
49k-node mesh.

**Countermeasure.** `system.reload` reloads `errors → contract → security → api
→ server` in dependency order inside the same FreeCAD process and rebinds the
socket.

The safety property that matters: **reload the modules first, and swap the
server only if every one of them imported.** If the new code is broken — one
typo — the old Bridge keeps serving, so FreeCAD is never left without one. All
three paths are tested: normal reload (same pid), reload with broken code
(Bridge survives, console reports the SyntaxError), reload after fixing it.
Covered by the integration test.

The reload request is served by the very server it replaces, so the reply goes
out and the dispatch stack unwinds before a zero-delay timer performs the swap —
reusing the re-entrancy counter added when fixing S2 below.

Not exposed over MCP: a developer operation does not belong in an agent's tool
space.

**Status:** filled

---

## G9 · Results cannot be plotted through the Bridge (**retracted**)

Colouring is driven by ViewObject properties (`NodeColor`, `Field`,
`DisplayMode`) and the Bridge only exposes App-level properties, so making the
result object visible and taking a screenshot produced a blank image.

**This entry was wrong.** CalculiX ships its own GUI pre- and post-processor,
**cgx**, installed here as `/usr/bin/cgx` 2.21 and named in the first paragraph
of the repository's own CalculiX notes. `cgx -v job.frd job.inp` loads results
together with the sets and loads taken from the deck — precisely what was
claimed to be impossible.

The real gap was ours: **not enumerating the installed tools before declaring a
capability missing.** The Bridge indeed cannot plot contours, but that is not a
gap in the stack. Recorded as a working principle in `AGENTS.md`.

**Status:** retracted

---

## G10 · cgx cannot take solid CAD, and its CAD converters are not packaged ⚠️ loud

**What happens.** cgx's own usage text states that `-step` reads "only points
and lines" — no surfaces, no bodies, so nothing that can be meshed. Every
`SURFACE_CURVE` in the file is rejected with `not known SURFACE_CURVE-type`.
It is also not scriptable: `read <file> stp` inside an `.fbd` gives
`ERROR, no matching file-type found`, so STEP only enters through the
interactive invocation.

**Evidence, graded.**

| Claim | Grade |
|---|---|
| `-step` is limited to points and lines | **documented** — cgx's usage text |
| every `SURFACE_CURVE` is refused | **observed** — 269 warnings against 269 `SURFACE_CURVE` entities in `halter.stp`, and the same on a FreeCAD-exported `joint.step` |
| STEP cannot be read from a command file | **observed** — `ERROR, no matching file-type found` |
| `-step` is interactive-only: it takes no piped commands either | **observed** — `printf 'send all fbd\nquit\n' \| cgx -step halter.stp` sat in the event loop until an 800 s timeout killed it, having executed neither command |
| after reading a STEP file cgx issues `plot l all` by itself | **observed** — it displays **lines**, which is consistent with the documented limit |
| the converters are missing | **observed** — `dpkg -L calculix-cgx` lists exactly one file, `/usr/bin/cgx`; `cad2fbd`, `vda2fbd`, `ng_vol` and `tetgen` are all absent |
| the resulting model contains 0 surfaces and 0 bodies | **not measured, and not measurable without a human at the window** — `prnt se` and `send all fbd` both went unexecuted because `-step` accepts no scripted input. The conclusion rests on the usage text and on cgx's own automatic `plot l all`, not on a count |

The read is not clean either: `ERROR in completeSet: set:+copy does not exist`
appears during interpretation, and `MANIFOLD_SOLID_BREP: #15` is recognised as
an entity without anything mesh-worthy resulting from it.

**Why it matters.** It settles the division of labour. cgx is a first-class
**deck** tool — sets, surfaces, loads, constraints, verification plots — and
not a geometry tool. Solid CAD reaches it through FreeCAD and Gmsh, or through
its own build language.

**Countermeasure.** Geometry in FreeCAD, mesh through Gmsh, then hand the mesh
to cgx (`-c`) and define everything else there. Upstream source for the
converters exists as `cgxCadTools.tar.bz2` if it is ever worth building.

**Status:** recorded (a real limit, loudly reported)

---

## G11 · cgx writes a traction card CalculiX cannot read ⚠️ loud

**What happens.** `send <set> abq trac <v1> <v2> <v3>` — the only obvious way to
apply a *tangential* distributed load — writes

```
38643, TRVEC3, 3.978874e+00, 1.000000e+00, 0.000000e+00, 0.000000e+00
```

and ccx 2.21 stops with `*ERROR reading *DLOAD`. `TRVEC` appears nowhere in the
ccx 2.23 manual.

**Why it matters.** Between the two pre-processors there is now **no working
route for a distributed load that is not normal to its face**: `pres` is normal
by definition, `trac` is unreadable, and FreeCAD's nodal route loses 11.8 %
(G2). For the bracket's radial bearing load this is the live blocker.

**Countermeasure.** Compute the consistent nodal forces and write the `*CLOAD`
block directly, checking the total against intent. Treat the deck as the
artifact.

**Status:** open

---

## Defects of our own, kept on record

| # | Problem | Nature |
|---|---|---|
| S1 | A rejected parameter left a half-configured object behind, and the same name could not be reused | validation order |
| S2 | A client disconnecting during a slow GUI call segfaulted FreeCAD. `Gui.updateGui()` re-enters the event loop, and `deleteLater()` inside that nested loop freed a socket Qt was still delivering read notifications to | concurrency / lifetime |
| S3 | `gui.fit_all` blocked for 11 s, longer than the 10 s default client timeout. Root cause was FreeCAD's `UseNavigationAnimations`, whose duration scales with camera travel. The Bridge now disables it around programmatic view changes and restores it, leaving the user's own setting untouched | host behaviour |
| S4 | `objects.list` assumed a `Shape` property is always a TopoShape; on a FEM mesh object it is a link to the part being meshed | type assumption |
| S5 | The Bridge previously did not capture FreeCAD's console, so `PrintError`/`PrintMessage` from the writer never reached the agent. FreeCAD stated the cause of G2 in plain language at the moment the deck was written, and it was lost. The Bridge now returns the per-request Report View delta as `host_messages` on success and failure, and explicitly reports when that channel is unavailable. **Closed in Bridge 0.6.0; live FEM regression pending.** | missing channel |

---

## Two things this taught us about method

**A generic API beats a domain wrapper.** The real property names on FEM objects
(`mesh_gmsh.Shape` rather than `Part`; `constraint_force.DirectionVector` being
read-only) were not found by reading source. They were found by asking the live
object through the generic property API. One `objects.get_properties` is worth a
pile of per-type schemas, and it does not go stale when the host does.

**The gap between reading and recalling is measurable.** Nearly every API-level
mistake in that session was on the CalculiX side, where no authoritative
documentation was installed; the FreeCAD side, well represented in training
data, was mostly right first time. That is a corpus availability problem, not a
model capability problem — which is why the retrieval layer is a precondition
for doing FEA at all, not a nicety.
