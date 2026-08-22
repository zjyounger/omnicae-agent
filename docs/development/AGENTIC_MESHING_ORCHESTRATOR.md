# Agentic meshing orchestrator

## Objective

Build an open, evidence-driven orchestrator that can inspect a meshing task,
discover the available open-source tools, choose an appropriate mesher and
recipe, verify the resulting mesh, recover from diagnosed failures, and stop
honestly when the available portfolio cannot satisfy the engineering intent.

The goal is not to reproduce one commercial mesher. It is to make a portfolio
of replaceable open-source meshers more capable as a system than any fixed
default configuration, while preserving enough evidence for an engineer to
understand every acceptance, retry, and refusal.

This is a separate development programme because its benchmark, validation,
and contribution surface are substantial. Implementation changes arising from
this plan still require the architectural approvals defined in `AGENTS.md`.

## Why this can compound

Open-source meshers expose different algorithms, geometry assumptions,
parameterisations, optimisers, and failure modes. A difficult case for one
backend may be routine for another. The durable project asset is therefore not
a prompt that guesses parameters, but a growing public record of:

- geometry and task characteristics;
- available backend capabilities and versions;
- the exact recipe attempted;
- structured state and artifacts before and after the attempt;
- independent validity and suitability checks;
- failure diagnosis and recovery action;
- applicability and invalidation conditions for reuse.

Each new backend, benchmark, validator, or diagnosed failure should improve
the whole portfolio without requiring contributors to understand every tool.

## Non-goals

- Reimplement MeshGems or promise industrial automatic hexahedral meshing.
- Treat one generic mesh-quality number as proof of solver suitability.
- Optimise visual appearance without preserving geometry and boundary meaning.
- Use an LLM's confidence as evidence that a mesh is valid.
- Depend on proprietary algorithms in the default path or public benchmark.
- Require a live GUI Bridge when files, native APIs, logs, and rendered
  artifacts provide sufficient feedback.

## Operating loop

```text
meshing intent
    -> discover available tool capabilities
    -> inspect geometry and required semantics
    -> choose backend and bounded recipe
    -> execute one attempt
    -> collect structured state and artifacts
    -> apply hard validity gates
    -> assess solver-specific suitability
    -> accept, retry with a diagnosed change, switch backend, or abstain
    -> record the complete episode
```

The orchestrator owns selection and recovery. Meshing algorithms remain owned
by their upstream applications. Validators are independent of the planner
wherever practical, so the component proposing a mesh is not the only
component judging it.

## Initial portfolio

| Application | Initial role | Status in this programme |
|---|---|---|
| Gmsh | surface and tetrahedral generation, optimisation, quality queries | first executable baseline; integration already exists |
| Netgen | independent surface/tetrahedral alternative | second backend candidate |
| MMG | remeshing, adaptation, and quality repair | recovery-stage candidate |
| SALOME/SMESH | geometry groups, filters, mesh editing, and multiple open algorithms | advanced preprocessing candidate |
| PrePoMax | CalculiX-oriented workflow and downstream solver-readiness evidence | workflow consumer; not treated as a general meshing backend |

SALOME's commercial MeshGems plugins are excluded from required capabilities,
benchmarks, examples, and acceptance criteria. An installation may report them
as optional proprietary capabilities, but the orchestrator must never select
them silently.

## Contracts to define before orchestration logic

### Meshing intent

A benchmark or user request must state at least:

```yaml
geometry: source artifact and units
physics: structural, thermal, CFD, or another declared use
solver: intended downstream consumer
dimension: surface or volume
element_families: permitted and preferred families
regions: boundaries, interfaces, groups, and names that must survive
size_controls: global and local requirements
feature_policy: features that must be resolved or may be suppressed
budget: element, wall-time, memory, and retry limits
acceptance: required checks and decision-specific tolerances
```

If intent is incomplete, the orchestrator asks for or records the missing
decision instead of manufacturing a universal quality target.

### Backend capability manifest

Every backend declares its application and algorithm versions, supported input
and output formats, dimensions, element families, geometry assumptions,
controls, optimisation methods, evidence channels, interaction level, and
licence class. Capability discovery reports the live installation rather than
assuming that an optional plugin exists.

### Attempt record

Every attempt records the input hashes, exact backend recipe, versioned tool
capabilities, resource use, native messages, output hashes, validation results,
diagnosis, and next decision. A retry must identify what changed and which
observation justified the change.

## Evaluation design

### Separate the backend envelope from orchestration quality

For each benchmark case, run a bounded, versioned set of permitted
backend/recipe combinations offline. If any combination passes every hard
gate, the case is *portfolio-solvable*. The best passing result under the
declared objective is the portfolio oracle for that case.

The primary orchestration metric is:

```text
orchestration recall =
    cases solved by the orchestrator
    / cases solvable by the bounded portfolio oracle
```

This distinction prevents an algorithmic limitation shared by all available
meshers from being reported as a planning failure. It also exposes the opposite
case: when a valid recipe exists but the orchestrator fails to find it.

The oracle is a measured upper bound for the declared recipe space, not proof
that no possible open-source algorithm can solve the case.

### Baselines

Every evaluation compares at least:

1. a fixed documented Gmsh recipe;
2. a fixed recipe from each additional backend;
3. a deterministic rule-based selector;
4. the agentic orchestrator under the same budget;
5. the bounded portfolio oracle.

An expert-created recipe can be added as a separate reference where a public
artifact and rationale are available. Tool versions, hardware, time limits,
and random seeds are fixed and reported.

