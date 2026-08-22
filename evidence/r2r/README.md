# R2R knowledge backend

OmniCAE Agent uses the open-source
[R2R framework](https://github.com/SciPhi-AI/R2R) as its reference semantic
knowledge backend. R2R provides ingestion, vector-backed storage, and semantic
retrieval; OmniCAE supplies CAE-specific parsing, navigation, provenance, and
agent tools around it.

The reference R2R deployment uses the local Ollama embedding model
selected by R2R v3.6.5's official `full_ollama.toml` configuration:

- model: `mxbai-embed-large`;
- output: 1024 dimensions;
- provider: Ollama;
- the R2R deployment is reproducible and its derived indexes remain disposable.

Upstream configuration:
[`py/core/configs/full_ollama.toml`](https://github.com/SciPhi-AI/R2R/blob/v3.6.5/py/core/configs/full_ollama.toml).

The normal contributor path is one command:

```bash
python3 evidence/r2r/bootstrap_calculix.py
```

It confirms or downloads the Ollama model, starts the pinned local R2R and
PostgreSQL services under the fixed Compose project name
`omnicae-r2r-evaluation`, rebuilds the tracked corpus, ingests it, and verifies
the source-location map. Docker and a running Ollama service are prerequisites.

No database snapshot is distributed. The index is derived from tracked source
artifacts; the measured 4,670-chunk rebuild took 77.11 seconds on the test RTX
5070 Ti. CPU-only rebuild time has not been measured.

The individual diagnostic steps remain available. Install or verify the model:

```bash
ollama pull mxbai-embed-large
python3 evidence/r2r/check_embedder.py
```

Verify the running model:

```bash
python3 evidence/r2r/check_embedder.py
```

Merge [`embedding.ollama.toml`](embedding.ollama.toml) into the configuration
used by R2R. When R2R runs directly on the host, the verifier and provider use
`http://127.0.0.1:11434` by default. When R2R runs in Docker, set
`OLLAMA_API_BASE=http://host.docker.internal:11434` and ensure the container can
resolve that host gateway.

The Ollama model store and generated vectors are local runtime data. Neither is
committed to Git.

Start the pinned evaluation service with:

```bash
docker-compose -f evidence/r2r/compose.yaml up -d
curl http://127.0.0.1:7272/v3/health
```

This deployment binds R2R only to localhost and keeps PostgreSQL in a named
Docker volume. The present compose file uses Linux host networking so R2R can
reach an Ollama service bound to the host loopback interface. It is an
evaluation backend, not an authoritative corpus store.

Build, ingest, and evaluate the complete tracked CalculiX 2.23 manuals:

```bash
python3 evidence/r2r/build_calculix_corpus.py
python3 evidence/r2r/ingest_calculix.py
python3 evidence/r2r/evaluate_calculix.py
python3 evidence/r2r/evaluate_context_scope.py
python3 evidence/r2r/evaluate_visual_retrieval.py
python3 evidence/r2r/evaluate_multi_source.py
```

This path uploads project-generated custom chunks with R2R automatic extraction
disabled. It does not test R2R's native HTML parsing.

The separate native-parser lifecycle uploads all 820 authoritative HTML pages
as individual R2R documents. It uses stable IDs per manual page, records hashes
for incremental add/update/rename/delete handling, audits the chunks and
location metadata R2R actually produces, and verifies corpus deletion:

```bash
python3 evidence/r2r/native_calculix.py inventory
python3 evidence/r2r/native_calculix.py sync
python3 evidence/r2r/native_calculix.py audit
python3 evidence/r2r/native_calculix.py delete
```

Generated state and command-specific sync, audit, and deletion reports stay
under `.evidence-data/`; a later lifecycle command never overwrites an earlier
report.
The command is an evaluation path; the measured custom-chunk path remains the
default semantic backend. The complete native audit produced 2,782 chunks from
820 non-empty documents, but retained only document-level location fields and
underperformed the project parser on the fixed retrieval regression. See the
recorded baseline for the measured comparison. The deletion check subsequently
removed all 820 native experiment documents and found zero stale search results,
without removing the project-prepared CalculiX corpus.

TOC navigation and exact source opening do not require R2R:

```bash
python3 evidence/r2r/navigate_calculix.py lookup --manual ccx --term CLOAD
python3 evidence/r2r/navigate_calculix.py discover --manual ccx \
  --query "How do I apply a concentrated point force to selected nodes?"
python3 evidence/r2r/navigate_calculix.py children --manual ccx --source node223.html
python3 evidence/r2r/navigate_calculix.py open --manual ccx --source node242.html
python3 evidence/r2r/navigate_calculix.py references --manual ccx --source node242.html
```

`lookup` is exact API/title resolution. `discover` searches only the generated
keyword/command catalogue for unknown vocabulary. `children` traverses the real
document tree. `open` reads the complete authoritative HTML page; it does not
reconstruct an answer from vector chunks.

For a task requiring several sources, the calling agent supplies explicit
information needs. Each need searches the API catalogue and semantic index
independently; route scores are never fused with each other or with the TOC.
The command also opens the first authoritative pages from each route and exposes
manual cross-references:

```bash
python3 evidence/r2r/retrieve_calculix.py \
  --task-id cgx-coordinate-surface-export
```

Generated corpus, source-location sidecars, R2R state, and evaluation results
are written under `.evidence-data/` and are not committed. The synthetic
regression queries and the baseline report remain in Git.

R2R is the semantic backend for the project-owned Evidence MCP. The MCP server
is [`../mcp_server.py`](../mcp_server.py), not the upstream raw `search`/`rag`
script bundled inside the R2R container.
