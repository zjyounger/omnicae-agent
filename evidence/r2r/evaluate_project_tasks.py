#!/usr/bin/env python3
"""Capture retrieval candidates for project-derived tasks fixed before search."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from evidence.r2r.evaluate_calculix import (
        load_pages,
        search_r2r,
        source_rank,
        toc_title_rank,
    )
    from evidence.r2r.navigate_calculix import discover_entries
except ModuleNotFoundError:  # Direct execution from the repository root.
    from evaluate_calculix import load_pages, search_r2r, source_rank, toc_title_rank
    from navigate_calculix import discover_entries


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
DEFAULT_TASKS = Path(__file__).with_name("calculix_project_tasks.json")


def task_rank(ranked: list[dict], groups: list[list[dict]]) -> int | None:
    ranks = []
    for group in groups:
        acceptable = {(item["manual"], item["source_file"]) for item in group}
        rank = next(
            (
                index
                for index, item in enumerate(ranked, 1)
                if (item["manual"], item["source_file"]) in acceptable
            ),
            None,
        )
        if rank is None:
            return None
        ranks.append(rank)
    return max(ranks)


def summarize(results: list[dict], route: str) -> dict:
    ranks = [item["ranks"][route] for item in results]
    return {
        "tasks": len(ranks),
        "top1": sum(rank == 1 for rank in ranks),
        "top5": sum(rank is not None and rank <= 5 for rank in ranks),
        "top10": sum(rank is not None and rank <= 10 for rank in ranks),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--base-url", default="http://127.0.0.1:7272")
    args = parser.parse_args()

    document_map = json.loads((args.data / "document_map.json").read_text())
    catalogue = json.loads((args.data / "api_catalog.json").read_text())
    locations = json.loads((args.data / "chunk_locations.json").read_text())
    pages = load_pages(document_map)
    tasks = json.loads(args.tasks.read_text())
    output = []
    for task in tasks:
        scope = set(task["scope"])
        semantic = [
            result
            for result in source_rank(
            search_r2r(args.base_url, task["query"], "semantic"), locations
            )
            if result["manual"] in scope
        ]
        title_search = toc_title_rank(
            task["query"], [page for page in pages if page["manual"] in scope]
        )
        catalogue_results = [
            result
            for manual in task["scope"]
            for result in discover_entries(catalogue, task["query"], manual, 50)
        ]
        catalogue_results.sort(key=lambda item: item["score"], reverse=True)
        ranked = {
            "api_catalogue": catalogue_results,
            "toc_title_lexical": title_search,
            "semantic": semantic,
        }
        ranks = {
            route: task_rank(results, task["acceptable_source_groups"])
            for route, results in ranked.items()
        }
        output.append(
            {
                **task,
                "ranks": ranks,
                "candidates": {
                    "api_catalogue": catalogue_results[:10],
                    "toc_title_lexical": [
                        {
                            key: result.get(key)
                            for key in [
                                "manual",
                                "source_file",
                                "title",
                                "section_path",
                                "score",
                            ]
                        }
                        for result in title_search[:10]
                    ],
                    "semantic": [
                        {
                            key: result.get(key)
                            for key in [
                                "manual",
                                "source_file",
                                "title",
                                "kind",
                                "source_anchor",
                                "line_start",
                                "asset_path",
                                "section_path",
                                "score",
                            ]
                        }
                        for result in semantic[:10]
                    ],
                },
            }
        )
        print(task["id"], ranks, flush=True)
    routes = ["api_catalogue", "toc_title_lexical", "semantic"]
    result = {
        "provenance": {
            "queries": "captured from project artifacts before retrieval",
            "labels": "assigned by authoritative-source inspection after candidate capture",
            "independent_human_review": False,
        },
        "summary": {route: summarize(output, route) for route in routes},
        "tasks": output,
    }
    (args.data / "project_task_candidates.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
