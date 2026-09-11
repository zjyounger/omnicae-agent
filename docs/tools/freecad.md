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

## Native CAD observations from the inline-four study

- Check the running application's native IPC before attempting GUI input.
  During the inline-four shutdown, `/tmp/FreeCAD` accepted a UTF-8 line
  `OpenFile:/absolute/path/script.FCMacro\n`; the owning GUI instance executed
  the macro, saved its live documents with `saveAs`, and exited normally.
  Only the first of three instances owned this endpoint; it was not a broadcast
  interface. Inspect the socket owner and require an in-process save receipt.
  Evidence: `examples/inline_four_cad/session_close_20260911/freecad_1341644.json`.
- An additive feature can refill an earlier hole. In
  `examples/inline_four_cad/`, adding the rod-cap bolt seats after the annular
  bearing bore introduced about 213 mm³ of bearing interference per cap. A
  final bore pocket removed it. Check final solid intersections, including
  components that appear to fit in an external view.
- `Shape.BoundBox` can include display triangulation approximations. For a
  geometric native/STEP comparison, use
  `Shape.optimalBoundingBox(False, False)` and inspect both Boolean differences;
  do not equate a small default-box or volume-summary discrepancy with a
  demonstrated geometry change.
- A Qt main-window `grab()` captured the OpenGL viewport incorrectly in this
  session even though `activeView().saveImage()` rendered correctly. Use native
  `saveImage()` for CAD views and an exact-window X11 capture for GUI evidence;
  visually inspect either result before reporting it.
- The inline-four document's `App::PropertyAngle` clamps requested values above
  360 degrees to 360. This froze the second turn of the initial ignition export.
  Keep the 720-degree four-stroke cycle separate and write its angle modulo 360
  to the mechanical property. `ignition/freecad_angle_probe.json` records actual
  stored values for requests 359, 360, 361, 540 and 720; cross-application motion
  comparison caught the resulting 86 mm discrepancy before delivery.
- Resetting `Placement` to identity also loses a previously configured rotation
  axis. In the counterweight export, restoring only an angle expression made
  the display shaft turn around the default axis. Restore the X axis explicitly
  before restoring the angle expression; `counterweight/check_cutaway.py`
  compares actual placed shaft solids against the uncut assembly at six angles.

- Cross-assembly surface registries need `App::PropertyLinkSubGlobal` when
  referencing Bodies inside other `App::Part` containers. Ordinary
  `App::PropertyLinkSub` emitted out-of-scope warnings in the inline-four archive.
  The global property removed those warnings;
  `examples/inline_four_cad/reference_v1/verification.json` records successful
  save/reopen of 68 selections and unchanged geometry for all 83 Bodies.
  These references and archived face names are version-specific; CAD edits or
  STEP reimport still require geometric revalidation.
