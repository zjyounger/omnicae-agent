# OmniCAE Agent — Project Objective and Architecture

## Objective

Build a fully open-source, self-hostable CAE agent that can understand an
engineering problem, choose and operate suitable analysis software, inspect
what actually happened, recover from failures, and report a conclusion with
its assumptions, evidence, confidence, and limits.

The long-term aim is an open alternative to a closed CAE ecosystem: models are
replaceable, applications are replaceable, and contributors can add support
for another solver or engineering field without changing the whole system.

The agent is not finished when software produces a result. It is finished when
the result is understood well enough for the decision at hand and the limits of
that understanding are visible.

## The problem being solved

Open-source CAE software is capable but fragmented. Documentation is difficult
to search, interfaces differ, experience is scattered, and many failures look
like success. An agent can remove much of the operational barrier, but it also
makes it easier to produce a professional-looking wrong answer.

The project therefore has two equally important responsibilities:

1. Operate engineering software reliably through explicit, inspectable
   interfaces.
2. Prevent software operation from being mistaken for engineering
   understanding.

People remain at the two ends: they define or approve the real question, and
they decide whether the conclusion can be used. Autonomy is earned one
procedure at a time from validation and override records; it is not declared
for the agent as a whole.

## What compounds

Agent frameworks, model providers, and retrieval products will change. They
are replaceable infrastructure. The durable project assets are:

- application integrations and their machine-readable capabilities;
- parsers, inspectors, runners, converters, and reusable engineering tools;
- engineering procedures and their applicability conditions;
- failure signatures, diagnoses, and recovery methods;
- validation rules and public benchmarks;
- records of a person overruling the agent, including why;
- public source material and traceable evidence used by those records.

Traditional RAG over manuals is useful, but it is not the centre of the
project. The difficult work is turning engineering experience into records
that another agent can apply without silently extending them beyond their
evidence.

## System shape

```text
engineer
   │ defines the question and accepts or rejects the conclusion
   ▼
CAE agent core
   ├── problem definition and assumption register
   ├── procedure selection and execution
   ├── evidence and experience retrieval
   └── validation and reporting
           │
           ├── application integrations
           │     ├── bridges
           │     ├── runners
           │     ├── input/result readers
           │     └── inspectors and converters
           │
           ├── engineering methods
           │     ├── structural
           │     ├── fluids
           │     ├── thermal
           │     └── shared modelling and validation rules
           │
           └── engineering evidence library
                 ├── public documentation
                 ├── reusable examples and scripts
                 ├── experience records
                 └── validation cases
```

The core depends on project-owned contracts, not on an LLM vendor, an agent
framework, a retrieval backend, or the private API of one CAE application.

## Application integrations

An integration is everything required to use one external application
reliably. Not every integration is a Bridge:

- FreeCAD requires an in-process Bridge because its GUI, Python runtime, and Qt
  lifecycle must be controlled from inside the host process.
- Gmsh uses a persistent native Bridge around its official Python/FLTK API;
  API calls and GUI events are serialized on the application's main thread.
- CalculiX uses a batch job service, input/result readers, and deck inspectors;
  it is not described as an interactive GUI Bridge.
- cgx has no supported native command channel. Its controlled-process adapter
  exposes the limitation and labels keyboard control as a gui-fallback.

All interactive integrations use an observed state revision and a single-writer
lease. A person can take the lease; an agent must observe native state again
before resuming. Each mutation produces a step record with exact arguments,
before/after state, acknowledgement, artifacts, and verification data. Details
are in [the interactive Bridge plan](development/INTERACTIVE_APPLICATION_BRIDGES.md).

Integrations are owned by application because compatibility, deployment,
failure modes, and tests are application-specific. Engineering categories such
as `fea`, `cfd`, `cad`, `meshing`, and `postprocessing` are capabilities, not
directory ownership. They mix analysis disciplines and workflow stages, and
one application may provide several of them.

Each integration will eventually declare a manifest such as:

```yaml
id: freecad
capabilities:
  - cad
  - preprocessing
  - meshing
  - structural_fea
  - visualisation
protocols:
  - json-rpc
optional_protocols:
  - mcp
```

