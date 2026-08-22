#!/usr/bin/env python3
"""Measure answer-marker coverage after a CalculiX source page is known."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
DEFAULT_QUERIES = Path(__file__).with_name("calculix_context_queries.json")
TOKEN = re.compile(r"\*?[a-z0-9][a-z0-9_-]*")


def terms(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


def rank_page_chunks(query: str, chunks: list[dict]) -> list[int]:
    documents = [terms(chunk["text"]) for chunk in chunks]
    frequencies = Counter()
    for document in documents:
        frequencies.update(set(document))
    average_length = sum(map(len, documents)) / max(1, len(documents))
    ranked: list[tuple[float, int]] = []
    for index, document in enumerate(documents):
        counts = Counter(document)
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
        ranked.append((score, index))
    return [index for _, index in sorted(ranked, reverse=True)]


def marker_coverage(text: str, required: list[list[str]]) -> tuple[int, int]:
    lowered = text.casefold()
    matched = sum(
        any(alternative.casefold() in lowered for alternative in alternatives)
        for alternatives in required
    )
    return matched, len(required)


def context_scopes(query: str, chunks: list[dict]) -> dict[str, dict]:
    selected = rank_page_chunks(query, chunks)[0]
    ranges = {
        "chunk": range(selected, selected + 1),
        "neighbours": range(max(0, selected - 1), min(len(chunks), selected + 2)),
        "page": range(0, len(chunks)),
    }
    return {
        scope: {
            "selected_chunk": selected,
            "chunk_indices": list(indices),
            "text": "\n\n".join(chunks[index]["text"] for index in indices),
        }
        for scope, indices in ranges.items()
    }


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


def evaluate(records: list[dict], queries: list[dict]) -> dict:
    pages: dict[tuple[str, str], list[dict]] = {}
    for record in records:
        if record["kind"] == "figure":
            continue
        pages.setdefault((record["manual"], record["source_file"]), []).append(record)
    evaluations = []
    for query in queries:
        page_chunks = pages[(query["manual"], query["source_file"])]
        scopes = context_scopes(query["query"], page_chunks)
        for value in scopes.values():
            matched, total = marker_coverage(value.pop("text"), query["required"])
            value.update(
                {
                    "characters": sum(
                        len(page_chunks[index]["text"])
                        for index in value["chunk_indices"]
                    ),
                    "matched_requirements": matched,
                    "total_requirements": total,
                    "complete": matched == total,
                }
            )
        evaluations.append({**query, "scopes": scopes})
    page_sizes = [sum(len(chunk["text"]) for chunk in chunks) for chunks in pages.values()]
    api_pages = {
        (record["manual"], record["source_file"])
        for record in records
        if (
            record["manual"] == "ccx"
            and record["title"].startswith("*")
            and "Input deck format" in record["section_path"]
        )
        or (record["manual"] == "cgx" and "Commands" in record["section_path"])
    }
    api_sizes = [
        sum(len(chunk["text"]) for chunk in pages[key])
        for key in api_pages
        if key in pages
    ]
    return {
        "queries": evaluations,
        "summary": {
            scope: {
                "complete": sum(item["scopes"][scope]["complete"] for item in evaluations),
                "queries": len(evaluations),
                "mean_characters": round(
                    sum(item["scopes"][scope]["characters"] for item in evaluations)
                    / len(evaluations)
                ),
            }
            for scope in ["chunk", "neighbours", "page"]
        },
        "page_sizes": {
            "all_pages": {
                "median": percentile(page_sizes, 0.5),
                "p90": percentile(page_sizes, 0.9),
                "maximum": max(page_sizes),
            },
            "api_pages": {
                "count": len(api_sizes),
                "median": percentile(api_sizes, 0.5),
                "p90": percentile(api_sizes, 0.9),
                "maximum": max(api_sizes),
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    args = parser.parse_args()
    records = [
        json.loads(line)
        for line in (args.data / "corpus.jsonl").read_text().splitlines()
    ]
    output = evaluate(records, json.loads(args.queries.read_text()))
    (args.data / "context_scope_evaluation.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"summary": output["summary"], "page_sizes": output["page_sizes"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
