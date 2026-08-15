# FreeCAD

Version in use: 1.1.3, official Linux AppImage. Bundles CalculiX 2.23 and
Gmsh 4.15. Used for geometry, FEM pre-processing, and reading results back.

## Driving it

Scriptable through its own Python API in-process. Geometry primitives are plain
`addObject` types (`Part::Box`, `Part::Cylinder`, ...). FEM objects are **not** —
they are Python features that must be created through the `ObjectsFem` factory
functions, because a bare `addObject` produces an object with no Proxy that then
silently writes nothing to the solver deck.

Factory names are case-sensitive in ways that are easy to get wrong:
`makeSolverCalculiXCcxTools` has a capital X.

Meshing goes through `femmesh.gmshtools.GmshTools(mesh_obj).create_mesh()`.
Solving goes through `femtools.ccxtools.FemToolsCcx(analysis, solver)`. The
working directory has to be set before `check_prerequisites()`, because it is
itself one of the prerequisites.

## Where it will mislead you

**A force on a cylindrical face can silently produce no load at all.** The
writer emits a `*CLOAD` block containing only a comment and no node loads. The
solver then exits 0, writes a result file, and every displacement and stress is
zero. Moving the same constraint to a planar face produces node loads
immediately. Nothing anywhere reports a problem.

**A distributed force does not necessarily total what you asked for.** A 5000 N
request produced 4410.35 N of node loads — 11.8% short. Applied load and
reaction agree exactly with each other, so checking equilibrium does not catch
it; only comparing the deck against your intent does.

The mechanism (measured, see [GAPS.md G2](../GAPS.md)): a face force is spread
by area-weighting the mesh faces on the reference face, and
`get_ref_facenodes_areas()` in `femmesh/meshtools.py` handles node counts of 3,
4, 6 and 8 only. With `SecondOrderLinear=true` the mid-side node of a chord on a
**concave** boundary — a hole edge — lands outside the face, so
`getNodesByFace()` omits it, the element face arrives with 5 nodes, and it falls
through every branch contributing no area and no load. Silently. Expect this on
any loaded face bounded by a hole; it is worst on small annuli. Use a pressure
constraint where the load is normal to the face — `*DLOAD` is written per
element face and does not go through this path — or check the deck with
`tools/check_face_load.py`.

**FreeCAD does report it, on a channel you are probably not reading.** The same
function prints `Deviation sum_node_load to frc_obj.Force is more than 1%` with
the ratio and a hint, to the FreeCAD console. The Bridge does not capture the
console. Read the report view after writing a deck.

**Bare numbers on dimensional properties are read in internal units.** Internal
units are mm–kg–s, so force is kg·mm/s² = mN, and `Force = 5000` means 5 N. Pass
`"5000 N"` instead and FreeCAD parses and validates it.

**An empty `.dat` file breaks result loading.** With no `*NODE PRINT` requested
the file is nearly empty, and `load_results_ccxdat()` still builds a text object
and dereferences a `None` view provider. The solve itself has already succeeded
at that point.

**`Shape` is not always geometry.** On a FEM mesh object, `Shape` is a link to
the part being meshed, not a TopoShape.

**Camera moves block for as long as the animation lasts.** `UseNavigationAnimations`
is on by default and the duration scales with camera travel: `fitAll` on a
20-face model took 11 s. Turn the preference off around programmatic view
changes and restore it afterwards.

## Coverage of the CalculiX writer

Supported: fixed, displacement, force, pressure, contact, tie, rigid body,
section print, self weight, centrif, transform, plane rotation. Contact is
written as `*CONTACT PAIR` / `*SURFACE INTERACTION` / `*SURFACE BEHAVIOR` /
`*FRICTION`, ties as `*TIE`.

**Not supported: bolt pre-tension.** There is no `PRE-TENSION` anywhere in the
Fem module, so pre-loaded bolted joints cannot be expressed through the
pre-processor alone.
