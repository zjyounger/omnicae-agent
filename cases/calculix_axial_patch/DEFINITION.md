# CalculiX axial patch benchmark

## Question

Can the installed CalculiX solver reproduce the constant-strain solution for a
single linear brick under uniaxial tension, with the intended load and support
conditions confirmed from the input deck?

The source deck is [`../../calculix/cantilever.inp`](../../calculix/cantilever.inp).
Its legacy filename says `cantilever`, but the model is an axial patch test, not
a bending cantilever.

## Definition

- Unit system: mm, N, MPa.
- Geometry: one 1 mm × 1 mm × 1 mm C3D8 element.
- Material: linear elastic, E = 210,000 MPa and ν = 0.3.
- Load: four 250 N nodal forces in +x on the x = 1 mm face; resultant 1,000 N.
- Restraint: x displacement fixed on the x = 0 face. Minimal y/z anchors remove
  rigid motion while leaving the uniform Poisson contraction admissible.
- Procedure: linear static.

The analytical constant-strain solution is

```text
axial stress       F/A       = 1,000 MPa
axial displacement FL/(AE)   = 0.004761904762 mm
lateral displacement at y=1  = -nu F L/(AE) = -0.001428571429 mm
```

The model is a solver/deck/reader patch test. It does not validate bending,
mesh convergence, stress concentrations, or a real component idealisation.

## Observed result

CalculiX 2.21 completed in one increment on 2026-08-19. The deck inspector
confirmed four loaded nodes and a +1,000 N resultant. The `.dat` output reported:

- axial displacement at every loaded node: 0.004761905 mm;
- lateral displacement at y = 1 mm or z = 1 mm: -0.001428571 mm;
- reaction resultant on the x = 0 face: -1,000.000 N in x.

Relative to the analytical values, the displacement deviation is below
0.00001% at the printed precision and force imbalance is 0. The FRD nodal
stress output is 999.96 MPa, a -0.004% printed/output deviation from 1,000 MPa.

## Confidence and invalidation

Confidence is high for this narrow constant-strain patch test because the
applied load, reaction, displacement, stress, and Poisson contraction close
against independent analytical values. It says nothing about the accuracy of
a coarse mesh in nonuniform stress or bending. Any change to element type,
constraints, dimensions, material constants, or load distribution requires the
reference values to be recomputed.
