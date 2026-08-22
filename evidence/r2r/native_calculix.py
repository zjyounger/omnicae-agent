#!/usr/bin/env python3
"""Exercise R2R's native HTML ingestion over the complete CalculiX manuals.

This is deliberately separate from ``ingest_calculix.py``.  That path measures
project-generated custom chunks; this one uploads each authoritative HTML page
as a standard R2R document and records what R2R's own parser preserves.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evidence.r2r.build_calculix_corpus import MANUALS


DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
NAMESPACE = uuid.UUID("4dc8cc4a-3d24-4d98-a0af-3d7db772671e")


@dataclass(frozen=True)
class NativeDocument:
    key: str
    manual: str
    source_file: str
    source_path: str
    content_hash: str
    document_id: str


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def inventory_documents(
    manuals: dict[str, Path] = MANUALS,
    repo_root: Path = REPO_ROOT,
) -> dict[str, NativeDocument]:
    inventory: dict[str, NativeDocument] = {}
    for manual, directory in sorted(manuals.items()):
        for path in sorted(directory.glob("*.html")):
            source_file = path.name
            key = f"calculix-2.23/{manual}/{source_file}"
            relative = path.relative_to(repo_root).as_posix()
            inventory[key] = NativeDocument(
                key=key,
                manual=manual,
                source_file=source_file,
                source_path=relative,
                content_hash=_file_hash(path),
                document_id=str(uuid.uuid5(NAMESPACE, key)),
            )
    return inventory


def sync_plan(
    previous: dict[str, dict[str, Any]],
    current: dict[str, NativeDocument],
) -> dict[str, list[str]]:
    old_keys = set(previous)
    new_keys = set(current)
    return {
        "create": sorted(new_keys - old_keys),
        "update": sorted(
            key
            for key in old_keys & new_keys
            if previous[key].get("content_hash") != current[key].content_hash
        ),
        "delete": sorted(old_keys - new_keys),
        "unchanged": sorted(
            key
            for key in old_keys & new_keys
            if previous[key].get("content_hash") == current[key].content_hash
        ),
    }


def _results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results", [])
    if isinstance(results, dict):
        results = results.get("results", [])
    return results if isinstance(results, list) else []


class R2RNativeClient:
    def __init__(self, base_url: str, session: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def document(self, document_id: str) -> dict[str, Any] | None:
        response = self.session.get(
            f"{self.base_url}/v3/documents/{document_id}", timeout=30
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        result = payload.get("results", payload)
        return result if isinstance(result, dict) else payload

    def create(self, item: NativeDocument) -> dict[str, Any]:
        path = REPO_ROOT / item.source_path
        metadata = {
            "source_id": item.key,
            "source_path": item.source_path,
            "source_file": item.source_file,
            "manual": item.manual,
            "source_version": "2.23",
            "authority": "official",
            "content_hash": item.content_hash,
        }
        with path.open("rb") as stream:
            response = self.session.post(
                f"{self.base_url}/v3/documents",
                files={
                    "file": (
                        f"calculix-{item.manual}-{item.source_file}",
                        stream,
                        "text/html",
                    )
                },
                data={
                    "id": item.document_id,
                    "metadata": json.dumps(metadata, ensure_ascii=False),
                    "ingestion_mode": "fast",
                    "ingestion_config": json.dumps(
                        {"skip_document_summary": True}
                    ),
                    "run_with_orchestration": "false",
                },
                timeout=3600,
            )
        response.raise_for_status()
        return response.json()

    def delete(self, document_id: str) -> None:
        response = self.session.delete(
            f"{self.base_url}/v3/documents/{document_id}", timeout=120
        )
        if response.status_code != 404:
            response.raise_for_status()

    def chunks(self, document_id: str) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = self.session.get(
                f"{self.base_url}/v3/documents/{document_id}/chunks",
                params={"offset": offset, "limit": 100},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            page = _results(payload)
            chunks.extend(page)
            total = payload.get("total_entries")
            if total is None and isinstance(payload.get("results"), dict):
                total = payload["results"].get("total_entries")
            if not page or (total is not None and len(chunks) >= total):
                return chunks
            offset += len(page)

    def search(
        self, query: str, document_ids: Iterable[str], limit: int = 10
    ) -> list[dict[str, Any]]:
        response = self.session.post(
            f"{self.base_url}/v3/chunks/search",
            json={
                "query": query,
                "search_settings": {
                    "use_semantic_search": True,
                    "use_fulltext_search": True,
                    "use_hybrid_search": True,
                    "limit": limit,
                    "filters": {
                        "document_id": {"$in": list(document_ids)}
                    },
                },
            },
            timeout=120,
        )
        response.raise_for_status()
        return _results(response.json())


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "documents": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != 1 or not isinstance(
        state.get("documents"), dict
    ):
        raise ValueError(f"unsupported native R2R state: {path}")
    return state


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _save_state(path: Path, documents: dict[str, dict[str, Any]]) -> None:
    _write_json(
        path,
        {
            "schema_version": 1,
            "backend": "R2R 3.6.5 native document API",
            "documents": documents,
        },
    )


def _record(item: NativeDocument) -> dict[str, Any]:
    return asdict(item)


def sync_corpus(
    client: R2RNativeClient,
    inventory: dict[str, NativeDocument],
    state_path: Path,
) -> dict[str, Any]:
    state = _read_state(state_path)
    recorded = dict(state["documents"])
    plan = sync_plan(recorded, inventory)
    actions = {name: [] for name in ("created", "updated", "deleted", "repaired")}

    for key in plan["delete"]:
        client.delete(recorded[key]["document_id"])
        recorded.pop(key)
        _save_state(state_path, recorded)
        actions["deleted"].append(key)

    for key in plan["update"]:
        client.delete(recorded[key]["document_id"])
        recorded.pop(key)
        _save_state(state_path, recorded)
        client.create(inventory[key])
        recorded[key] = _record(inventory[key])
        _save_state(state_path, recorded)
        actions["updated"].append(key)

    for key in plan["create"]:
        if client.document(inventory[key].document_id) is not None:
            raise RuntimeError(
                f"untracked deterministic document ID already exists: {key}"
            )
        client.create(inventory[key])
        recorded[key] = _record(inventory[key])
        _save_state(state_path, recorded)
        actions["created"].append(key)

    for key in plan["unchanged"]:
        if client.document(inventory[key].document_id) is None:
            client.create(inventory[key])
            recorded[key] = _record(inventory[key])
            _save_state(state_path, recorded)
            actions["repaired"].append(key)

    return {"plan": {name: len(keys) for name, keys in plan.items()}, **actions}


def audit_corpus(
    client: R2RNativeClient,
    inventory: dict[str, NativeDocument],
    queries_path: Path,
) -> dict[str, Any]:
    document_reports = []
    total_chunks = 0
    metadata_keys: set[str] = set()
    empty_documents = []
    for item in inventory.values():
        document = client.document(item.document_id)
        if document is None:
            raise RuntimeError(f"native document is missing: {item.key}")
        chunks = client.chunks(item.document_id)
        total_chunks += len(chunks)
        if not chunks:
            empty_documents.append(item.key)
        for chunk in chunks:
            metadata = chunk.get("metadata") or {}
            if isinstance(metadata, dict):
                metadata_keys.update(metadata)
        document_reports.append(
            {
                "key": item.key,
                "document_id": item.document_id,
                "status": document.get("ingestion_status")
                or document.get("status"),
                "chunks": len(chunks),
                "first_chunk": (
                    {
                        "id": chunks[0].get("id"),
                        "text": chunks[0].get("text", "")[:500],
                        "metadata": chunks[0].get("metadata"),
                    }
                    if chunks
                    else None
                ),
            }
        )

    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    ids = [item.document_id for item in inventory.values()]
    query_reports = []
    ranks: list[int | None] = []
    for query in queries:
        results = client.search(query["query"], ids)
        expected = (query["expected_manual"], query["expected_source"])
        rank = next(
            (
                index
                for index, result in enumerate(results, 1)
                if (
                    (result.get("metadata") or {}).get("manual"),
                    (result.get("metadata") or {}).get("source_file"),
                )
                == expected
            ),
            None,
        )
        ranks.append(rank)
        query_reports.append(
            {
                "id": query["id"],
                "query": query["query"],
                "expected_manual": query["expected_manual"],
                "expected_source": query["expected_source"],
                "expected_kind": query["expected_kind"],
                "expected_source_rank": rank,
                "results": [
                    {
                        "id": result.get("id"),
                        "document_id": result.get("document_id"),
                        "score": result.get("score"),
                        "text": result.get("text", "")[:500],
                        "metadata": result.get("metadata"),
                    }
                    for result in results
                ],
            }
        )
        time.sleep(3.1)

    return {
        "documents": len(document_reports),
        "chunks": total_chunks,
        "empty_documents": empty_documents,
        "chunk_metadata_keys": sorted(metadata_keys),
        "location_fields_surviving_in_chunk_metadata": sorted(
            metadata_keys & {"source_id", "source_path", "source_file", "manual"}
        ),
        "retrieval_metrics": {
            "queries": len(ranks),
            "top_1": sum(rank == 1 for rank in ranks),
            "top_5": sum(rank is not None and rank <= 5 for rank in ranks),
            "top_10": sum(rank is not None and rank <= 10 for rank in ranks),
            "mrr": sum(0.0 if rank is None else 1.0 / rank for rank in ranks)
            / len(ranks),
        },
        "document_reports": document_reports,
        "query_reports": query_reports,
    }


def delete_corpus(
    client: R2RNativeClient, state_path: Path
) -> dict[str, Any]:
    state = _read_state(state_path)
    recorded = dict(state["documents"])
    deleted_ids = []
    for key in sorted(list(recorded)):
        document_id = recorded[key]["document_id"]
        client.delete(document_id)
        if client.document(document_id) is not None:
            raise RuntimeError(f"document survived deletion: {key}")
        deleted_ids.append(document_id)
        recorded.pop(key)
        _save_state(state_path, recorded)
    stale = client.search("CalculiX", deleted_ids, limit=1) if deleted_ids else []
    if stale:
        raise RuntimeError("deleted native documents still return searchable chunks")
    return {"deleted": len(deleted_ids), "stale_search_results": len(stale)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "sync", "audit", "delete"))
    parser.add_argument("--base-url", default="http://127.0.0.1:7272")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()

    inventory = inventory_documents()
    state_path = args.data / "native_r2r_state.json"
    report_path = args.data / f"native_{args.command}_report.json"
    if args.command == "inventory":
        by_manual: dict[str, int] = {}
        for item in inventory.values():
            by_manual[item.manual] = by_manual.get(item.manual, 0) + 1
        print(json.dumps({"documents": len(inventory), "by_manual": by_manual}, indent=2))
        return 0

    client = R2RNativeClient(args.base_url)
    if args.command == "sync":
        result = sync_corpus(client, inventory, state_path)
    elif args.command == "audit":
        result = audit_corpus(
            client, inventory, Path(__file__).with_name("calculix_queries.json")
        )
    else:
        result = delete_corpus(client, state_path)
    _write_json(
        report_path,
        {
            "command": args.command,
            "base_url": args.base_url,
            "corpus_documents": len(inventory),
            "result": result,
        },
    )
    if args.command == "sync":
        display = {
            "plan": result["plan"],
            "created": len(result["created"]),
            "updated": len(result["updated"]),
            "deleted": len(result["deleted"]),
            "repaired": len(result["repaired"]),
        }
    elif args.command == "audit":
        display = {
            "documents": result["documents"],
            "chunks": result["chunks"],
            "empty_documents": len(result["empty_documents"]),
            "chunk_metadata_keys": result["chunk_metadata_keys"],
            "location_fields_surviving_in_chunk_metadata": result[
                "location_fields_surviving_in_chunk_metadata"
            ],
            "retrieval_metrics": result["retrieval_metrics"],
        }
    else:
        display = result
    print(json.dumps(display, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
