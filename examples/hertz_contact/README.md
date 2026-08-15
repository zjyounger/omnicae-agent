# Hertz Contact CAD

The first CAD-only workflow built after the Bridge was in place, to verify that an agent can create multi-body contact geometry through MCP.

## Geometry assumptions

- classic 3D sphere-on-flat Hertz point contact;
- lower block: `80 × 80 × 10 mm`;
- upper sphere: radius `20 mm`;
- block top face at `z = 10 mm`;
- sphere centre at `[0, 0, 30] mm`, so the sphere's lowest point sits exactly at `z = 10 mm`;
- zero initial gap and zero initial penetration.

The model contains two independent solids, with no boolean fuse. The STEP file also keeps both solids separate, so a contact pair can be defined later.

## Current boundary

Only CAD is created and verified here: solids, dimensions, placement, contact geometry, FCStd, STEP, and a screenshot.

Material, contact properties, boundary conditions, loads, mesh, and solver model are not yet defined.

## Running it

Start the FreeCAD Bridge first, then run from the MCP environment:

```bash
.venv-mcp/bin/python examples/hertz_contact/create.py \
  --output-dir /data/CAE/projects/hertz_contact
```
