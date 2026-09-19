#!/usr/bin/env python3
"""Compare TOC-title search and content-retrieval routes."""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
DEFAULT_QUERIES = Path(__file__).with_name("calculix_queries.json")
TOKEN = re.compile(r"\*?[a-z0-9][a-z0-9_-]*")


def terms(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def load_pages(document_map: dict) -> list[dict[str, Any]]:
    pages = []
    for manual, item in document_map["manuals"].items():
        for source, page in item["pages"].items():
            pages.append({"manual": manual, "source_file": source, **page})
    return pages


def toc_title_rank(query: str, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lexically search TOC titles; this is not agent directory traversal."""
    documents = [
        terms(" > ".join(page["section_path"]) + " " + page["title"])
        for page in pages
    ]
    document_frequency = Counter()
    for document in documents:
        document_frequency.update(set(document))
    average_length = sum(map(len, documents)) / max(1, len(documents))
    query_terms = terms(query)
    ranked = []
    for page, document in zip(pages, documents):
        frequencies = Counter(document)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse = math.log(
                1 + (len(documents) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            denominator = frequency + 1.2 * (
                1 - 0.75 + 0.75 * len(document) / max(1, average_length)
            )
            score += inverse * frequency * 2.2 / denominator
        title = page["title"].lower()
        normalized_query = query.lower().strip()
        if title and title in normalized_query:
            score += 12
        for term in query_terms:
            if term.startswith("*") and term in title:
                score += 15
        ranked.append({**page, "score": score})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def search_r2r(base_url: str, query: str, mode: str, limit: int = 50) -> list[dict]:
    settings = {
        "semantic": {
            "use_semantic_search": True,
            "use_fulltext_search": False,
            "use_hybrid_search": False,
        },
        "lexical": {
            "use_semantic_search": False,
            "use_fulltext_search": True,
            "use_hybrid_search": False,
        },
        "hybrid": {
            "use_semantic_search": True,
            "use_fulltext_search": True,
            "use_hybrid_search": True,
        },
    }[mode]
    response = requests.post(
        f"{base_url.rstrip('/')}/v3/chunks/search",
        json={"query": query, "search_settings": {**settings, "limit": limit}},
        timeout=120,
    )
    response.raise_for_status()
    results = response.json()["results"]
    time.sleep(3.1)
    return results


def source_rank(
    results: list[dict], locations: dict[str, dict], kind: str | None = None
) -> list[dict]:
    ranked = []
    seen = set()
    for result in results:
        location = locations.get(result["id"])
        if not location:
            continue
        if kind and location.get("kind") != kind:
            continue
        key = (location["manual"], location["source_file"])
        if key in seen:
            continue
        seen.add(key)
        ranked.append(
            {
                **location,
                "score": result.get("score"),
                "chunk_id": result["id"],
                "excerpt": result.get("text", "")[:800],
            }
        )
    return ranked


def requested_kind(query: str) -> str | None:
    lowered = query.lower()
    if any(word in lowered for word in ["diagram", "figure", "image", "picture"]):
        return "figure"
    if any(word in lowered for word in ["fortran", "subroutine", "script", "source code"]):
        return "code"
    return None


def expected_rank(query: dict, ranked: list[dict], require_kind: bool = False) -> int | None:
    for index, result in enumerate(ranked, 1):
        if (
            result["manual"] == query["expected_manual"]
            and result["source_file"] == query["expected_source"]
            and (not require_kind or result.get("kind") == query["expected_kind"])
        ):
            return index
    return None


def summarize(evaluations: list[dict], mode: str) -> dict[str, float | int]:
    ranks = [item["ranks"][mode] for item in evaluations]
    found = [rank for rank in ranks if rank is not None]
    return {
        "queries": len(ranks),
        "top1": sum(rank == 1 for rank in found),
        "top5": sum(rank <= 5 for rank in found),
        "top10": sum(rank <= 10 for rank in found),
        "mrr": round(sum(1 / rank for rank in found) / len(ranks), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--base-url", default="http://127.0.0.1:7272")
    args = parser.parse_args()

    document_map = json.loads((args.data / "document_map.json").read_text())
    locations = json.loads((args.data / "chunk_locations.json").read_text())
    queries = json.loads(args.queries.read_text())
    pages = load_pages(document_map)
    evaluations = []
    for query in queries:
        toc_title = toc_title_rank(query["query"], pages)
        remote_raw = {
            mode: search_r2r(args.base_url, query["query"], mode)
            for mode in ["lexical", "semantic", "hybrid"]
        }
        remote = {
            mode: source_rank(results, locations)
            for mode, results in remote_raw.items()
        }
        typed_semantic = source_rank(
            remote_raw["semantic"], locations, requested_kind(query["query"])
        )
        ranked = {
            "toc_title": toc_title,
            **remote,
            "typed_semantic": typed_semantic,
        }
        ranks = {mode: expected_rank(query, values) for mode, values in ranked.items()}
        kind_ranks = {
            mode: expected_rank(
                query,
                source_rank(remote_raw[mode], locations, query["expected_kind"]),
                require_kind=True,
            )
            for mode in remote
        }
        evaluations.append(
            {
                **query,
                "ranks": ranks,
                "kind_ranks": kind_ranks,
                "top_results": {
                    mode: [
                        {
                            key: item.get(key)
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
                        for item in values[:5]
                    ]
                    for mode, values in ranked.items()
                },
            }
        )
        print(query["id"], ranks)

    modes = [
        "toc_title",
        "lexical",
        "semantic",
        "hybrid",
        "typed_semantic",
    ]
    corpus_summary = json.loads((args.data / "summary.json").read_text())
    output = {
        "corpus": corpus_summary,
        "metrics": {mode: summarize(evaluations, mode) for mode in modes},
        "queries": evaluations,
        "location_mapping": {"mapped": len(locations), "expected": corpus_summary["chunks"]},
    }
    (args.data / "evaluation.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
