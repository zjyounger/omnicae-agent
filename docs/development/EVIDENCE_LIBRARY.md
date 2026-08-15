# Engineering Evidence Library — Development Plan

This document records implementation choices and work sequence. The stable
purpose and interface are in [`../EVIDENCE_LIBRARY.md`](../EVIDENCE_LIBRARY.md).

## Status

The first E0 artifact is implemented: `evidence/` contains a machine-readable
source-manifest schema, deterministic file/tree hashing, provenance validation,
and tests. This utility does not block an initial native R2R ingestion trial.
No retrieval service, ingestion pipeline, normalized experience/evidence-record
schema, or chunker has been implemented yet.

The first useful scope is retrieval over CalculiX official documentation. Do
not expand to broad OCR, knowledge graphs, a new user interface, or automatic
experience ingestion until that narrow retrieval path is measured.

## Design decisions

- Repository files and declared public objects are authoritative.
- Indexes and embeddings are derived and disposable.
- The project owns the evidence schema and retrieval interface.
- Retrieval backends are adapters.
- R2R is the initial candidate for a lightweight reference adapter, not a
  mandatory project dependency.
- RAGFlow is an optional enterprise adapter for users who want its UI,
  multi-user operation, and document pipeline.
- Docling is the initial candidate for structured document parsing.
- Code, solver inputs, and experience records use domain-specific parsers rather
  than a generic document chunker.
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

The first controlled R2R trial may upload a small declared sample before the
full manifest inventory is complete. This manifest is project provenance; it
does not replace or redefine R2R's document schema.

## Parsing and chunking

### Structured documents

The first baseline uploads standard documents through R2R's native document
API and inspects the chunks and citations it actually produces. It does not
introduce a project normalizer first. If that measured baseline shows a parsing
or chunking limitation, the later structured-document path is:

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
- retain the heading path on every child chunk;
- keep a table with its header, repeating the header when a table must split;
- keep figures and tables associated with their captions;
- retain page and bounding-box provenance;
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

## Backend adapters

### Reference adapter

Evaluate R2R through its REST API for document/chunk ingestion, embedding,
hybrid retrieval, and metadata filters. Do not depend on its chat or agent
interfaces. The reference deployment must remain optional and reproducible
from repository artifacts.

Preparation baseline: the upstream R2R repository currently exposes a v3 REST
API, offers an optional Python SDK, and documents both a light Python launch and
a full Docker deployment. The first trial uses the native document and search
endpoints directly. A project adapter is written only after observing that
contract; it targets REST rather than importing the SDK. No R2R package or
container is part of the default installation until an ingestion/search
conformance test exists.

### Enterprise adapter

RAGFlow is not part of the default installation. An organisation may ingest the
same corpus and experience records into RAGFlow and use its document pipeline,
UI, access model, or MCP server. Compatibility is established at the evidence
contract, not by copying runtime databases.

### MCP

If an MCP adapter is added, it wraps the project-owned retrieval client and
exposes the stable read operations. Ingestion remains a manifest-driven native
API or CLI workflow unless an explicit reviewed write tool is later justified.

## Delivery sequence

### R0 — native standard-document injection

1. Inventory the permitted CalculiX documentation and select a small sample.
2. Add the smallest reproducible R2R deployment.
3. Upload the sample through R2R's native document API without a project
   normalizer or custom experience-record schema.
4. Inspect document state, generated chunks, metadata, citations, deletion,
   and search results.
5. Record a small reviewed query set and the observed API payloads.

Exit: standard CalculiX documents can be ingested, searched, cited, and removed
through the native R2R API, and the actual chunk behaviour is recorded.

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

1. Measure native R2R parsing and retrieval over the permitted CalculiX
   documentation and existing keyword cards.
2. Introduce Docling or custom keyword-card chunking only where the baseline
   demonstrates a specific failure.
3. Build a reviewed query set covering keyword meaning, applicability,
   cross-references, and representative errors.
4. Record scores and missed queries as repository artifacts.

Exit: at least 90% of the reviewed queries retrieve the correct official source
in the top five, and every result opens the exact source location. This is an
initial engineering target, not a claim about current performance.

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
3. Associate captions and nearby text.
4. Return the visual artifact through the stable interface.
5. Test diagrams, screenshots, tables, plots, and equations separately.

Exit: the correct visual artifact opens at the correct source region and the
system can explain which text caused the match.

### E4 — alternate deployments

1. Verify clean rebuild and incremental update with the reference backend.
2. Add an optional thin MCP adapter.
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
- retrieval regression against reviewed queries;
- concurrent query while a new source is being indexed;
- structured `insufficient_evidence` when retrieval cannot support an answer.

## Restraint

R0 comes first. E0 and E1 follow only from what the native injection baseline
actually shows. Normalized experience/evidence records, more corpus, more
models, and more retrieval features do not compensate for an unmeasured
standard-document baseline. The library remains subordinate to application
integrations, engineering tools, experience abstraction, and validation.
