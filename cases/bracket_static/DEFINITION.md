# Flanged bearing bracket · static · first FEA run to completion

Generated CAD, meshes, results and evidence files referenced here are local,
Git-ignored artifacts. They are not included in a fresh clone; regenerate them
where a procedure is provided, or obtain the preserved local case archive.
Source scripts, authored inputs and this document remain versioned.

## 1. Engineering problem

A flanged bearing bracket bolted to a base through four Ø10 holes in its base
plate, with the bearing bore carrying a radial load. Questions:

1. Where is the peak stress and how large is it?
2. **How much load does each bolt actually carry?** (this decides bolt
   selection and preload requirements)
3. Does the base plate lift off?

## 2. Geometry

Taken from `bridge/test-output/bracket.FCStd`, built entirely through
step-by-step Bridge API calls (16 objects, 5 boolean operations):

base plate 120×80×12, conical transition R40→R25, bearing boss Ø50×60, Ø30
through bore, retaining-ring groove (toroid R25/R3), transverse Ø12 oil hole,
four Ø10 bolt holes in the base plate at (±48, ±30).

| Face | Role |
|---|---|
| Face12 | Ø30 bearing bore (intended load face, see below) |
| Face16 | boss top annulus, π(25²−15²)=1256.6 mm² (actual load face used) |
| Face9/10/11/13 | the four bolt holes, each A=2π·5·12=377.0 mm² |
| Face5 | base plate bottom face |

## 3. Material and units

S355: E = 210 000 MPa, ν = 0.30. Units **mm–N–MPa–t**.

Verified in the deck: `*ELASTIC / 210000, 0.3`, and `*SOLID SECTION,
ELSET=MatSteelSolid` where `MatSteelSolid` resolves to `Evolumes`, i.e. every
C3D10 element. Material coverage is complete.

> Dimensional quantities are always written with a unit (`"5000 N"`). A bare
> number is read in FreeCAD's internal units — force is internally mN — a
> silent factor-of-1000 error. See [GAPS.md G4](../../docs/GAPS.md).

## 4. Loads and boundary conditions

| | |
|---|---|
| Radial load | 5000 N, +X (4410.35 N actually reached the deck, see A3) |
| Constraint | full restraint on the cylindrical face of each of the 4 bolt holes |
| Analysis type | linear elastic static, CalculiX 2.23 |
| Mesh | Gmsh second-order tetrahedra, 4 mm, `SecondOrderLinear=true`, 49 123 nodes / 28 806 elements |

## 5. Assumption register

| # | Assumption | Invalidated when | Result this run |
|---|---|---|---|
| A1 | Linear elastic, small deformation | peak von Mises ≥ 355 MPa (S355 yield) or displacement/characteristic length ≥ 5% | **passes**: structural peak 33.7 MPa, displacement 0.018 mm |
| A2 | Full restraint on the bolt holes represents the bolted connection | the idealisation omits a load path that exists in reality | **fails** — see A8 |
| A3 | Applied load equals the intended load | Σ(deck node loads) ≠ intended value | **fails**: 4410.3 N vs 5000 N, 11.8% short. Cause now known: 22 element faces on the bore edge were dropped from the area weighting, `tools/check_face_load.py` reproduces 0.88207 exactly — [GAPS.md G2](../../docs/GAPS.md). Every stress below is low by this factor and has been scaled where stated |
| A4 | Overall static equilibrium | Σapplied + Σreaction ≠ 0 | **passes**: −4410.349 cancels exactly |
| A5 | Mesh has no inverted elements | ccx reports nonpositive jacobian | **passes** (failed first; passed after refining and setting `SecondOrderLinear`) |
| A6 | Mesh has converged | no convergence study performed | **not assessed** |
| A7 | The reported peak stress is a structural response, not a constraint singularity | the peak node sits inside the constrained set | **fails as reported** — the global peak of 84.44 MPa sits on constrained nodes. Resolved by excluding the constrained region: the structural peak is 33.65 MPa, see §7 |
| A8 | The plate is supported only at the bolt holes | the plate displaces downward where a base would be | **fails**: base plate Uz = −0.0029 mm at (+31.5, 0), i.e. it sinks into a base that is not in the model. The entire compressive bearing load path is missing |

## 6. Step-by-step verification

