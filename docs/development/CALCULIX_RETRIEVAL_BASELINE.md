# CalculiX full-corpus retrieval baseline

## Scope

This is an observed baseline, not a projected capability. The complete tracked
CalculiX 2.23 CCX and CGX HTML manuals were parsed by the project parser and
uploaded as custom chunks to the local R2R 3.6.5 evaluation service with
`mxbai-embed-large`:

- 820 HTML pages;
- 4,670 searchable chunks: 3,482 text, 532 code, and 656 figure companions;
- 5,821 image or equation occurrences retained in the document map;
- 4,670 of 4,670 R2R chunk IDs resolved to a project-owned source location.

HTML locations use the tracked source file, section anchor, and source lines.
No page number is invented for HTML. A PDF source must retain its real page and
bounding box. Figure chunks use explicit HTML captions where present, image alt
text, and nearby document text. Images without a source caption do not receive
an invented title. OCR has not been evaluated.

R2R did not parse the HTML in this experiment: ingestion used custom chunks
with automatic extraction disabled. These results measure retrieval over the
project-prepared corpus, not R2R's native document parsing or citation quality.

## Native R2R HTML comparison

R2R 3.6.5's native file API was subsequently exercised against the same full
manual set on 2026-08-21. Each HTML page was one stable R2R document. All 820
documents reached `success`, none produced zero chunks, and native recursive
chunking produced 2,782 chunks.

The project-supplied document metadata (`manual`, `source_file`, `source_id`,
and `source_path`) survived on every inspected chunk. Native parsing did not
produce the section path, HTML anchor, source lines, parent/previous/next
relationships, or resolvable image asset records required by the project. A
figure query locating the correct source page is therefore not counted as
returning the figure itself.

On the same 13 synthetic source-page queries, native hybrid retrieval measured:

| Route | Top 1 | Top 5 | Top 10 | MRR |
|---|---:|---:|---:|---:|
| R2R native HTML | 7/13 | 8/13 | 10/13 | 0.5712 |
| project parser + type-aware semantic | 9/13 | 12/13 | 12/13 | 0.8115 |

The native misses included fuzzy `*CLOAD`, CGX `anim`, and CGX von Mises. This
does not show that R2R is unsuitable: R2R remains the vector-backed retrieval
framework in both paths. It shows that the project parser's CAE-specific
document structure, artifact records, and locations are materially useful and
should remain the default CalculiX ingestion path.

The lifecycle cleanup deleted all 820 native experiment documents. A follow-up
search over their recorded document IDs returned zero stale results. The
separate project-prepared CalculiX document was not deleted.

## Synthetic regression query set

The initial 13-query set covers exact and unknown API terms, ordinary prose,
cross-references, Fortran subroutines, CGX commands, and figures. It is checked
into `evidence/r2r/calculix_queries.json` so every retrieval change can run the
same questions.

The questions were written after inspecting the manuals and intended target
pages. They test mechanics and catch regressions; they are not an independent
retrieval benchmark and must not be used to claim general performance.

Ranks below are the first occurrence of the correct source page. MRR is mean
reciprocal rank. The set is intentionally small and does not establish general
performance.

| Route | Top 1 | Top 5 | Top 10 | MRR |
|---|---:|---:|---:|---:|
| TOC-title lexical search | 6/13 | 7/13 | 8/13 | 0.4920 |
| R2R lexical | 2/13 | 2/13 | 2/13 | 0.1538 |
| R2R semantic | 9/13 | 12/13 | 12/13 | 0.7987 |
| R2R hybrid | 9/13 | 12/13 | 12/13 | 0.7987 |
| type-aware semantic | 9/13 | 12/13 | 12/13 | 0.8115 |

## What changed the design

- Exact API and command queries benefit from exact titles. The TOC-title search
  found `*CLOAD`, both figure sections, and the tested CGX commands at rank one.
- Semantic retrieval is necessary for unknown vocabulary. It found the pressure
  keyword at rank two and several explanatory passages at rank one where the
  TOC-title lexical search ranked the target below 100.
- Semantic retrieval still failed an important fuzzy API case: the `*CLOAD`
  keyword page ranked 20th for “apply a concentrated point force to selected
  nodes.” A larger vector did not solve the task.
- R2R hybrid was identical to semantic on this set. Its lexical-only route
  contributed little and must be inspected before it can be relied on.
- An earlier negative-control experiment added TOC-title and vector ranks. That
  was a category error: a directory is navigation, not a content score, so the
  experiment has been removed from the evaluator.
- Type-aware filtering moved the distributed-load Fortran target from rank
  three to rank two. Both images in the initial two-query smoke set returned
  the correct figure first after filtering semantic candidates to figure
  companions; the later ten-asset result is reported below.

## API catalogue experiment

A deterministic catalogue now contains 296 CCX keywords and CGX commands. It
stores the canonical name, first descriptive paragraph, syntax where present,
document path, section path, and source anchor. Exact lookup and fuzzy lexical
discovery run only over this compact catalogue and then open the source page.

