# Inline-four rotating assembly — original CAD study

This is the first agreed stage of the user's inline-four engine CAD demonstration:
the crankshaft and four piston/connecting-rod assemblies. It is an original
concept, not a dimensional reproduction of an OEM engine. No downloaded CAD is
used. Geometry is created with native FreeCAD sketches, pads and pockets.

## Geometry and scope

- Units: mm and degrees. Crankshaft axis X; cylinder axes Z; swing plane YZ.
- Bore 86; piston skirt diameter 85.92; stroke 86; cylinder pitch 96.
- Connecting-rod centre distance 143; wrist pin diameter 22.
- Five main journals, diameter 55; four crankpins, diameter 48.
- Crankpin phases: 0, 180, 180, 0 degrees (cylinders 1 through 4).
- Split rod big ends, separate bearing halves, small-end bushes, hollow wrist
  pins, three split rings per piston, and rod-cap fasteners are modelled.
- Counterweights are geometric concepts: no claim of dynamic balancing.
- No block, head, timing, lubrication circuit, bearing housing or combustion
  calculation is included at this stage. Fastener threads, oil holes, production
  fillets, piston ovality/taper and thermally determined fits are not detailed.

The piston axis is deliberately unoffset. Its pin height is obtained from the
slider-crank closure: z = r cos(theta) + sqrt(l^2 - r^2 sin(theta)^2).
Rod inclination is computed from the same joint centres, not eyeballed.

## Checks agreed before construction

1. Each finished component must be a valid, positive-volume single solid.
2. Crankshaft must be one connected solid, with five coaxial main journals.
3. The four piston strokes must measure 86 mm; 1/4 and 2/3 must remain paired.
4. Rod pin-centre distance must remain 143 mm throughout a revolution.
5. Inspect actual solid intersections between adjacent moving components at
   sampled angles; report the sampling interval and excluded interfaces.
6. Reopen the saved FCStd and re-import the STEP to verify artifact persistence.

The angle is an editable document property driving native placement expressions.
Geometry dimensions are centralized in the source generator; changing them and
regenerating rebuilds the native feature trees. This is an expression-driven
kinematic assembly, not a joint-solver/dynamics assembly.

Structural reference (qualitative, not a dimension source): Motorservice's
connecting-rod and piston-pin descriptions:
https://www.ms-motorservice.com/int/en/product-group/7416/
https://www.ms-motorservice.com/trbfep/en/technipedia/ks-kolbenschmidt-pistons-with-keystone-shaped-connecting-rod-recess-11