| Step | How verified | Result |
|---|---|---|
| Geometry | volume against analytical values | ✓ all exact |
| Material and units | `*ELASTIC` and `*SOLID SECTION` read from the deck | ✓ 210000, 0.3; covers all elements |
| Mesh | screenshot `step2_mesh.png` | ✓ curvature adaptivity works, refined at the groove |
| Constraint location | `tools/inspect_deck.py` | ✓ 412 nodes, x[−53,53] y[−35,35] z[0,12] r[51.6,61.6], dof 1/2/3 |
| Load location | same | ✓ 486 nodes, z constant at 72.00, r[15,25] — confirmed as Face16 |
| Load direction | same + screenshot `step3_bcs.png` | ✓ Fx=4410.3, Fy=Fz=0, arrows point +X |
| Load magnitude | against intent | ✗ 4410.3 vs 5000 (G2) |
| Deformed shape | displacement field + `step5_deformed.png` (cgx) | ✓ constrained nodes exactly zero; loaded ring translates in pure +X; boss tips +X-side-down; classic cantilever gradient. ✗ revealed A8 |
| Peak stress location | `tools/inspect_frd.py` | ✗ global peak sits on constrained nodes (A7) |
| Structural stress vs hand calculation | beam bending at two sections | ✓ both hot spots match with textbook Kt, see §7 |

## 7. Results

The global peak is an artefact of the constraint. Excluding the constrained
region gives the structure's actual response, and it survives an independent
check.

| Location | FEA | Nominal bending M/Z | Implied Kt | Expected Kt |
|---|---|---|---|---|
| z=27, cone-to-cylinder step (no fillet) | 33.65 MPa | 18.6 MPa | 1.81 | 1.5–2 |
| z=45, transverse Ø12 oil hole | 33.54 MPa | 11.1 MPa | 3.01 | 2–3 |

Hollow boss section: I = 267 035 mm⁴, Z = 10 681 mm³; moment taken as the
applied 4410.35 N acting at z=72.

| Quantity | Value |
|---|---|
| Structural peak von Mises (as run, 4410 N) | 33.65 MPa |
| Structural peak corrected to the intended 5000 N | 38.1 MPa |
| Safety factor against S355 yield | ≈ 9 |
| Max displacement | 0.01808 mm at the boss top rim |
| Global peak von Mises (constraint artefact, not a result) | 84.44 MPa |

## 8. What holds and what does not

The dividing line is static determinacy.

**The boss stresses hold.** The bending moment at the boss root depends only on
the applied load and the moment arm, not on how the base plate is supported. So
the missing bearing load path (A8) does not affect them, and both hot spots
agree with hand calculation at sensible stress concentration factors. Subject to
correcting the 11.8% load shortfall, 38.1 MPa at the cone-to-cylinder step is a
usable number.

**The bolt loads and plate stresses do not hold.** They depend entirely on the
load path that A8 shows is missing. In a real bolted bracket most of the
overturning moment is reacted by bearing pressure between the plate and the
base; here that path was removed, so the whole moment is forced through four
hole walls. That is both why the peak stress lands on the constraint and why the
per-bolt load — the original question 2 — cannot be answered by this model at
all.

**Also outstanding:** the load acts on the boss top annulus at z=72 rather than
the bore wall at z≈45, inflating the moment arm by 60%; and no mesh convergence
study has been done, so 33.65 MPa carries no discretisation error estimate.

## 9. Next

1. Add the plate-to-base bearing path — the missing load path from A8. Without
   it neither bolt loads nor plate stresses mean anything.
2. ~~Fix A3: find why FreeCAD's load distribution loses 11.8%~~ — **cause
   found**, [GAPS.md G2](../../docs/GAPS.md). Straightened mid-side nodes on the
   bore edge fall outside the face, and those element faces contribute no load.
   Re-run either with a pressure load or after correcting the node set, and
   confirm with `tools/check_face_load.py` that the deck reaches 5000 N.
3. Move the load to the bearing bore Face12 at the correct height: needs the
   cylindrical-face zero-load problem solved first
   ([GAPS.md G1](../../docs/GAPS.md)).
4. Bolt preload plus contact, which is the only way to answer the per-bolt load
   question and compare against the hand calculation.
5. Mesh convergence study (3 levels) on the boss hot spots.
6. Compare against the solid-bolt model in `cases/bolted_joint_M12_static/` to
   quantify the accuracy of the simplified idealisation.

## 10. Files

| | |
|---|---|
| Model (mesh and analysis included) | `bracket_fem.FCStd` |
| Solve directory | `solve/` (`.inp` `.frd` `.dat` `.sta` `.cvg`) |
| Mesh | `step2_mesh.png` |
| Boundary conditions and loads | `step3_bcs.png` |
| Deformed shape (Ux, ×400) | `step5_deformed.png` |
