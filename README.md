# OmniCAE Agent

A fully open-source, self-hostable agent for computer-aided engineering. An
engineer states the real problem; the system finds relevant evidence, chooses
and operates suitable software, checks what actually happened, recovers from
failures, and reports the conclusion together with its assumptions, confidence,
and limits.

The project is not another chat interface over manuals. Its durable assets are
application integrations, engineering tools, procedures, failure diagnoses,
validation rules, benchmarks, and records of people correcting the agent.

## Direction

```text
CAE agent core
├── application integrations: FreeCAD, CalculiX, Gmsh, cgx, ...
├── engineering methods: structural, fluids, thermal, ...
├── engineering evidence library
├── experience records
└── validation cases
```

Models, agent frameworks, MCP, and retrieval systems are replaceable.
Project-owned application integrations remain the control path. The system
must be able to say that the available software or evidence cannot support a
requested conclusion.

Application control is evidence-driven and incremental when live feedback
matters: observe state, take one bounded action, inspect its feedback, then
continue or release control to a person. A live GUI Bridge is optional; a batch
or command path is sufficient when it exposes the resulting state, artifacts,
and independent checks needed for the engineering decision.

## Open-source knowledge foundation

OmniCAE's reference knowledge implementation uses the open-source
[R2R framework](https://github.com/SciPhi-AI/R2R) (currently pinned to v3.6.5)
for document/chunk ingestion,
embedding storage, and semantic retrieval. R2R is the retrieval foundation; it
is not an OmniCAE-developed component and remains governed by its upstream
project and licence.

OmniCAE adds the CAE-specific layer around R2R: source manifests, domain
parsers, exact keyword/API lookup, document-tree navigation, source locations,
multi-need retrieval, and the read-only agent-facing MCP interface. Repository
source artifacts remain authoritative; the R2R index is derived and
rebuildable.

## Personal and organisational use

The same CAE knowledge layer supports two different deployment models:

| | Personal/open-source use | Organisation/enterprise use |
|---|---|---|
| Knowledge service | R2R, Ollama, and PostgreSQL run locally | R2R or an enterprise backend such as RAGFlow runs centrally |
| MCP connection | Each coding agent starts its own local `stdio` Evidence MCP | Users connect to one authenticated Streamable HTTP MCP service |
| Knowledge updates | Each user rebuilds the derived local index from repository artifacts | A managed ingestion process updates the shared index once |
| Data boundary | Queries and indexes remain on the user's machine unless they configure remote models or services | Access, private sources, retention, and backups are controlled by the organisation |
| Intended operation | Clone, bootstrap, and use without depending on an OmniCAE-hosted service | Central deployment maintained by the organisation's own infrastructure team |

The personal `stdio` mode is implemented and registered for Claude Code and
Codex in this repository. The shared authenticated HTTP MCP is an enterprise
deployment path, not a currently shipped OmniCAE service. Both modes can reuse
the same `EvidenceService`, CAE parsers, evidence contract, and permitted source
artifacts; an organisation does not need to recreate the domain layer.

The complete objective, architecture, repository strategy, and contribution
model are in [Project Objective and Architecture](docs/PROJECT.md).

## Implemented so far

- an in-process FreeCAD Bridge with a JSON-RPC client and thin MCP adapter;
- a persistent native Gmsh Bridge using the official pip-installed Python/FLTK
  API, with single-writer leases, state revisions, entity inspection, meshing,
  quality statistics, physical groups, human selection, and screenshots;
- a CalculiX batch job service that preserves solver logs, state, and hashed
  result artifacts;
- a one-window CGX controller that explicitly reports its xdotool transport as
  a gui-fallback and verifies commands with process, console, and visual
  evidence;
- shared atomic action records with before/after native state and stale-revision
  rejection, plus separate MCP adapters for Gmsh, CalculiX, and CGX;
- CAD, FEM setup, Gmsh meshing, and CalculiX solving through the Bridge;
- structured errors, capability discovery, path confinement, and hot reload;
- deck and result inspectors;
- evidence source manifests, deterministic content hashing, and provenance
  validation;
- an R2R-based knowledge system with a read-only Evidence MCP for exact API
  lookup, document navigation, authoritative source opening, and semantic
  retrieval;
- integration tests for protocol, security, reconnection, and failure paths.

See [PLAN.md](PLAN.md) for current work and immediate priorities.

## Working principle

In engineering, “the program ran” is not evidence. The model, mesh, and result
are means to an understanding; a plausible number without a known confidence
or applicability boundary is not a finished result.

Every computational simplification should therefore state the condition that
would invalidate it, and every important conclusion should resolve to concrete
artifacts that a person can inspect.

## Documentation

| Document | Purpose |
|---|---|
| [docs/PROJECT.md](docs/PROJECT.md) | project objective, system architecture, and repository strategy |
| [PLAN.md](PLAN.md) | current status and immediate work |
| [AGENTS.md](AGENTS.md) | working principles and routing for agents |
| [docs/ENGINEERING.md](docs/ENGINEERING.md) | how an analysis is defined, checked, and reported |
| [docs/EVIDENCE_LIBRARY.md](docs/EVIDENCE_LIBRARY.md) | formal role and interface of the engineering evidence library |
| [docs/development/EVIDENCE_LIBRARY.md](docs/development/EVIDENCE_LIBRARY.md) | evidence-library implementation decisions and milestones |
| [docs/BRIDGE.md](docs/BRIDGE.md) | current FreeCAD Bridge contract and behaviour |
| [docs/MCP_ADAPTER.md](docs/MCP_ADAPTER.md) | thin MCP adapter decisions |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | general lessons from building application integrations |
| [integrations/README.md](integrations/README.md) | installation, application services, cooperative sessions, and live tests |
| [docs/development/INTERACTIVE_APPLICATION_BRIDGES.md](docs/development/INTERACTIVE_APPLICATION_BRIDGES.md) | interactive Bridge requirements, capability levels, and implementation checklist |
| [docs/development/AGENTIC_MESHING_ORCHESTRATOR.md](docs/development/AGENTIC_MESHING_ORCHESTRATOR.md) | meshing portfolio, evaluation design, milestones, and contribution units |
| [docs/AGENT_FAILURE_MODES.md](docs/AGENT_FAILURE_MODES.md) | ways the agent has fooled itself and concrete countermeasures |
| [docs/GAPS.md](docs/GAPS.md) | observed weaknesses in the open-source CAE stack |
| [docs/tools/](docs/tools/) | behaviour and traps of individual programs |

## Contributions and licensing

The intended contribution unit is small: one integration capability, reader,
inspector, procedure, experience record, or benchmark should be useful without
requiring a contributor to understand the whole system.

Code and corpus licensing, and the choice between a DCO and CLA, are still open
decisions. They must be settled before accepting outside contributions.