Seven existing synthetic queries point to catalogue pages. The catalogue ranked
the expected page first for six: exact and fuzzy `*CLOAD`, fuzzy `*DLOAD`,
`*PRE-TENSION SECTION`, `*STATIC`, and CGX `anim`. The force-driven submodel
cross-reference ranked its labelled `*CLOAD` page fourth while returning
`*SUBMODEL` first; this query needs multiple acceptable labels in the held-out
evaluation rather than an answer forced by the old target.

## Context-scope experiment

After the source page was fixed, five synthetic usage questions compared one
locally selected chunk, that chunk plus one neighbour on each side, and the
complete keyword/command page. Marker coverage was complete for 4/5, 4/5, and
5/5 questions respectively. Mean context sizes were 639, 1,209, and 6,688
characters.

For all 296 API catalogue pages, complete-page text has a median size of 1,186
characters, a 90th percentile of 5,533, and a maximum of 29,701. In this HTML
manual each keyword or command page is already the reliable semantic section;
there is no consistent smaller subsection hierarchy to reconstruct. Complete
page opening is therefore the measured baseline for API material, with large
outliers requiring a later size policy.

## Project-task evaluation

Ten information needs were captured from `docs/GAPS.md`, `docs/tools/cgx.md`,
and existing case decks before retrieval was run. Acceptable source groups were
then assigned by inspecting the authoritative manual pages. The queries were
not rewritten after seeing results, but the labels have not received independent
human review.

A task counts as retrieved only when every required source group is present.
This matters for workflows that need several commands or both a keyword card and
a user-subroutine interface.

| Route | Top 1 | Top 5 | Top 10 |
|---|---:|---:|---:|
| API catalogue | 3/10 | 5/10 | 6/10 |
| TOC-title lexical search | 0/10 | 0/10 | 1/10 |
| R2R semantic | 3/10 | 7/10 | 8/10 |

The main misses were multi-source tasks. Selecting and exporting a CGX surface
requires the `enq`, `comp`, and `send` references; displaying von Mises needs
both the predefined calculation and dataset-display command. One global top-k
query did not recover the complete command chains.

After human approval, those ten fixed tasks were decomposed into 16 explicit
information needs. Each need independently queried the API catalogue and R2R
semantic route. A task still counted only when all of its needs were covered.

| Explicit-need route | Top 1 | Top 5 | Top 10 |
|---|---:|---:|---:|
| API catalogue | 3/10 | 5/10 | 8/10 |
| R2R semantic | 5/10 | 9/10 | 9/10 |
| union of route candidates | 7/10 | 10/10 | 10/10 |
| route union plus explicit manual cross-references | 7/10 | 10/10 | 10/10 |

The union is candidate coverage, not score fusion. Explicit content links did
not improve this result because the finer queries already located all required
sources by Top 5, but links are preserved as inspectable navigation evidence.
The decomposition and labels have not received independent human review, so
10/10 is a regression result for this fixed set, not a general quality claim.

## Visual-asset experiment

The first parser associated images only with alt and nearby text. Direct visual
inspection exposed caption drift between adjacent figures even though the HTML
contains explicit `<CAPTION>` elements. Caption extraction is now bound to the
following image and tested against the coarse/fine mesh refinement sequence.

Ten manually verified assets cover element diagrams, CGX GUI screenshots, field
contours, a time-history graph, and an equation. Success is the exact image path,
not merely the correct HTML page.

| Route | Top 1 | Top 5 | Top 10 |
|---|---:|---:|---:|
| semantic among all chunks | 2/10 | 9/10 | 9/10 |
| semantic results filtered to figures | 8/10 | 10/10 | 10/10 |
| caption-weighted lexical figure search | 8/10 | 10/10 | 10/10 |

The query set was written after the assets were visually inspected, so it is a
visual regression set rather than an unbiased benchmark. OCR is still absent.
The CGX main-window screenshot was semantic figure rank two and raw rank 26;
text visibly printed inside a GUI or contour remains the clearest case for a
later identifiable OCR experiment.

## MCP agent-use check

The read-only Evidence MCP was tested with an agent question that did not name
the expected command: selecting nodes by rectangular coordinates with a
tolerance. This exposed a weakness hidden by the regression wording: an earlier
query used "enquire", which made `enq` artificially easy to retrieve.

After indexing CGX command-page body text and requiring complete command-token
matches for the catalogue bonus, `enq` ranked first. In the final agent run the
agent used one retrieval/opening sequence, returned the command syntax, and
cited `knowledge/calculix/CalculiX/cgx_2.23/doc/cgx/node95.html`. This is an
end-to-end use check, not a general retrieval-quality score.

A later live Codex MCP check confirmed the route distinction: for "select
nodes by rectangular coordinates with tolerance", the API catalogue ranked
`enq` first while raw R2R semantic retrieval ranked `qdis` first. The agent can
reach the right source through the route union, but this query is concrete
evidence that semantic ranking must not replace the exact API catalogue.

## Next experiment

Keep the corpus and synthetic query set fixed for regression, then measure these
changes independently:

1. agent traversal of the actual TOC followed by direct source opening;
2. identifiable OCR on visual text where caption and nearby text are
   insufficient;
3. R2R full-text configuration and tokenization, because the present lexical
   baseline is not useful.

Do not add a reranker or change the embedding model until exact lookup,
navigation, source opening, and context scope are measured. The present results
do not justify either change.