### Hard acceptance gates

A mesh is unsuccessful if any gate required by its intent fails. Candidate
gates include:

- all required domains are represented and no unintended domain is meshed;
- no invalid, inverted, duplicate, or illegally intersecting elements;
- geometric deviation, area, and volume remain within declared tolerances;
- required boundaries, interfaces, groups, and orientations survive;
- the output respects permitted element families and the resource budget;
- the target solver imports the mesh without semantic loss;
- a declared smoke solve completes where the case requires one;
- benchmark quantities meet their accuracy or convergence requirement.

Thresholds are solver-, element-, and decision-specific. They belong to the
case or engineering method, not to a universal orchestrator constant.

### Performance after validity

Passing meshes are compared as a Pareto set rather than collapsed immediately
into one quality score. Report at least:

- solver-relevant quality distributions and worst locations;
- geometric fidelity;
- element and node counts;
- meshing and validation wall time;
- downstream solver convergence and cost when available;
- number of attempts and backend switches;
- human interventions;
- regret relative to the portfolio oracle under the declared objective.

Returning a confidently invalid mesh is worse than abstaining. False acceptance
and unsupported claims are reported separately from ordinary failure to find a
recipe.

### Robustness and generalisation

Hold out geometry families, not only random files. Apply controlled
perturbations in scale, units, orientation, feature size, tolerances, and
backend availability. If a learned policy is introduced, benchmark test cases
and their derived variants remain outside its training and experience index.

### Benchmark ladder

| Level | Case class | Programme role |
|---|---|---|
| L1 | clean single-body CAD, surface and tetrahedral meshes | minimum viable evaluation |
| L2 | holes, fillets, thin regions, small features, multiple solids | first useful engineering scope |
| L3 | sliver faces, gaps, overlaps, tolerance defects, non-manifold inputs | geometry recovery scope |
| L4 | CFD boundary layers and narrow passages | advanced mixed-mesh scope |
| L5 | automatic hex or hex-dominant meshes for complex assemblies | research scope, not an MVP promise |

The first corpus should combine parameterised shapes with exact geometric
invariants, real openly licensed mechanical parts, deliberately corrupted
variants, and solver-backed cases with analytical or trusted numerical
references. Every external artifact requires source and licence metadata.

## Delivery stages

### M0 — Benchmark and evidence contract

- Define the meshing-intent, backend-manifest, attempt-record, and validation
  result formats.
- Implement a runner that preserves inputs, outputs, logs, versions, timings,
  and hashes.
- Curate a small L1/L2 corpus with independently known invariants.
- Publish fixed acceptance gates before measuring any agent.

**Exit:** another contributor can run one case and reproduce the same pass/fail
record without using an LLM.

### M1 — Single-backend baseline

- Enumerate a bounded Gmsh recipe set from live capabilities.
- Run fixed recipes and the bounded oracle on the initial corpus.
- Verify geometry fidelity, topology preservation, element validity, and a
  downstream CalculiX smoke solve where applicable.

**Exit:** the project knows which cases the initial Gmsh portfolio can solve,
at what cost, and why rejected results failed.

### M2 — Independent backend and deterministic selection

- Add Netgen or another independently implemented open backend.
- Add a deterministic selector based on explicit task and geometry features.
- Measure the gain from portfolio diversity before introducing agent planning.

**Exit:** tool selection demonstrably beats at least one fixed backend on the
published corpus, or the result shows that the added backend provides no value.

### M3 — Agentic diagnosis and bounded recovery

- Let the agent choose only from declared capabilities and recipes.
- Expose failure signatures and validators as structured observations.
- Permit bounded parameter changes, repair steps, backend switches, and honest
  abstention.
- Compare orchestration recall, regret, false acceptance, and cost against the
  deterministic selector and oracle.

**Exit:** the agent adds measured value beyond deterministic selection without
increasing silent invalid-mesh acceptance.

### M4 — Advanced preprocessing portfolio

- Evaluate SALOME/SMESH for grouping, mesh editing, and open algorithm
  composition.
- Evaluate MMG as an explicit repair/adaptation stage.
- Add human handoff only where interactive inspection changes the evidence or
  recovery outcome.

**Exit:** the programme demonstrates a reproducible recovery unavailable from
the initial generation-only portfolio.

### M5 — Broader physics and difficult element families

- Add solver-specific CFD, thermal, shell, mixed-element, and boundary-layer
  criteria one domain at a time.
- Treat robust automatic hexahedral meshing as a separate research track with
  its own benchmark and claims.

## Contribution units

Contributors can independently add:

- one openly licensed benchmark case with intent and expected invariants;
- one backend capability manifest or recipe family;
- one geometry, topology, mesh-quality, or solver-readiness validator;
- one reproducible failure signature and discriminating diagnosis;
- one repair or fallback action with applicability limits;
- one deterministic selection rule;
- one result viewer or evidence renderer;
- one benchmark report reproduced on a new platform or tool version.

Every contribution includes the artifacts that establish its behaviour.
Screenshots are welcome visual evidence, but they do not replace structured
checks of hidden state.

## Decisions deliberately left open

- Exact schemas and package boundaries.
- The second backend after Gmsh.
- Benchmark corpus size and redistribution terms.
- Whether selection remains rule-based, uses an LLM, or later includes a
  learned policy.
- Whether SALOME needs a persistent integration or only observable scripts and
  exported artifacts.
- Acceptance thresholds for each solver and physics domain.

These decisions are made from M0/M1 measurements and explicit human approval,
not invented while implementing an unrelated task.