Capability discovery allows the agent to find every available mesher or
post-processor without duplicating an application across directories.

## Engineering experience

Experience is not stored as an unqualified tip. A reusable experience record
must say what happened, how it was distinguished from alternatives, and where
it stops applying. Its conceptual fields are:

```yaml
context: software, version, analysis type, elements, model conditions
trigger: error, warning, unexpected result, or human correction
observation: concrete logs, files, images, and numbers
hypothesis: proposed explanation
test: observation that could refute the explanation
action: change that was made
outcome: what was observed after the change
applicability: conditions required for reuse
invalidation: conditions that make the record inapplicable
artifacts: source files, scripts, results, figures, and benchmark links
```

Observed facts, derived claims, hypotheses, and superseded explanations remain
distinguishable. A failed hypothesis is useful evidence and must not be erased
when a later explanation succeeds.

The exact record schema is a separate design task. It is more central than the
choice between R2R, RAGFlow, or another retrieval system.

## Trust model

There is no state in which a model is simply marked correct. Confidence comes
from evidence appropriate to the decision:

- the actual deck, mesh, result, screenshot, and log are inspected;
- intent is checked independently from the solver's own bookkeeping;
- simplifications carry machine-checkable invalidation conditions;
- important quantities are checked by an independent route where possible;
- reported precision does not exceed established numerical accuracy;
- unresolved assumptions remain attached to the conclusion;
- the system can return that current tools or evidence are insufficient.

Terminology follows ASME V&V 10 and V&V 20 where applicable rather than
inventing a parallel vocabulary.

## Repository strategy

The project remains a monorepo while the integration contract and contributor
model are forming. This keeps the complete system discoverable, enables shared
tests, and avoids imposing cross-repository version coordination on early
contributors.

The target organisation is:

```text
core/                         agent-independent contracts and orchestration
integrations/                 application-owned integrations
  freecad/
  calculix/
  gmsh/
  cgx/
engineering/                  application-independent methods and procedures
  structural/
  fluids/
  thermal/
knowledge/                    public documentation and references
examples/                     complete reusable public artifacts
cases/                        benchmarks and complete analysis records
tools/                        tools used by this project itself
docs/                         objectives, contracts, behaviour, and development
```

This is a target, not a reason for an immediate mechanical move. Existing code
moves only when the owning integration is being changed and tests can establish
that the move preserved behaviour.

An integration should move to a separate repository only when at least one
concrete pressure justifies the cost: an independent maintainer and release
cycle, incompatible licensing, unusually large dependencies or assets, or a
stable plugin contract that allows independent versioning. Repository splitting
is a deployment decision, not a taxonomy mechanism.

## Contribution units

A contributor should not need to understand the entire agent. Independently
valuable contributions include:

- one application method or capability;
- one input or result reader;
- one verified inspector or reusable script;
- one engineering procedure with applicability and invalidation conditions;
- one failure record with concrete evidence;
- one public benchmark;
- one retrieval or storage adapter.

Every contribution must identify its evidence and how its behaviour was
checked. For engineering claims, “the program ran” is not a verification.

## Replaceable infrastructure

The following are explicitly replaceable:

- LLM and embedding providers;
- agent frameworks and tool protocols;
- local or hosted execution environments;
- evidence indexing and retrieval systems;
- individual CAE applications where equivalent capabilities exist.

The evidence corpus remains file-based and reconstructable. A lightweight
retrieval backend may serve individual users; an organisation may index the
same public corpus and experience records in RAGFlow or another enterprise
system. Neither changes ownership of the underlying artifacts.

## Current front

The first vertical slice is structural static implicit analysis with CalculiX,
starting from an existing mesh and closing the loop against an analytical
solution. The FreeCAD integration is the first application integration. Current
status and immediate work are recorded only in `PLAN.md`.

## Licensing

Code and corpus may require different licences. The project must decide their
licences and whether contributions use a DCO or CLA before accepting the first
outside contribution; changing those terms later would require contributor
consent.
