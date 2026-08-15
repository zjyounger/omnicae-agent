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

Models, agent frameworks, MCP, and retrieval systems are replaceable. Native
application APIs remain the control path. The system must be able to say that
the available software or evidence cannot support a requested conclusion.

The complete objective, architecture, repository strategy, and contribution
model are in [Project Objective and Architecture](docs/PROJECT.md).

## Current state

The first vertical slice is structural static implicit analysis with CalculiX,
starting from an existing mesh and closing the result against an analytical
solution.

Implemented so far:

- an in-process FreeCAD Bridge with a JSON-RPC client and thin MCP adapter;
- CAD, FEM setup, Gmsh meshing, and CalculiX solving through the Bridge;
- structured errors, capability discovery, path confinement, and hot reload;
- deck and result inspectors;
- integration tests for protocol, security, reconnection, and failure paths.

The retrieval layer, general experience-record format, additional application
integrations, and broader benchmarks are not implemented yet. See
[PLAN.md](PLAN.md) for the current front rather than a speculative roadmap.

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
| [docs/AGENT_FAILURE_MODES.md](docs/AGENT_FAILURE_MODES.md) | ways the agent has fooled itself and concrete countermeasures |
| [docs/GAPS.md](docs/GAPS.md) | observed weaknesses in the open-source CAE stack |
| [docs/tools/](docs/tools/) | behaviour and traps of individual programs |

## Contributions and licensing

The intended contribution unit is small: one integration capability, reader,
inspector, procedure, experience record, or benchmark should be useful without
requiring a contributor to understand the whole system.

Original project code and documentation are released under the [MIT
License](LICENSE). Bundled third-party material retains its upstream terms; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The choice between a DCO and
CLA remains open and must be settled before accepting outside contributions.
