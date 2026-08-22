#!/usr/bin/env python3
"""Evaluate exact visual-asset retrieval, not merely source-page retrieval."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

try:
    from evidence.r2r.evaluate_calculix import search_r2r, terms
except ModuleNotFoundError:  # Direct execution from the repository root.
    from evaluate_calculix import search_r2r, terms


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
DEFAULT_QUERIES = Path(__file__).with_name("calculix_visual_queries.json")


def lexical_figure_rank(query: str, figures: list[dict]) -> list[dict]:
    documents = [terms(figure["embedding_text"]) for figure in figures]
    frequencies = Counter()
    for document in documents:
        frequencies.update(set(document))
    average_length = sum(map(len, documents)) / max(1, len(documents))
    ranked = []
    for figure, document in zip(figures, documents):
        counts = Counter(document)
        caption_counts = Counter(terms(figure.get("caption", "")))
        for term, count in caption_counts.items():
            counts[term] += 3 * count
        score = 0.0
        for term in terms(query):
            frequency = counts[term]
            if not frequency:
                continue
            inverse = math.log(
                1
                + (len(documents) - frequencies[term] + 0.5)
                / (frequencies[term] + 0.5)
            )
            denominator = frequency + 1.2 * (
                1 - 0.75 + 0.75 * len(document) / max(1, average_length)
            )
            score += inverse * frequency * 2.2 / denominator
        ranked.append({**figure, "score": score})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def remote_figure_rank(results: list[dict], locations: dict[str, dict]) -> list[dict]:
    ranked = []
    seen = set()
    for result in results:
        location = locations.get(result["id"])
        if not location or location.get("kind") != "figure":
            continue
        asset = location["asset_path"]
        if asset in seen:
            continue
        seen.add(asset)
        ranked.append({**location, "score": result.get("score")})
    return ranked


def expected_rank(ranked: list[dict], asset: str) -> int | None:
    return next(
        (
            index
            for index, item in enumerate(ranked, 1)
            if item.get("asset_path") == asset
        ),
        None,
    )


def summarize(evaluations: list[dict], route: str) -> dict:
    ranks = [item["ranks"][route] for item in evaluations]
    return {
        "queries": len(ranks),
        "top1": sum(rank == 1 for rank in ranks),
        "top5": sum(rank is not None and rank <= 5 for rank in ranks),
        "top10": sum(rank is not None and rank <= 10 for rank in ranks),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--base-url", default="http://127.0.0.1:7272")
    args = parser.parse_args()

    records = [
        json.loads(line)
        for line in (args.data / "corpus.jsonl").read_text().splitlines()
    ]
    figures = [record for record in records if record["kind"] == "figure"]
    locations = json.loads((args.data / "chunk_locations.json").read_text())
    queries = json.loads(args.queries.read_text())
    evaluations = []
    for query in queries:
        remote_raw = search_r2r(
            args.base_url, query["query"], "semantic", limit=200
        )
        remote_figures = remote_figure_rank(remote_raw, locations)
        lexical_figures = lexical_figure_rank(query["query"], figures)
        raw_rank = next(
            (
                index
                for index, result in enumerate(remote_raw, 1)
                if locations.get(result["id"], {}).get("asset_path")
                == query["expected_asset"]
            ),
            None,
        )
        ranks = {
            "semantic_raw": raw_rank,
            "semantic_figures": expected_rank(
                remote_figures, query["expected_asset"]
            ),
            "caption_lexical": expected_rank(
                lexical_figures, query["expected_asset"]
            ),
        }
        evaluations.append(
            {
                **query,
                "ranks": ranks,
                "top_figures": {
                    "semantic_figures": [
                        {
                            key: item.get(key)
                            for key in [
                                "asset_path",
                                "caption",
                                "title",
                                "source_file",
                                "source_anchor",
                                "score",
                            ]
                        }
                        for item in remote_figures[:5]
                    ],
                    "caption_lexical": [
                        {
                            key: item.get(key)
                            for key in [
                                "asset_path",
                                "caption",
                                "title",
                                "source_file",
                                "source_anchor",
                                "score",
                            ]
                        }
                        for item in lexical_figures[:5]
                    ],
                },
            }
        )
        print(query["id"], ranks, flush=True)
    routes = ["semantic_raw", "semantic_figures", "caption_lexical"]
    output = {
        "queries": evaluations,
        "metrics": {route: summarize(evaluations, route) for route in routes},
    }
    (args.data / "visual_evaluation.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
