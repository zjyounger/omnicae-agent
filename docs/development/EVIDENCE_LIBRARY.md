# Engineering Evidence Library — Development Plan

This document records implementation choices and work sequence. The stable
purpose and interface are in [`../EVIDENCE_LIBRARY.md`](../EVIDENCE_LIBRARY.md).

## Status

The first E0 artifact is implemented: `evidence/` contains a machine-readable
source-manifest schema, deterministic file/tree hashing, provenance validation,
and tests. A local R2R 3.6.5 evaluation deployment, full CalculiX HTML parser,
296-entry keyword/command catalogue, TOC/exact-source navigator, location
sidecar, explicit multi-need retrieval runner, and regression-query runners are implemented under
`evidence/r2r/`. The observed first baseline is recorded in
[`CALCULIX_RETRIEVAL_BASELINE.md`](CALCULIX_RETRIEVAL_BASELINE.md). No
normalized experience/evidence-record schema has been implemented yet.

The first useful scope is retrieval over a complete, permitted CalculiX
documentation set. Do not validate on hand-picked excerpts: complete ingestion
is required to expose repeated vocabulary, cross-section ambiguity, missing
content, and broken locations. Do not expand to knowledge graphs, a new user
interface, or automatic experience ingestion until that retrieval path is
measured.

The measured CalculiX trial uses the project parser and R2R custom chunks
(`automatic_extraction=false`). It therefore measures embedding and retrieval
over project-prepared content, not R2R's native standard-document parser. R0's
native-injection lifecycle is implemented for all 820 HTML pages, with stable
per-page IDs and incremental add/update/rename/delete state. The live native
sync and audit are now measured: 820 non-empty documents produced 2,782 chunks.
Document-level manual, source file, source ID, and source path survived in
chunk metadata, but section paths, HTML anchors, source lines, and figure-asset
locations did not. Native retrieval underperformed the project parser on the
fixed regression set, so it remains a baseline rather than the default path.
The native lifecycle was also closed cleanly: all 820 experiment documents were
deleted, a follow-up search returned zero stale results, and the existing
project-prepared CalculiX corpus remained available.

Candidate sources after that baseline are assessed in
[`RETRIEVAL_SOURCES.md`](RETRIEVAL_SOURCES.md).
The measured size and rebuild cost of the current R2R state are recorded in
[`R2R_DISTRIBUTION_BASELINE.md`](R2R_DISTRIBUTION_BASELINE.md). The approved
current release path is a one-command clean rebuild; no database snapshot is
distributed.

## Design decisions

- Repository files and declared public objects are authoritative.
- Indexes and embeddings are derived and disposable.
- The project owns the evidence schema and retrieval interface.
- Retrieval backends are adapters.
- The implemented reference knowledge backend uses the open-source R2R
  framework. Its deployment is required for semantic retrieval, while exact
  lookup, document navigation, and source opening remain usable without it.
- RAGFlow is an optional enterprise adapter for users who want its UI,
  multi-user operation, and document pipeline.
- Docling is the initial candidate for structured document parsing.
- Code, solver inputs, and experience records use domain-specific parsers rather
  than a generic document chunker.
- The table of contents and section tree are first-class indexes, not incidental
  chunk metadata.
- Exact term/API lookup, document-map navigation, and semantic discovery are
  different operations. Directory position is never blended into a content
  score.
- Query and ingestion interfaces remain separate. The MCP surface is thin and
  read-only by default.

## Source layout

Use existing repository ownership rather than creating a backend-owned corpus:

```text
knowledge/                 official documentation and searchable references
knowledge/assets/          redistributable extracted figures when required
examples/                  complete reusable public scripts and solver inputs
cases/                     benchmarks and complete analysis records
docs/                      project observations, methods, and program behaviour
.evidence-data/            local derived index data; never authoritative
```

Large or non-redistributable sources require an explicit object-store or fetch
manifest. Public availability alone does not grant redistribution permission.

## Manifest and validation

Before a corpus is treated as reproducible project data, every source provides:

```yaml
id:
path_or_url:
source_version:
license:
redistribution: allowed | fetch_only
content_hash:
authority:
```

Schema validation rejects missing provenance. Incremental ingestion compares
stable identifiers and hashes, and handles add, update, rename, and delete. A
deleted source must not leave searchable orphan chunks.

The first controlled R2R trial uses a complete declared document set, not
hand-picked excerpts. This manifest is project provenance; it does not replace
or redefine R2R's document schema.

## Parsing and chunking

### Structured documents

The R0 native-parser comparison will upload standard documents through R2R's
native document API and inspect the chunks and citations it actually produces.
It does not introduce a project normalizer first. If that measured comparison
shows a parsing or chunking limitation, the later structured-document path is:

```text
PDF/DOCX/PPTX
    → Docling document model
    → project evidence normalizer
    → backend adapter
```

