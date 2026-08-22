# R2R distribution baseline

## Purpose

This measurement answers whether a contributor must rebuild the CalculiX RAG
index before using it.

## Measured configuration

- R2R 3.6.5;
- PostgreSQL 16 with pgvector;
- Ollama `mxbai-embed-large`, 1,024 dimensions;
- complete generated CalculiX 2.23 corpus: 4,670 chunks;
- local RTX 5070 Ti for the fresh embedding run.

## Results

| Operation or artifact | Observed result |
|---|---:|
| final live PostgreSQL logical database | 89,791,511 bytes |
| final live PostgreSQL data directory | 206,297,419 bytes |
| final compressed custom-format `pg_dump` | 24,748,358 bytes |
| final dump time | 2.06 s |
| isolated restore time | 0.99 s |
| restored logical database | 43,703,319 bytes |
| restored contents | 1 document, 4,670 chunks |
| clean parse/embed/store run | 77.11 s |

The isolated restore used the immediately preceding 24,761,383-byte snapshot;
the final snapshot was regenerated after caption-aware corpus replacement. The
content count remained one document and 4,670 chunks. The difference between
the live and restored logical sizes is expected from runtime history such as
dead tuples and logs.

## What the measurement establishes

- A compressed snapshot of the present corpus is about 25 MB and restores in
  about one second on this machine.
- A clean rebuild is also short on this GPU: about 77 seconds after the model
  and containers are already present.
- The snapshot does not include the R2R/PostgreSQL container images or the
  Ollama embedding model.
- CPU-only and lower-end machines have not been measured, so the 77-second
  rebuild time cannot be generalized.

## Decision

Do not distribute a database snapshot at this stage. Rebuild the disposable
index from the tracked corpus with `bootstrap_calculix.py`.

The measured clean build is short on the available GPU, while a PostgreSQL dump
is coupled to the selected R2R schema and version. A release snapshot would also
need a proven sanitization step for runtime users, authentication state, logs,
and other non-corpus rows. It would not remove the runtime requirement for the
query embedder. That maintenance burden is not justified by the current
measurement.

This decision must be revisited if CPU-only or lower-end-machine measurements
show that rebuild time is a practical adoption barrier. No such measurement
exists yet.
