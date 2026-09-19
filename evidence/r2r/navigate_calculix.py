#!/usr/bin/env python3
"""Traverse the CalculiX document map and open authoritative source pages."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

try:
    from evidence.r2r.build_calculix_corpus import ManualPageParser, REPO_ROOT
except ModuleNotFoundError:  # Direct execution from the repository root.
    from build_calculix_corpus import ManualPageParser, REPO_ROOT


DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
TOKEN = re.compile(r"\*?[a-z0-9][a-z0-9_-]*")


def load_manual(data: Path, manual: str) -> dict:
    document_map = json.loads((data / "document_map.json").read_text())
    try:
        manual_map = document_map["manuals"][manual]
    except KeyError as error:
        raise SystemExit(f"manual not found: {manual}") from error
    pages = manual_map["pages"]
    if any("children_sources" not in page for page in pages.values()):
        for page in pages.values():
            page["children_sources"] = []
        for source_file, page in pages.items():
            if page["parent_source"] in pages:
                pages[page["parent_source"]]["children_sources"].append(source_file)
        for page in pages.values():
            page["children_sources"].sort(
                key=lambda source: (
                    pages[source]["toc_order"] is None,
                    pages[source]["toc_order"] or 0,
                    source,
                )
            )
    return manual_map


def reference_entries(manual_map: dict, source_file: str) -> list[dict]:
    pages = manual_map["pages"]
    if source_file not in pages:
        raise SystemExit(f"source page not found: {source_file}")
    return [
        {
            "source_file": target,
            "title": pages[target]["title"],
            "section_path": pages[target]["section_path"],
        }
        for target in pages[source_file].get("referenced_sources", [])
        if target in pages
    ]


def child_entries(manual_map: dict, source_file: str) -> list[dict]:
    pages = manual_map["pages"]
    if source_file not in pages:
        raise SystemExit(f"source page not found: {source_file}")
    return [
        {
            "source_file": child,
            "title": pages[child]["title"],
            "child_count": len(pages[child]["children_sources"]),
        }
        for child in pages[source_file]["children_sources"]
    ]


def exact_entries(manual_map: dict, term: str) -> list[dict]:
    normalized = term.strip().casefold().lstrip("*")
    return [
        {
            "source_file": source_file,
            "title": page["title"],
            "section_path": page["section_path"],
        }
        for source_file, page in manual_map["pages"].items()
        if page["title"].strip().casefold().lstrip("*") == normalized
    ]


def terms(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


def discover_entries(
    catalogue: list[dict], query: str, manual: str, limit: int = 10
) -> list[dict]:
    entries = [entry for entry in catalogue if entry["manual"] == manual]
    documents = [terms(entry["search_text"]) for entry in entries]
    document_frequency = Counter()
    for document in documents:
        document_frequency.update(set(document))
    average_length = sum(map(len, documents)) / max(1, len(documents))
    query_terms = terms(query)
    normalized_query_terms = {term.lstrip("*") for term in query_terms}
    ranked = []
    for entry, document in zip(entries, documents):
        frequencies = Counter(document)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse = math.log(
                1
                + (len(documents) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            denominator = frequency + 1.2 * (
                1 - 0.75 + 0.75 * len(document) / max(1, average_length)
            )
            score += inverse * frequency * 2.2 / denominator
        normalized_query = query.strip().casefold().lstrip("*")
        if normalized_query == entry["normalized_name"]:
            score += 100
        canonical = entry["canonical_name"].casefold()
        explicitly_named = (
            canonical in query_terms
            if canonical.startswith("*")
            else entry["normalized_name"] in normalized_query_terms
        )
        if explicitly_named:
            score += 25
        if score:
            ranked.append(
                {
                    key: entry[key]
                    for key in [
                        "manual",
                        "artifact_type",
                        "canonical_name",
                        "summary",
                        "source_path",
                        "source_file",
                        "source_anchor",
                        "section_path",
                    ]
                }
                | {"score": round(score, 6)}
            )
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:limit]


def source_blocks(manual_map: dict, source_file: str) -> tuple[dict, str, list[dict]]:
    try:
        page = manual_map["pages"][source_file]
    except KeyError as error:
        raise SystemExit(f"source page not found: {source_file}") from error
    path = (REPO_ROOT / page["source_path"]).resolve()
    if not path.is_relative_to(REPO_ROOT):
        raise SystemExit(f"source path escapes repository: {path}")
    raw = path.read_text(encoding="latin-1")
    parser = ManualPageParser()
    parser.feed(raw)
    parser.close()
    blocks = [
        {
            "kind": block.kind,
            "text": block.text,
            "line_start": block.line_start,
            "line_end": block.line_end,
            "source_anchor": block.anchor,
        }
        for block in parser.blocks
    ]
    return page, raw, blocks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    subparsers = parser.add_subparsers(dest="command", required=True)

    children = subparsers.add_parser("children")
    children.add_argument("--manual", choices=["ccx", "cgx"], required=True)
    children.add_argument("--source", required=True)

    lookup = subparsers.add_parser("lookup")
    lookup.add_argument("--manual", choices=["ccx", "cgx"], required=True)
    lookup.add_argument("--term", required=True)

    discover = subparsers.add_parser("discover")
    discover.add_argument("--manual", choices=["ccx", "cgx"], required=True)
    discover.add_argument("--query", required=True)
    discover.add_argument("--limit", type=int, default=10)

    references = subparsers.add_parser("references")
    references.add_argument("--manual", choices=["ccx", "cgx"], required=True)
    references.add_argument("--source", required=True)

    open_page = subparsers.add_parser("open")
    open_page.add_argument("--manual", choices=["ccx", "cgx"], required=True)
    open_page.add_argument("--source", required=True)
    open_page.add_argument("--format", choices=["text", "json", "raw"], default="text")

    args = parser.parse_args()
    manual_map = load_manual(args.data, args.manual)
    if args.command == "children":
        print(json.dumps(child_entries(manual_map, args.source), ensure_ascii=False, indent=2))
        return 0
    if args.command == "lookup":
        print(json.dumps(exact_entries(manual_map, args.term), ensure_ascii=False, indent=2))
        return 0
    if args.command == "discover":
        catalogue = json.loads((args.data / "api_catalog.json").read_text())
        print(
            json.dumps(
                discover_entries(catalogue, args.query, args.manual, args.limit),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "references":
        print(
            json.dumps(
                reference_entries(manual_map, args.source),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    page, raw, blocks = source_blocks(manual_map, args.source)
    if args.format == "raw":
        print(raw, end="")
    elif args.format == "json":
        print(
            json.dumps(
                {
                    "source_path": page["source_path"],
                    "source_file": args.source,
                    "title": page["title"],
                    "section_path": page["section_path"],
                    "blocks": blocks,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"Source: {page['source_path']}")
        print(f"Section: {' > '.join(page['section_path'])}")
        print()
        print("\n\n".join(block["text"] for block in blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