Use Docling's structure-aware hybrid chunking as a baseline. It begins from
detected document structure, splits only oversized chunks against the embedding
tokenizer, and may merge small adjacent peers under the same headings.

Project rules take precedence:

- do not cross unrelated section or keyword-card boundaries;
- retain document, section, parent, previous, next, and table-of-contents order
  identifiers on every child chunk;
- keep a table with its header, repeating the header when a table must split;
- keep figures and tables associated with their captions;
- retain PDF page and bounding-box provenance, HTML anchors or DOM locations,
  and source line ranges for code;
- create project-owned parent and neighbour identifiers;
- choose token limits from retrieval measurements, not convention.

Docling's default serializer does not traverse OCR text nested inside picture
items. The visual pipeline must opt in deliberately and keep OCR distinguishable
from native text.

### Solver documentation

CalculiX keyword cards are split by keyword and semantic section rather than by
fixed length. Syntax, parameter definitions, applicability limits,
cross-references, and examples retain their relationship through a parent
record.

### Code and solver artifacts

Code is indexed structurally:

- Fortran: module, subroutine, and function;
- Python: module, class, and function;
- CalculiX input: keyword section;
- cgx `.fbd`: logical command block;
- Gmsh `.geo`: geometry or mesh-field definition.

Each chunk resolves to the complete file and records lines, entry point,
dependencies, compatibility, licence, and validation status. Retrieval locates
a candidate; the complete source is the artifact.

### Visual evidence

The searchable companion for an image contains:

```text
section path
+ figure or table caption
+ OCR text inside the image
+ relevant text immediately before it
+ relevant text immediately after it
```

The payload retains the image or crop, source, page, bounding box, OCR output,
nearby text, and parser version. The first implementation uses public parsers
and public evaluation material.

## Collections and filters

Collections express broad source boundaries:

- `official-documentation`
- `public-references`
- `public-examples`
- `validated-benchmarks`
- `project-experience`

Controlled metadata provides precise filtering by application, capability,
solver version, artifact type, language, interface, authority, claim grade,
validation status, and licence.

## Retrieval pipeline

The calling agent first states every distinct information need. This is explicit
input, not a hidden classifier. Each need then uses the cheapest route that can
identify its source:

```text
task → explicit information needs
                ↓
             one need
  ├── known keyword/API → exact index → authoritative page
  ├── identifiable topic → inspect TOC → authoritative section
  └── unknown vocabulary → lexical/semantic discovery
                              ↓
                   resolve candidate into document map
                              ↓
                    open authoritative source
                              ↓
              follow explicit content cross-reference when needed
```

The document map is presented as a compact tree that an agent can traverse. It
does not participate in score fusion. A semantic result is a pointer into that
tree, not the final context sent to the agent. Once the source is known, opening
one chunk, neighbours, a subsection, or a complete page is evaluated separately.
For compact keyword cards, opening the complete page is the first baseline.

Scores are comparable only within the route that produced them. A reranker may
later reorder semantic candidates, but it is not a substitute for exact lookup
or TOC navigation.

Candidate sources from independent routes may be unioned to obtain coverage;
that is not score fusion. Completion is evaluated at task level: every explicit
information need must resolve to at least one acceptable authoritative source.

## Backend adapters

### R2R reference adapter

The implemented semantic route uses the open-source R2R framework through its
REST API for document/chunk ingestion and vector retrieval. OmniCAE does not
own or reimplement R2R. The adapter does not depend on R2R's chat or agent
interfaces, and its deployment remains reproducible from repository artifacts.

Preparation baseline: the upstream R2R repository currently exposes a v3 REST
API, offers an optional Python SDK, and documents both a light Python launch and
a full Docker deployment. The current custom-chunk trial uses the document and
search endpoints but bypasses native parsing. The project adapter targets REST
rather than importing the SDK. R2R v3.6.5 and PostgreSQL/pgvector are pinned in
the reproducible Compose deployment; their runtime and derived database are not
committed to this repository.

The local embedder used by the reference deployment is configured under
`evidence/r2r/`. It uses
R2R v3.6.5's official Ollama choice, `mxbai-embed-large` with 1024 dimensions,
and has a local health check.

The current trial ingests all generated chunks as one R2R document and maps
remote chunk IDs back to source locations through a local sidecar. That is
an identified limitation of the initial ingestion experiment. Before a
release-scale corpus, ingestion must use stable source/artifact-sized documents,
support incremental replacement and deletion, and preserve a stable project
chunk ID in backend metadata rather than infer identity from repeated text.

### Enterprise adapter

RAGFlow is not part of the default installation. An organisation may ingest the
same corpus and experience records into RAGFlow and use its document pipeline,
UI, access model, or MCP server. Compatibility is established at the evidence
contract, not by copying runtime databases.

### MCP

The implemented `evidence-library` MCP adapter wraps the project-owned
`EvidenceService` and exposes four stable read operations: exact lookup,
document-map navigation, authoritative source opening, and explicit multi-need
retrieval. R2R remains the semantic route behind that service. The upstream R2R
`search`/`rag` MCP script is deliberately not exposed. Ingestion remains a
manifest-driven native API or CLI workflow unless an explicit reviewed write
tool is later justified.

