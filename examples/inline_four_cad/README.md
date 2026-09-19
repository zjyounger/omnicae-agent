# Inline-four 2.0 L — original CAD example

Generated CAD, meshes, results and evidence files referenced here are local,
Git-ignored artifacts. They are not included in a fresh clone; regenerate them
where a procedure is provided, or obtain the preserved local case archive.
Source scripts, authored inputs and this document remain versioned.

**Archived reference:** [named short-block CAD v1](reference_v1/README.md) provides
all-face names, geometric boundary selections and verification for future FEA/CFD preparation.
See `archive/` for the complete frozen snapshot.

An original FreeCAD model of a four-cylinder crankshaft/piston/connecting-rod
assembly. No downloaded CAD, MCP server or repository Bridge is used to build it.
`model.py` constructs the geometry through FreeCAD's native Python API.

The subsequently requested cylinder block and short-block assembly are in
[BLOCK_README.md](BLOCK_README.md), with separate CAD files and checks.

![Assembly](assembly.png)

## Open and inspect

- `inline_four_rotating_assembly.FCStd`: editable original with 49 component
  Bodies, 163 Sketcher profiles, and 163 native PartDesign pads/pockets.
- `inline_four_rotating_assembly.step`: placed individual solid components.
- `piston_rod_section.FCStd`: a separate geometric section for inspecting the
  piston underside, pin bosses, hollow pin, small-end bush and split big end.
- `rotation.gif` / `rotation.mp4`: one crank revolution, 72 native FreeCAD
  frames, 5 degrees per frame, displayed at 24 frames/second.
- `piston_section.png`, `front_elevation.png`, `assembly.png`: native CAD views.
- `freecad_window.png`: the actual FreeCAD window, captured separately from
  its OpenGL viewport rendering.

In the main FCStd, select **00 · Mechanism / edit CrankAngle**, then edit
**CrankAngle** in the Data tab. Native placement expressions move the crank,
rods and pistons. No external Python proxy is required for this motion after
reopening. This is an analytically driven kinematic assembly, not a solved
Assembly-workbench joint system or a dynamics simulation.

Geometry dimensions are centralized in `model.py:P`. Change those and rebuild
to regenerate the native features. The saved sketches contain editable geometry;
they are not a completely dimension-constrained production sketch system.

## Design

86 mm nominal bore, 85.92 mm piston skirt diameter, 86 mm stroke, 96 mm cylinder
pitch, 143 mm rod centre distance, 55 mm main journals, 48 mm crankpins and
22 mm wrist pins. The implied four-cylinder swept volume is approximately
1.998 L. Cylinders 1/4 share a crank phase; 2/3 are 180 degrees away.

The 49 components consist of one crankshaft and, per cylinder: piston, hollow
pin, three split rings, rod, rod cap, two big-end bearing halves, small-end bush
and two cap bolts. See `DEFINITION.md` for assumptions and boundaries.

## Reproduce

From this repository, using the installed FreeCAD AppImage launcher:

```bash
freecad examples/inline_four_cad/build.FCMacro
freecad freecadcmd examples/inline_four_cad/check.py
freecad examples/inline_four_cad/render.FCMacro
```

The macros' default path targets this workspace. If copied elsewhere, set
`INLINE_FOUR_ROOT` to the absolute directory containing these files. The check
script also works from its own file location. `INLINE_FOUR_CLOSE=1` makes the
build macro close its newly launched session after writing the model.

If FUSE is unavailable, extract the AppImage into a temporary directory and
use its `squashfs-root/AppRun`, with `freecadcmd` as its first argument for
headless checks. The build and render macros require an accessible GUI display.
Use separate `-u` and `-s` config files for disposable verification sessions.

To encode the motion frames:

```bash
ffmpeg -framerate 24 -i motion_frames/frame_%03d.png -c:v libx264 \
  -pix_fmt yuv420p -movflags +faststart rotation.mp4
```

## Evidence

`verification.json` records component validity, volume, measured stroke and
joint-closure samples. `inspection.json` records an independent reopening,
crankpin/rod-centre alignment, interference checks, and STEP reimport checks.

- Four measured strokes: **86 mm**.
- Motion closure and crankpin alignment: below **1e-7 mm** acceptance threshold.
- All 49 component solids must be valid and have positive volume.
- Collision sampling: **0 through 345 degrees in 15-degree increments**;
  **1,100** bounding-box-selected Boolean common operations. Relative geometry
  within each rigid subassembly is checked once. No component interfaces are
  excluded; zero-volume contact is allowed, overlap above **1e-5 mm³** fails.
- STEP comparison: pair all 49 imported solids with native components using
  position and volume; check two-way Boolean subtraction and geometric optimal
  bounding boxes. Default display-based bounding boxes are not used as precise
  dimension measurements. Preserve mass-property differences in the report.

These are sampled geometric checks, not proof of clearance at every angle,
dynamic balance, fatigue strength, production fits or an operable engine.

The first inspection caught a real modelling defect: the cap bolt-seat pads
intruded into the already-created bearing bore, causing about 213 mm³ overlap
per lower bearing half. `inspection_initial.json` preserves that failed result.
The final feature tree cuts the bearing bore after adding the bolt seats.

The initial STEP check also found a roughly 3.5 ppm difference between compound
volume summaries. This is retained rather than silently rounded away. Direct
geometry checks are used to distinguish that statistic from a detectable change
to the component BReps.

## Current boundary

This completes the agreed rotating-assembly stage. The block, head, timing
mechanism, oil circuit and production detailing belong to subsequent stages.
The oil ring is a simplified split ring, fasteners have no helical threads,
and piston/counterweight shapes are concept geometry. This is not an OEM
replica or a manufacturing release.
