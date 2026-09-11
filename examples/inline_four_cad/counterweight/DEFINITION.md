# Counterweight mass-moment design — revision 1

User request: replace the earlier uncalculated counterweight concept with a
designed geometry, using an ordinary crankshaft steel. This stage targets
per-throw rotating first-moment balance, not a complete engine durability design.

## Material assumptions

Crankshaft: 42CrMo4, quenched and tempered; density **7800 kg/m³**, from
Ovako's typical physical properties: https://steelnavigator.ovako.com/steel-grades/42crmo4/
The supplier also lists E=210 GPa and Poisson ratio 0.3, but no strength result
is being calculated here. Strength would require a specified product section,
heat treatment and fatigue data.

For the existing conceptual assembly, rod, cap, bolts, pin, rings and equivalent
steel-backed bearing shells use 7800 kg/m³; the small-end bush uses an assumed
8800 kg/m³, piston an assumed 2700 kg/m³. These are explicit design assumptions,
not measurements from an OEM engine. Oil inventory is omitted. Ring density,
piston density and small-end bush density do not enter this revision's pure
rotating balance target, though their masses are reported for later analysis.

## Balance target and alternative explanation

Use 100% equivalent rotating mass and 0% reciprocating mass in the counterweight
target. This is a declared first design point, not a universally optimal inline
four balance factor or a demonstrated minimum of main-bearing loads.

The rod assembly includes rod forging, cap, bolts, bearing halves and bush.
For rod length L=143 mm and local CG distance z from the big-end pin:

    m_big = sum(m_j * (1 - z_j/L))
    m_small = sum(m_j * z_j/L)

This two-end replacement preserves total mass and CG, but generally not the
rod's rotational inertia. Record the real CAD inertia and the discrepancy;
retain real inertia when building a full multibody model later.

For each 96 mm crank cell between neighbouring main-bearing centre planes,
including the two webs, crankpin and main-journal halves:

    residual = rho * integral(z dV) + m_big * 43 mm = 0

Use the actual fused CAD solid's first moment, so intersections cannot be
double-counted. Reflection defines the other throw signs. Two equal webs flank
each pin, retaining axial symmetry. The adjustable counterweight lower contour
is a semicircle opposite the crankpin; retain a 27 mm crankpin lobe, 27.5 mm
root half-width and 20 mm web thickness. Solve the outer radius within 55–74 mm,
then round it to 0.01 mm and report the remaining imbalance.

Whole-crank zero force/couple alone is NOT an acceptance check: the symmetric
0/180/180/0 layout can pass that even with badly chosen individual weights.
Inspect per-cell residuals as well. This design does not cancel the inline-four
secondary reciprocating force and does not optimise flexible shaft/bearing loads.
The distinction between global balance and journal load changes is discussed in
the research paper https://www.mdpi.com/2076-3417/11/19/8997 .

## Acceptance and limits

- Preserve source FCStd and all journal, pin and interface dimensions.
- New shaft remains one valid native solid with editable sketches/pads/pockets.
- Each cell rotating mass-moment residual is below 0.1% of its rod equivalent
  rotating moment after the radius is rounded.
- Inspect crank versus every other body over a 360-degree revolution at 5-degree
  intervals. No positive overlap above 1e-5 mm³; at least 1 mm sampled cold
  clearance to block and piston bodies. Bearing radial clearance remains the
  existing value and is not subject to the 1 mm envelope criterion.
- Reopen native output and reimport STEP. Compare both Boolean differences.
- Report the rod assembly's true mass, CG and inertia alongside the equivalent
  end masses; report shaft mass, CG, inertia and per-web first moments.

Fillets, oil drillings, forging details, elastic deflection, hot clearances,
fatigue, manufacturing balance tolerance and bearing load optimisation remain
outside this stage. Adding/removing any material later requires recalculating
the balance target and checking the geometry again.