## Delivery sequence

### R0 — native standard-document injection

1. Inventory the permitted CalculiX documentation and identify the complete
   versioned set used by the test.
2. Add the smallest reproducible R2R deployment.
3. Upload the complete set through R2R's native document API without a custom
   experience-record schema.
4. Separately capture its table of contents, section tree, and exact source
   locations; measure which of those survive native parsing.
5. Inspect document state, generated chunks, metadata, citations, deletion,
   and search results.
6. Record a synthetic regression set and the observed API payloads. Do not use
   that set to claim general retrieval quality.

Exit: the complete CalculiX test corpus can be ingested, searched, cited, and
removed through the native R2R API; corpus coverage, document hierarchy,
locations, and actual chunk behaviour are recorded.

### E0 — provenance and the thin retrieval adapter

1. Apply the source-manifest contract to the selected corpus. **Schema,
   identity, hashing, and validation are implemented.**
2. Record source and corpus licensing decisions.
3. Implement only the adapter fields required by the observed R2R REST
   payloads.
4. Add clean rebuild and incremental update tests.

Exit: the tested corpus is reproducible from declared sources, and replacing
R2R requires changing an adapter rather than the source artifacts.

### E1 — CalculiX text baseline

1. Measure native R2R parsing and retrieval over the complete permitted
   CalculiX documentation set and existing keyword cards.
2. Introduce Docling or custom keyword-card chunking only where the baseline
   demonstrates a specific failure.
3. Build a held-out task set from real agent information needs before inspecting
   retrieval results. Keep the present synthetic set only for regression.
   **Ten project-derived tasks are now fixed and measured; labels were assigned
   after candidate capture and still require independent human review.**
4. Evaluate exact lookup, agent TOC navigation, and semantic discovery according
   to their own contracts. Do not put TOC navigation into a content-ranking
   table.
5. After each route locates a source, compare chunk, neighbour, subsection, and
   complete-page reads and record whether the resulting context answers the
   task with an exact source location. **For the CalculiX HTML API catalogue,
   the first synthetic measurement is complete: full-page reads covered 5/5
   tested tasks versus 4/5 for a chunk or immediate neighbours.**

Exit: the evaluation reports corpus coverage, TOC navigation success and source
opens, semantic reciprocal rank and top-k recall, exact-source location rate,
context reconstruction, and figure/code location success. Every accepted result
opens the authoritative source. Targets are set only after a held-out task set
exists.

### E2 — code artifacts

1. Add structural parsing for the first required code and solver formats.
2. Index existing public examples with controlled metadata.
3. Resolve every search chunk to a complete source file.
4. Test application, interface, version, and validation filters.

Exit: the agent can locate a relevant artifact, state its compatibility and
validation status, and open the complete source.

### E3 — visual evidence

1. Extract figures and tables with page coordinates.
2. Preserve native text and produce identifiable OCR text.
3. Associate captions and nearby text. **Explicit HTML captions are now bound
   to CalculiX image assets and exact-asset retrieval is measured on ten
   visually inspected queries.**
4. Return the visual artifact through the stable interface.
5. Test diagrams, screenshots, tables, plots, and equations separately.

Exit: the correct visual artifact opens at the correct source region and the
system can explain which text caused the match.

### E4 — alternate deployments

1. Verify clean rebuild and incremental update with the reference backend.
2. Add an optional thin MCP adapter. **Implemented and activated for the local
   CalculiX corpus.**
3. Document how an enterprise deployment can map the same contract into
   RAGFlow without changing source artifacts.
4. Document local-only model configuration and what leaves the machine when an
   external parser, embedding, reranking, or generation provider is used.

Exit: replacing the retrieval backend requires changing an adapter, not the CAE
agent, evidence schema, or source corpus.

## Required tests

- clean rebuild from authoritative artifacts;
- deterministic artifact inventory and content hashes;
- incremental add, update, rename, and delete;
- no stale search result after source removal;
- exact source-path and location resolution;
- official-only and validated-only filtering;
- complete-code resolution;
- image, page, and bounding-box resolution;
- retrieval regression against the synthetic smoke queries;
- held-out evaluation from real agent information needs;
- full-corpus coverage and orphan detection;
- table-of-contents traversal and exact section opening;
- route-specific evaluation without cross-route score fusion;
- parent, previous, and next reconstruction;
- concurrent query while a new source is being indexed;
- structured `insufficient_evidence` when retrieval cannot support an answer.

## Restraint

R0 comes first. E0 and E1 follow only from what the native injection baseline
actually shows. Normalized experience/evidence records, more corpus, more
models, and more retrieval features do not compensate for an unmeasured
standard-document baseline. The library remains subordinate to application
integrations, engineering tools, experience abstraction, and validation.
