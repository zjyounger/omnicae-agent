# OmniCAE Agent — Project Objective and Architecture

## Objective

Make reliable engineering analysis accessible to people who lack the software
skills, specialist experience, or resources to carry it out themselves.
OmniCAE aims to be an assistant for engineers, a place where experienced
engineers contribute reusable knowledge, and a digital engineering consultant
for small companies and individuals without their own CAE capability.

The intention is for these roles to support one another: engineers use and
correct the assistant in real work, and contributors help make that experience
reusable for users who could not perform the same analysis independently.
Collecting, questioning, and improving engineering experience is itself part
of the project's open-source purpose.

The technical objective is a fully open-source, self-hostable CAE agent that
can understand an engineering problem, choose and operate suitable analysis
software, inspect what actually happened, recover from failures, and report a
conclusion with its assumptions, evidence, confidence, and limits.

The long-term aim is an open alternative to a closed CAE ecosystem: models are
replaceable, applications are replaceable, and contributors can add support
for another solver or engineering field without changing the whole system.

The agent is not finished when software produces a result. It is finished when
the result is understood well enough for the decision at hand and the limits of
that understanding are visible.

## People and the assistance they need

Software familiarity, engineering foundations, and domain experience are
different things. The project should help with each without assuming that
removing one barrier removes the others:

- An engineer who knows the domain but not the software needs reliable
  execution and a clear way to inspect and direct the work.
- An engineer entering another domain needs help choosing methods, recognising
  missing physics, and checking interpretations. A structural engineer who has
  studied fluid dynamics may be able to undertake suitable CFD projects with
  this assistance, while still needing specialist input for unfamiliar regimes.
- A small company or individual with little CAE background may understand the
  equipment and operating problem well. They need help translating that
  knowledge into an analysis question, supplying relevant information, and
  understanding what the result means for their decision.

The digital consultant is a long-term goal. Build confidence in specific tasks
through reviewed methods and cases, and expand their scope as evidence supports
it. Do not imply that operating a solver establishes expertise across a field.

Progress should be judged by useful time saved for engineers, whether a
contributed lesson improves subsequent work, and whether users with fewer CAE
resources can make better-supported decisions. Tool coverage and generated
artifacts support these outcomes; they do not establish them on their own.

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

People remain involved in defining the real question and deciding how the
conclusion will be used. The agent must help users understand those choices;
user approval alone does not establish technical validity. Experienced
contributors also help review methods, cases, and corrections. Autonomy is
earned one procedure at a time from validation and override records; it is not
declared for the agent as a whole.

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
user (engineer, small company, or individual)
   │ defines the question with assistance and decides how to use the conclusion
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

Engineering experience should retain the context, reasoning, evidence, and
limits that make it useful. Observations, hypotheses, and supported conclusions
need to remain distinguishable; unsuccessful attempts can also teach something
valuable. The aim is to help another user or agent understand when a lesson
applies and when to question it.

The representation of that experience and the mechanisms for judging its
quality remain to be designed. The [open design questions](#experience-quality-direction-and-open-questions)
are more central to this goal than the choice of retrieval backend.

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

A contributor should not need to write code or understand the entire agent.
We need engineers to contribute and challenge engineering judgment, users to
explain real needs and report misleading assistance, and developers to improve
execution and observation. Independently valuable contributions include:

- one explanation of a modelling decision and the conditions that justify it;
- one correction to an agent's reasoning, with the evidence that changed it;
- one review or independent reproduction of someone else's analysis;
- one practical problem that exposes missing information or capability;
- one failure record, including unsuccessful attempts and unresolved questions;
- one engineering procedure with applicability and invalidation conditions;
- one public benchmark with a reference result and its uncertainty or limits;
- one application method or capability;
- one input or result reader;
- one verified inspector or reusable script;
- one retrieval or storage adapter.

Every contribution must identify its evidence and how its behaviour was
checked, or explicitly state what remains untested. An unresolved observation
can be useful without being accepted as a verified method. For engineering
claims, “the program ran” is not a verification.

### Experience quality: direction and open questions

The direction is to make engineering experience an open, reusable contribution
that improves the assistance available to less experienced users. Contributing
engineering judgment should not require software development skills.

How to collect, assess, maintain, and authorise the agent's use of experience
is still an open design problem. More records do not necessarily mean better
guidance: duplicates, contradictions, outdated advice, and unsupported claims
can degrade the system. Receiving an account of experience must not by itself
make that account an accepted instruction for the agent.

Further design needs to address how to distinguish duplicate advice from
independent corroboration, recognise differences in applicability, assess
evidence and conflicting judgments, and determine whether new guidance improves
subsequent work without causing regressions. Review responsibilities and the
handling of corrections or withdrawal also remain unresolved.

These questions need iterative design and evaluation against concrete cases.
This document establishes the purpose and quality concerns, not a submission
format, review workflow, acceptance policy, or automatic learning mechanism.

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
