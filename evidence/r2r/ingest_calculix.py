#!/usr/bin/env python3
"""Ingest the complete generated CalculiX corpus into the local R2R service."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from collections import defaultdict, deque
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
NAMESPACE = uuid.UUID("d7bc5ba2-0a7f-49a6-96ed-f7450b403641")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--base-url", default="http://127.0.0.1:7272")
    args = parser.parse_args()

    corpus_path = args.data / "corpus.jsonl"
    raw = corpus_path.read_bytes()
    corpus_hash = hashlib.sha256(raw).hexdigest()
    records = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    document_id = uuid.uuid5(NAMESPACE, corpus_hash)
    endpoint = args.base_url.rstrip("/")
    state_path = args.data / "r2r_state.json"
    previous_document_id = None
    if state_path.exists():
        previous_state = json.loads(state_path.read_text())
        previous_document_id = previous_state.get("document_id")

    existing = requests.get(
        f"{endpoint}/v3/documents/{document_id}", timeout=30
    )
    if existing.ok:
        print(f"already ingested: document={document_id}")
    else:
        print(
            f"ingesting {len(records)} chunks from the complete CalculiX corpus...",
            flush=True,
        )
        response = requests.post(
            f"{endpoint}/v3/documents",
            data={
                "chunks": json.dumps(
                    [record["embedding_text"] for record in records],
                    ensure_ascii=False,
                ),
                "id": str(document_id),
                "metadata": json.dumps(
                    {
                        "title": "CalculiX 2.23 CCX and CGX complete structured corpus",
                        "corpus_hash": corpus_hash,
                        "location_sidecar": "document_map.json",
                    }
                ),
                "ingestion_mode": "custom",
                "ingestion_config": json.dumps(
                    {
                        "automatic_extraction": False,
                        "skip_document_summary": True,
                    }
                ),
                "run_with_orchestration": "false",
            },
            timeout=3_600,
        )
        if not response.ok:
            raise SystemExit(
                f"ingestion failed ({response.status_code}): {response.text}"
            )
        print(response.text)

    chunks = requests.get(
        f"{endpoint}/v3/documents/{document_id}/chunks",
        params={"offset": 0, "limit": 1},
        timeout=30,
    )
    chunks.raise_for_status()
    payload = chunks.json()
    total = payload.get("total_entries")
    if total is None:
        total = payload.get("results", {}).get("total_entries")
    if total != len(records):
        raise SystemExit(f"chunk count mismatch: expected {len(records)}, got {total}")

    by_text: dict[str, deque[dict]] = defaultdict(deque)
    for record in records:
        by_text[record["embedding_text"]].append(record)
    locations: dict[str, dict] = {}
    for offset in range(0, total, 1_000):
        page = requests.get(
            f"{endpoint}/v3/documents/{document_id}/chunks",
            params={"offset": offset, "limit": 1_000},
            timeout=60,
        )
        page.raise_for_status()
        for remote in page.json()["results"]:
            candidates = by_text.get(remote["text"])
            if not candidates:
                raise SystemExit(f"cannot locate remote chunk {remote['id']}")
            local = candidates.popleft()
            locations[remote["id"]] = {
                key: value
                for key, value in local.items()
                if key not in {"text", "embedding_text"}
            }
    unmatched = sum(len(items) for items in by_text.values())
    if len(locations) != total or unmatched:
        raise SystemExit(
            f"location map mismatch: remote={len(locations)} unmatched={unmatched}"
        )
    if previous_document_id and previous_document_id != str(document_id):
        deleted = requests.delete(
            f"{endpoint}/v3/documents/{previous_document_id}", timeout=120
        )
        if deleted.status_code != 404:
            deleted.raise_for_status()
    (args.data / "chunk_locations.json").write_text(
        json.dumps(locations, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    state = {
        "document_id": str(document_id),
        "corpus_hash": corpus_hash,
        "chunks": len(records),
        "base_url": endpoint,
    }
    state_path.write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )
    print(f"verified: document={document_id} chunks={total} locations={len(locations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
