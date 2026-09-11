# M12 pre-loaded bolted joint · static

Generated CAD, meshes, results and evidence files referenced here are local,
Git-ignored artifacts. They are not included in a fresh clone; regenerate them
where a procedure is provided, or obtain the preserved local case archive.
Source scripts, authored inputs and this document remain versioned.

The first FEA case. The point is not to produce a number but to exercise the
chain "problem definition → assumption register → solve → recheck assumptions
against the result".

## 1. Engineering problem

A bolted joint pre-loaded and loaded in axial tension. Two questions:

1. Under the design external load, does the joint stay closed (no separation)?
2. Does the bolt stay below its proof stress? How much of the external load
   actually reaches the bolt?

The decision this supports: **whether the preload and bolt grade chosen for
this joint are right.**

## 2. Failure modes considered

| Failure mode | Assessed here |
|---|---|
| Joint separation | yes (primary) |
| Bolt yield / exceeding proof stress | yes (primary) |
| Plate yield under the bearing face | yes (secondary) |
| Bolt slip (shear case) | no — this case is purely axial |
| Thread stripping | no — the thread is not modelled |
| Fatigue | no — see assumption A4, out of scope for this model |
| Relaxation / creep | no |

## 3. Geometry and material

| | |
|---|---|
| Bolt | M12, plain shank Ø12 (thread not modelled), head Ø18×7.5, nut Ø18×10 |
| Clamped parts | 2 × steel plate 60×60×15 mm |
| Grip length l | 30 mm |
| Clearance hole | Ø13 (medium clearance fit) |
| Bolt material | grade 8.8, E = 200 GPa, ν = 0.3, Sp = 600 MPa, Sy = 640 MPa |
| Plate material | S355, E = 210 GPa, ν = 0.3, Sy = 355 MPa |
| Units | **mm–N–MPa–t** (length mm, force N, stress MPa, density t/mm³) |

## 4. Loads and boundary conditions

| | Value | Represents |
|---|---|---|
| Preload F_i | 37 935 N (= 0.75 · A_t · Sp, A_t = 84.3 mm²) | assembly torque-up, the usual figure for a reusable joint |
| External tension P | 20 000 N | the design working load carried per bolt |
| Constraint | lower plate bottom face normal restraint + minimal rigid-body constraint | represents a connection to a rigid base; **this is a simplification, not the real structure** |
| Load sequence | Step 1 apply preload → Step 2 superpose external load | matches the actual assembly sequence |

## 5. Analytical reference (Shigley's cone method / same lineage as VDI 2230)

Used to judge whether the FEA result can be trusted. The cone method is itself
an approximation; expected deviation is on the order of 10–20%. Anything beyond
that means either the model or the analytical assumptions have broken down.

| Quantity | Analytical value |
|---|---|
| Bolt stiffness k_b = A_d E_b / l | 754.0 kN/mm |
| Clamped-member stiffness k_m (30° double cone) | 3057.5 kN/mm |
| Stiffness ratio C = k_b/(k_b+k_m) | 0.1978 |
| Bolt elongation δ = F_i·l/(A_d·E_b) | 0.0503 mm |
| Bolt force under load F_b = F_i + C·P | 41 891 N |
| Bolt stress σ_b = F_b/A_t | 496.9 MPa (Sp = 600) |
| Residual clamp force F_m = F_i − (1−C)·P | 21 891 N (> 0 → no separation) |
| Separation load P_0 = F_i/(1−C) | 47 290 N |
| Separation safety factor n_0 = P_0/P | 2.36 |

## 6. Assumption register

Every assumption carries a **machine-checkable condition that would invalidate
it**. Checked against the result after solving; anything overturned must be
reported.

| # | Assumption | Why | Invalidated when (check after solving) |
|---|---|---|---|
| A1 | Linear elastic, small deformation | design intent is to stay elastic throughout | bolt max von Mises ≥ 600 MPa, or plate ≥ 355 MPa, or max displacement/grip length ≥ 5% |
| A2 | Joint stays closed | the analytical superposition only holds while preload is sufficient | any opening (gap > 0) at the plate–plate interface |
| A3 | Bolt shank does not touch the hole wall | purely axial load, Ø13 hole on a Ø12 shank | radial clearance between shank and hole ≤ 0 (contact occurs) |
| A4 | Thread not modelled, plain shank used | thread geometry has little effect on overall stiffness | **fails outright if the question involves fatigue or thread-root stress** — a thread-root Kt of roughly 3–4 is not captured |
| A5 | Bearing-face friction μ = 0.15 | typical value for dry steel-on-steel | tangential/normal force at the contact ≥ μ (slip occurs) |
| A6 | Washer omitted | head bears directly on the plate | contact pressure at the bearing face ≥ plate yield 355 MPa (crushing) |
| A7 | The pressure cone fully develops within the plate | precondition of Shigley's k_m formula | required cone outer diameter 18 + 2·30·tan30° = **52.6 mm** vs plate width 60 mm — satisfied, but only 3.7 mm to spare on each side. If plate width were below 52.6 mm, k_m would be overestimated and C underestimated |
| A8 | Full restraint on the lower plate's bottom face represents a rigid base | boundary simplification | if the reaction distribution on that face is markedly uneven, base stiffness cannot be neglected |
| A9 | Preload is exactly 37 935 N | for a clean comparison against the analytical value | **real torque-controlled preload scatters ±25–35%**. This model does not represent assembly scatter; any margin judgement drawn from it needs that scatter accounted for separately |

## 7. Accuracy required

This supports a binary "is the selection right" decision, not a life
prediction. So:

- separation criterion and peak bolt stress: agreement with the analytical
  value within **±20%** is enough to support the decision
- stiffness ratio C: **±20%** (the cone method's own accuracy is at that order)
- no life, no reliability, no uncertainty quantification

## 8. Explicitly out of scope

Material nonlinearity, thread geometry, assembly scatter, temperature,
vibration loosening, fatigue, load distribution across multiple bolts.

## 9. Status

- [x] problem definition
- [ ] geometry
- [ ] mesh
- [ ] solve
- [ ] assumption recheck
