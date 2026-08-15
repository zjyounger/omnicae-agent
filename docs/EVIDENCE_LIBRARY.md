# Engineering Evidence Library

## Purpose

The Engineering Evidence Library lets the CAE agent locate the exact document,
code artifact, image, case, or experience record that bears on a question and
return enough provenance to inspect the source.

It is supporting infrastructure, not the core of the project. Retrieval finds
candidate evidence; it does not decide that the evidence applies to the current
physical problem or turn a retrieved claim into fact.

## Authoritative artifacts

The authoritative copy of an artifact is a repository file or an explicitly
declared public object. An index is derived state and must be rebuildable.

The library covers:

- public official documentation and references;
- complete reusable scripts, subroutines, and solver inputs;
- figures and tables with their document locations;
- engineering procedures and validation rules;
- public benchmarks and analysis records;
- structured records of observations, diagnoses, failures, and human
  corrections.

Complete code remains in Git. A search chunk may locate it, but is never
treated as runnable code.

## Evidence contract

Every result has a stable identifier and enough information to answer:

- What is the artifact?
- Where did it come from?
- Which version and licence apply?
- Is this official material, a project observation, or a community example?
- Is the claim observed, derived, hypothesised, or superseded?
- Has this project reviewed or validated it?
- Where is the complete source?

The common envelope contains, where applicable:

```yaml
id:
artifact_type: text | figure | table | script | subroutine | input_deck |
               procedure | experience | benchmark
title:
content:

source_path:
source_url:
source_version:
license:
content_hash:

solver:
solver_version:
language:
interface:

page:
bbox:
asset_path:
line_start:
line_end:

authority: official_documentation | public_reference | validated_benchmark |
           project_observation | community_example
claim_grade: observed | derived | hypothesised | superseded
validation_status: unreviewed | reviewed | validated | failed | superseded
validated_by:
```

Authority, claim grade, and validation status are independent. An official
manual can be wrong for the installed version; a community example can be well
validated; an observed symptom can still have only a hypothesised cause.

## Stable interface

The CAE agent depends on a project-owned interface:

```text
search_evidence(query, filters)
get_evidence(evidence_id)
get_artifact(artifact_id)
open_source_location(evidence_id)
```

It returns structured evidence or `insufficient_evidence`. It does not return
an unsupported synthesized answer in place of missing material.

Ingestion is a separate, controlled path. Sources pass provenance, licence,
schema, and content-hash checks before entering an index. An agent does not
silently write conversation text into the library.

## Backend independence

No retrieval product owns the corpus or its schema. A lightweight deployment
may use a local index or R2R. An organisation may index the same artifacts in
RAGFlow or another system. MCP may expose the stable query interface, while
native APIs remain available to project code.

Queries may continue while new artifacts are parsed and indexed. A new version
becomes visible only after its ingestion succeeds; previously indexed evidence
remains available during that work.

## Visual evidence

A visual result resolves to the original image or crop, source document, page,
bounding box, caption, OCR output, nearby text, and parser version. Native text
is preferred where available, and OCR remains identifiable rather than silently
replacing the source.

## Development

Parsers, chunking rules, backend adapters, repository layout, milestones, and
tests are implementation concerns recorded in
[development/EVIDENCE_LIBRARY.md](development/EVIDENCE_LIBRARY.md).
