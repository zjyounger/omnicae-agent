#!/usr/bin/env python3
"""Measure explicit multi-need retrieval on the fixed CalculiX task set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from evidence.r2r.retrieve_calculix import retrieve_need
except ModuleNotFoundError:  # Direct execution from the repository root.
    from retrieve_calculix import retrieve_need


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
DEFAULT_TASKS = Path(__file__).with_name("calculix_project_tasks.json")


def source_keys(items: list[dict]) -> set[tuple[str, str]]:
    return {(item["manual"], item["source_file"]) for item in items}


def need_covered(
    need: dict,
    result: dict,
    routes: list[str],
    limit: int,
    include_references: bool = False,
) -> bool:
    found: set[tuple[str, str]] = set()
    for route in routes:
        direct = result["routes"][route][:limit]
        found.update(source_keys(direct))
        if include_references:
            origins = source_keys(direct)
            found.update(
                (reference["manual"], reference["source_file"])
                for reference in result["explicit_references"][route]
                if (
                    reference["referenced_by"]["manual"],
                    reference["referenced_by"]["source_file"],
                )
                in origins
            )
    acceptable = source_keys(need["acceptable_sources"])
    return bool(found & acceptable)


def configuration_success(task_result: dict, configuration: dict, limit: int) -> bool:
    return all(
        need_covered(
            item["need"],
            item["result"],
            configuration["routes"],
            limit,
            configuration["references"],
        )
        for item in task_result["needs"]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--base-url", default="http://127.0.0.1:7272")
    args = parser.parse_args()

    document_map = json.loads((args.data / "document_map.json").read_text())
    catalogue = json.loads((args.data / "api_catalog.json").read_text())
    locations = json.loads((args.data / "chunk_locations.json").read_text())
    tasks = json.loads(args.tasks.read_text())
    task_results = []
    for task in tasks:
        needs = []
        for need in task["information_needs"]:
            result = retrieve_need(
                need,
                task["scope"],
                document_map,
                catalogue,
                locations,
                args.base_url,
                10,
            )
            needs.append({"need": need, "result": result})
            print(f"{task['id']} / {need['id']}", flush=True)
        task_results.append({"id": task["id"], "needs": needs})

    configurations = {
        "api_catalogue": {"routes": ["api_catalogue"], "references": False},
        "semantic": {"routes": ["semantic"], "references": False},
        "route_union": {
            "routes": ["api_catalogue", "semantic"],
            "references": False,
        },
        "route_union_with_explicit_references": {
            "routes": ["api_catalogue", "semantic"],
            "references": True,
        },
    }
    summary = {
        name: {
            f"top{limit}": sum(
                configuration_success(task, configuration, limit)
                for task in task_results
            )
            for limit in [1, 5, 10]
        }
        for name, configuration in configurations.items()
    }
    output = {
        "provenance": {
            "queries": "explicit information needs derived from the ten fixed project tasks",
            "labels": "assigned by authoritative-source inspection",
            "independent_human_review": False,
            "score_fusion": False,
        },
        "summary": summary,
        "tasks": task_results,
    }
    (args.data / "multi_source_evaluation.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
