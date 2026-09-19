# Cylinder block — second CAD stage

The user requested a cylinder block for the completed original inline-four
rotating assembly. The original rotating-assembly FCStd is the dimensional
source and remains unchanged. This stage adds the block, five removable main
caps, ten main-bearing halves, ten cap bolts and eight coolant core plugs.

## Coordinate and dimensional contract

- X is the crankshaft axis; Z is the cylinder direction; Y is transverse.
- Cylinder X centres: -144, -48, 48, 144 mm. Bore diameter: 86 mm.
- Main journal X centres: -192, -96, 0, 96, 192 mm; journal diameter 55 mm.
- Piston crown at TDC: 43 + 143 + 31 = 217 mm above the crank axis.
- Deck Z: 218 mm, giving 1 mm geometric piston/deck clearance at TDC.
- Cylinder bank starts at Z=90 mm. At BDC the skirt bottom is at Z=75 mm;
  15 mm protrudes below the bank into the crankcase.
- Bore-shaped reliefs extend into the upper bearing webs down to Z=70 mm,
  below the BDC skirt bottom. Without those reliefs the ends of the 24 mm-wide
  bearing webs would intrude into the skirt sweep despite correct cylinder axes.
- Two local connecting-rod notches per bore occupy X=center±16 mm,
  Y=39..46 mm and -46..-39 mm, Z=70..106 mm. The initial 60-degree check found
  the rod forging at Y=-42.52..-41.29, Z=98..101.26 mm intersecting the bore
  mouth. The notches clear that region without enlarging the upper cylinder
  bore. The lowest oil-ring bottom is at Z=115 mm, above the notches; the
  water-jacket floor at Z=118 mm is also retained.
- Five upper bulkheads and separate main caps are 24 mm wide, within the
  28 mm-wide main journals and between the crank webs.
- Main tunnel diameter 60.05 mm; bearing OD 59.96 mm; ID 55.06 mm.
- Deep-skirt crankcase extends to Z=-90 mm with an open oil-pan interface.
- Concept water jacket: Z=118..208 mm, 4 mm nominal cylinder walls and a
  10 mm closed deck. Deck passages connect it to a future cylinder head.

These dimensions are chosen for this original geometric study, not taken from
an OEM engine. Fits are explicit geometric clearances, not thermal/production
tolerances. The block has no finished oil circuit, thrust-bearing retention,
head gasket, cylinder head, end seals or oil pan at this stage. Water-jacket
geometry does not establish cooling performance or casting feasibility.

## Verification before acceptance

1. Inspect the native shape after each pad/pocket; each component must remain
   one valid positive-volume solid.
2. Measure the actual bore cylindrical surfaces and main tunnel from the BRep,
   not just the generator inputs. Check bore length and TDC clearance.
3. Check block/core-plug/main-cap/bearing/bolt intersections, then test the
   complete moving assembly against the new stationary assembly at 15-degree
   crank-angle intervals. Sampling is not a continuous collision proof.
4. Render the exterior, underside and a geometric cutaway from the generated
   solids; inspect those images before delivery.
5. Reopen both native files and reimport exported STEP solids. Compare geometry
   with two-way Boolean differences and non-tessellated optimal bounding boxes.
6. Preserve the rotating-assembly source hash to verify it was not overwritten.
