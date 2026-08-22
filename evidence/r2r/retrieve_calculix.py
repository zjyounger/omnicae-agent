#!/usr/bin/env python3
"""Retrieve explicit CalculiX information needs without score fusion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from evidence.r2r.evaluate_calculix import search_r2r, source_rank
    from evidence.r2r.navigate_calculix import discover_entries, source_blocks
except ModuleNotFoundError:  # Direct execution from the repository root.
    from evaluate_calculix import search_r2r, source_rank
    from navigate_calculix import discover_entries, source_blocks


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
DEFAULT_TASKS = Path(__file__).with_name("calculix_project_tasks.json")


def compact_candidate(candidate: dict) -> dict:
    keys = [
        "manual",
        "source_file",
        "source_path",
        "title",
        "canonical_name",
        "summary",
        "artifact_type",
        "kind",
        "excerpt",
        "section_path",
        "source_anchor",
        "line_start",
        "asset_path",
        "score",
    ]
    return {key: candidate[key] for key in keys if candidate.get(key) is not None}


def explicit_references(
    document_map: dict, candidates: list[dict], origin_limit: int = 5
) -> list[dict]:
    references = []
    seen = set()
    for origin in candidates[:origin_limit]:
        manual = origin["manual"]
        source_file = origin["source_file"]
        pages = document_map["manuals"][manual]["pages"]
        for target in pages[source_file].get("referenced_sources", []):
            key = (manual, target)
            if key in seen or target not in pages:
                continue
            seen.add(key)
            page = pages[target]
            references.append(
                {
                    "manual": manual,
                    "source_file": target,
                    "source_path": page["source_path"],
                    "title": page["title"],
                    "section_path": page["section_path"],
                    "referenced_by": {
                        "manual": manual,
                        "source_file": source_file,
                        "title": origin.get("title") or origin.get("canonical_name"),
                    },
                }
            )
    return references


def retrieve_need(
    need: dict,
    task_scope: list[str],
    document_map: dict,
    catalogue: list[dict],
    locations: dict,
    base_url: str,
    limit: int = 10,
) -> dict:
    scope = need.get("scope", task_scope)
    api = [
        result
        for manual in scope
        for result in discover_entries(catalogue, need["query"], manual, limit)
    ]
    api.sort(key=lambda item: item["score"], reverse=True)
    semantic = [
        result
        for result in source_rank(
            search_r2r(base_url, need["query"], "semantic", max(50, limit * 5)),
            locations,
        )
        if result["manual"] in scope
    ][:limit]
    api = api[:limit]
    return {
        "id": need["id"],
        "query": need["query"],
        "scope": scope,
        "routes": {
            "api_catalogue": [compact_candidate(item) for item in api],
            "semantic": [compact_candidate(item) for item in semantic],
        },
        "explicit_references": {
            "api_catalogue": explicit_references(document_map, api),
            "semantic": explicit_references(document_map, semantic),
        },
    }


def open_first_sources(result: dict, document_map: dict, count: int) -> list[dict]:
    selected = []
    seen = set()
    for route in ["api_catalogue", "semantic"]:
        for candidate in result["routes"][route][:count]:
            key = (candidate["manual"], candidate["source_file"])
            if key in seen:
                continue
            seen.add(key)
            manual_map = document_map["manuals"][candidate["manual"]]
            page, _, blocks = source_blocks(manual_map, candidate["source_file"])
            selected.append(
                {
                    "manual": candidate["manual"],
                    "source_file": candidate["source_file"],
                    "source_path": page["source_path"],
                    "title": page["title"],
                    "section_path": page["section_path"],
                    "blocks": blocks,
                }
            )
    return selected


def retrieve_task(
    task: dict,
    data: Path,
    base_url: str,
    limit: int = 10,
    open_top: int = 1,
) -> dict:
    document_map = json.loads((data / "document_map.json").read_text())
    catalogue = json.loads((data / "api_catalog.json").read_text())
    locations = json.loads((data / "chunk_locations.json").read_text())
    needs = []
    for need in task["information_needs"]:
        result = retrieve_need(
            need,
            task["scope"],
            document_map,
            catalogue,
            locations,
            base_url,
            limit,
        )
        if open_top:
            result["opened_sources"] = open_first_sources(
                result, document_map, open_top
            )
        needs.append(result)
    return {
        "task_id": task["id"],
        "query": task["query"],
        "information_needs": needs,
        "retrieval_contract": {
            "decomposition": "explicit input supplied by the calling agent",
            "route_scores": "comparable only inside each route",
            "document_map": "navigation only; not included in a content score",
            "references": "explicit links in authoritative manual content",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:7272")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--open-top", type=int, default=1)
    args = parser.parse_args()

    tasks = json.loads(args.tasks.read_text())
    try:
        task = next(item for item in tasks if item["id"] == args.task_id)
    except StopIteration as error:
        raise SystemExit(f"task not found: {args.task_id}") from error
    result = retrieve_task(task, args.data, args.base_url, args.limit, args.open_top)
    output = args.data / f"task_retrieval_{task['id']}.json"
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {output}")
    for need in result["information_needs"]:
        api = need["routes"]["api_catalogue"]
        semantic = need["routes"]["semantic"]
        api_name = (api[0].get("title") or api[0].get("canonical_name")) if api else "none"
        semantic_name = (
            semantic[0].get("title") or semantic[0].get("canonical_name")
            if semantic
            else "none"
        )
        print(
            f"{need['id']}: "
            f"api={api_name}; "
            f"semantic={semantic_name}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
