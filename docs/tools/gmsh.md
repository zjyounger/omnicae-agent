# Gmsh

Mesher. `gmsh 4.12.1` from the distribution, 4.15 bundled inside the FreeCAD
AppImage and used by the FEM workbench. Full PDF manual at
`/usr/share/doc/gmsh-doc/gmsh.pdf.gz`.

No Python module is installed for the system copy; the CLI takes `.geo`
command files.

## Second-order elements on small features

By default Gmsh projects the mid-side nodes of second-order elements onto the
curved geometry. On small fillets, grooves, and intersecting holes this inverts
elements, and CalculiX rejects them with `nonpositive jacobian`.

**Set `SecondOrderLinear = true` as the starting point for second-order solid
meshes.** Mid-side nodes then sit at edge midpoints instead of being projected.
On a bracket with an R3 retaining-ring groove and a Ø12 cross hole, a uniform
6 mm mesh failed every time and the same model meshed and solved once this was
set and the size dropped to 4 mm.

This is one of the most common reasons an open-source structural run fails
outright, and it is the concrete form of "meshing is the hard bottleneck".

## Probing a STEP file

A `.geo` that merges the file and prints bounding boxes is enough to identify
which volume and surface tags correspond to which feature:

```
SetFactory("OpenCASCADE");
Merge "part.step";
v() = Volume{:};
For i In {0:#v[]-1}
  bb() = BoundingBox Volume{v(i)};
  Printf("V%g x[%g,%g] y[%g,%g] z[%g,%g]", v(i), bb(0),bb(3), bb(1),bb(4), bb(2),bb(5));
EndFor
```

Run with `gmsh -0 probe.geo`. Separate solids in one STEP stay separate volumes
with independent meshes, which is what contact needs.
