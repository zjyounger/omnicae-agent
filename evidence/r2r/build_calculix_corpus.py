#!/usr/bin/env python3
"""Build a location-preserving CalculiX retrieval corpus from full HTML manuals."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / ".evidence-data" / "calculix-r2r"
MANUALS = {
    "ccx": REPO_ROOT
    / "knowledge/calculix/CalculiX/ccx_2.23/doc/ccx",
    "cgx": REPO_ROOT
    / "knowledge/calculix/CalculiX/cgx_2.23/doc/cgx",
}
NAV_LABELS = {"next", "previous", "up", "contents"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SPACE = re.compile(r"\s+")
NODE = re.compile(r"node(\d+)\.html$")


def clean(text: str) -> str:
    return SPACE.sub(" ", html.unescape(text)).strip()


def clean_code(text: str) -> str:
    lines = [line.rstrip() for line in html.unescape(text).splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


@dataclass
class Block:
    kind: str
    text: str
    line_start: int
    line_end: int
    anchor: str | None


class ManualPageParser(HTMLParser):
    """Extract readable blocks and image locations from LaTeX2HTML output."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.images: list[dict[str, Any]] = []
        self.links: list[str] = []
        self._buffer: list[str] = []
        self._kind = "text"
        self._line_start = 1
        self._anchor: str | None = None
        self._skip_depth = 0
        self._head_depth = 0
        self._pre_depth = 0
        self.title = ""
        self._in_title = False
        self._in_caption = False
        self._caption_buffer: list[str] = []
        self._pending_caption = ""

    def _flush(self, line_end: int | None = None) -> None:
        text = (
            clean_code("".join(self._buffer))
            if self._kind == "code"
            else clean(" ".join(self._buffer))
        )
        if text:
            self.blocks.append(
                Block(
                    kind=self._kind,
                    text=text,
                    line_start=self._line_start,
                    line_end=line_end or self.getpos()[0],
                    anchor=self._anchor,
                )
            )
        self._buffer = []
        self._kind = "code" if self._pre_depth else "text"
        self._line_start = self.getpos()[0]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "head":
            self._head_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "caption":
            self._in_caption = True
            self._caption_buffer = []
        classes = set(values.get("class", "").lower().split())
        if self._skip_depth:
            if tag not in VOID_TAGS:
                self._skip_depth += 1
            return
        if tag == "div" and "navigation" in classes:
            self._flush()
            self._skip_depth = 1
            return
        if tag == "ul" and "childlinks" in classes:
            self._flush()
            self._skip_depth = 1
            return
        if self._head_depth:
            return
        if tag == "a" and values.get("href"):
            target = Path(urlsplit(values["href"]).path).name
            if NODE.match(target):
                self.links.append(target)
        if tag == "a" and values.get("name"):
            name = values["name"]
            if (
                not name.lower().startswith("tex2html")
                and not name.startswith("SECTION")
                and name != "CHILD_LINKS"
            ):
                self._anchor = name
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre"}:
            self._flush()
            self._kind = "code" if tag == "pre" else "text"
            self._line_start = self.getpos()[0]
        if tag == "pre":
            self._pre_depth += 1
        if tag == "br":
            self._buffer.append("\n" if self._pre_depth else " ")
        if tag == "img":
            src = values.get("src", "")
            alt = clean(values.get("alt", ""))
            if src and not src.startswith("file:") and alt.lower() not in NAV_LABELS:
                width = int(values.get("width", "0") or 0)
                height = int(values.get("height", "0") or 0)
                self.images.append(
                    {
                        "asset": src,
                        "alt": alt,
                        "caption": self._pending_caption,
                        "line": self.getpos()[0],
                        "anchor": self._anchor,
                        "width": width,
                        "height": height,
                    }
                )
                self._pending_caption = ""
                if alt:
                    self._buffer.append(alt)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
        if tag == "caption":
            self._in_caption = False
            self._pending_caption = clean(" ".join(self._caption_buffer))
        if tag == "head":
            self._head_depth = max(0, self._head_depth - 1)
            return
        if tag == "pre":
            self._flush()
            self._pre_depth = max(0, self._pre_depth - 1)
            self._kind = "text"
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "li"}:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
        if self._in_caption:
            self._caption_buffer.append(data)
        if not self._head_depth:
            self._buffer.append(data)

    def close(self) -> None:
        super().close()
        self._flush()
        self.title = clean(self.title)


def nav_link(raw: str, label: str) -> str | None:
    match = re.search(
        rf"<B>\s*{label}:\s*</B>\s*<A[^>]+HREF=[\"']([^\"']+)",
        raw,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def anchors(raw: str) -> list[str]:
    values = re.findall(r"<A\s+NAME=[\"']([^\"']+)", raw, re.IGNORECASE)
    return [
        value
        for value in values
        if not value.lower().startswith("tex2html")
        and not value.startswith("SECTION")
        and value != "CHILD_LINKS"
    ]


def toc_order(root_html: str) -> dict[str, int]:
    start = root_html.find("<!--Table of Child-Links-->")
    body = root_html[start:] if start >= 0 else root_html
    seen: dict[str, int] = {}
    for href in re.findall(r'HREF=["\'](node\d+\.html)', body, re.IGNORECASE):
        seen.setdefault(href, len(seen))
    return seen


def split_long_block(block: Block, limit: int) -> list[Block]:
    if len(block.text) <= limit:
        return [block]
    units = block.text.splitlines(keepends=True) if block.kind == "code" else block.text.split()
    separator = "" if block.kind == "code" else " "
    parts: list[Block] = []
    current: list[str] = []
    size = 0
    for unit in units:
        if len(unit) > limit:
            if current:
                parts.append(
                    Block(block.kind, separator.join(current).strip(), block.line_start, block.line_end, block.anchor)
                )
                current, size = [], 0
            for offset in range(0, len(unit), limit):
                parts.append(
                    Block(block.kind, unit[offset : offset + limit].strip(), block.line_start, block.line_end, block.anchor)
                )
            continue
        addition = len(unit) + (len(separator) if current else 0)
        if current and size + addition > limit:
            parts.append(
                Block(block.kind, separator.join(current).strip(), block.line_start, block.line_end, block.anchor)
            )
            current, size = [], 0
        current.append(unit)
        size += addition
    if current:
        parts.append(
            Block(block.kind, separator.join(current).strip(), block.line_start, block.line_end, block.anchor)
        )
    return [part for part in parts if part.text]


def split_blocks(blocks: list[Block], limit: int = 800) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current: list[Block] = []
    size = 0

    def emit(parts: list[Block]) -> None:
        if not parts:
            return
        chunks.append(
            {
                "kind": "code" if all(part.kind == "code" for part in parts) else "text",
                "text": "\n\n".join(part.text for part in parts),
                "line_start": parts[0].line_start,
                "line_end": parts[-1].line_end,
                "source_anchor": next((part.anchor for part in parts if part.anchor), None),
            }
        )

    expanded = [part for block in blocks for part in split_long_block(block, limit)]
    for block in expanded:
        if block.kind == "code":
            emit(current)
            current, size = [], 0
            emit([block])
            continue
        if size and size + len(block.text) + 2 > limit:
            emit(current)
            current, size = [], 0
        if len(block.text) <= limit:
            current.append(block)
            size += len(block.text) + 2
            continue
    emit(current)
    return chunks


def section_path(page: str, pages: dict[str, dict[str, Any]]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    current: str | None = page
    while current and current not in seen and current in pages:
        seen.add(current)
        title = pages[current]["title"]
        if title and title.lower() != "contents":
            result.append(title)
        current = pages[current]["parent_source"]
    return list(reversed(result))


def stable_id(*parts: str) -> str:
    value = "\0".join(parts).encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:24]


def api_catalog(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_page: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for chunk in chunks:
        by_page.setdefault((chunk["manual"], chunk["source_file"]), []).append(chunk)
    entries: list[dict[str, Any]] = []
    for (manual, source_file), page_chunks in sorted(by_page.items()):
        first = page_chunks[0]
        path = first["section_path"]
        is_keyword = (
            manual == "ccx"
            and first["title"].startswith("*")
            and "Input deck format" in path
        )
        is_command = manual == "cgx" and "Commands" in path
        if not (is_keyword or is_command):
            continue
        paragraphs: list[str] = []
        syntax = ""
        for chunk in page_chunks:
            if chunk["kind"] == "code" and not syntax:
                syntax = chunk["text"][:800]
            if chunk["kind"] != "text":
                continue
            paragraphs.extend(
                part.strip()
                for part in re.split(r"\n\n+", chunk["text"])
                if part.strip()
            )
        canonical = first["title"].strip()
        summary = next(
            (
                paragraph
                for paragraph in paragraphs
                if paragraph.casefold() != canonical.casefold()
                and not paragraph.casefold().startswith("keyword type:")
            ),
            "",
        )[:800]
        entries.append(
            {
                "id": stable_id("api", manual, source_file),
                "manual": manual,
                "artifact_type": "keyword" if is_keyword else "command",
                "canonical_name": canonical,
                "normalized_name": canonical.lstrip("*").casefold(),
                "summary": summary,
                "syntax": syntax,
                "source_path": first["source_path"],
                "source_file": source_file,
                "source_anchor": first.get("source_anchor"),
                "section_path": path,
                "search_text": "\n".join(
                    value
                    for value in [
                        canonical,
                        summary,
                        syntax,
                        "\n".join(paragraphs)[:4_000] if is_command else "",
                    ]
                    if value
                ),
            }
        )
    return entries


def build_manual(manual: str, directory: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pages: dict[str, dict[str, Any]] = {}
    root_name = f"{manual}.html"
    root_raw = (directory / root_name).read_text(encoding="latin-1")
    order = toc_order(root_raw)
    html_files = sorted(
        directory.glob("*.html"),
        key=lambda path: (
            order.get(path.name, 10**9),
            int(NODE.match(path.name).group(1)) if NODE.match(path.name) else -1,
            path.name,
        ),
    )
    parsed: dict[str, ManualPageParser] = {}
    for path in html_files:
        raw = path.read_text(encoding="latin-1")
        parser = ManualPageParser()
        parser.feed(raw)
        parser.close()
        parsed[path.name] = parser
        pages[path.name] = {
            "manual": manual,
            "title": parser.title or path.stem,
            "source_path": str(path.relative_to(REPO_ROOT)),
            "source_file": path.name,
            "source_anchors": anchors(raw),
            "parent_source": nav_link(raw, "Up"),
            "previous_source": nav_link(raw, "Previous"),
            "next_source": nav_link(raw, "Next"),
            "toc_order": order.get(path.name),
        }

    for page in pages.values():
        page["children_sources"] = []
    for source_file, page in pages.items():
        parent = page["parent_source"]
        if parent in pages:
            pages[parent]["children_sources"].append(source_file)
    for page in pages.values():
        page["children_sources"].sort(
            key=lambda source: (
                pages[source]["toc_order"] is None,
                pages[source]["toc_order"] or 0,
                source,
            )
        )
    for source_file, page in pages.items():
        page["referenced_sources"] = list(
            dict.fromkeys(
                target
                for target in parsed[source_file].links
                if target in pages and target != source_file
            )
        )

    chunks: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    for source_file, page in pages.items():
        parser = parsed[source_file]
        path_titles = section_path(source_file, pages)
        page["section_path"] = path_titles
        source_path = page["source_path"]
        prefix = f"CalculiX {manual.upper()} 2.23 > " + " > ".join(path_titles)
        for index, item in enumerate(split_blocks(parser.blocks)):
            item.update(
                {
                    "id": stable_id(manual, source_file, item["kind"], str(index)),
                    "manual": manual,
                    "source_path": source_path,
                    "source_file": source_file,
                    "title": page["title"],
                    "section_path": path_titles,
                    "toc_order": page["toc_order"],
                    "parent_source": page["parent_source"],
                    "previous_source": page["previous_source"],
                    "next_source": page["next_source"],
                }
            )
            item["embedding_text"] = f"{prefix}\n\n{item['text']}"
            chunks.append(item)

        for image in parser.images:
            previous = max(
                (block for block in parser.blocks if block.line_end <= image["line"]),
                key=lambda block: block.line_end,
                default=None,
            )
            following = min(
                (block for block in parser.blocks if block.line_start >= image["line"]),
                key=lambda block: block.line_start,
                default=None,
            )
            asset = {
                **image,
                "manual": manual,
                "source_path": source_path,
                "source_file": source_file,
                "section_path": path_titles,
                "nearby_before": previous.text if previous else "",
                "nearby_after": following.text if following else "",
            }
            assets.append(asset)
            is_equation = image["alt"].lstrip().startswith("$")
            is_large = image["width"] >= 240 or image["height"] >= 120
            if is_equation and not is_large:
                continue
            context = clean(
                " ".join(
                    value
                    for value in [
                        image["caption"],
                        image["alt"],
                        asset["nearby_before"],
                        asset["nearby_after"],
                    ]
                    if value
                )
            )
            if not context:
                continue
            context = " ".join(context[:800].split())
            asset_path = str((directory / image["asset"]).relative_to(REPO_ROOT))
            chunks.append(
                {
                    "id": stable_id(manual, source_file, "figure", image["asset"]),
                    "kind": "figure",
                    "manual": manual,
                    "source_path": source_path,
                    "source_file": source_file,
                    "source_anchor": image["anchor"],
                    "asset_path": asset_path,
                    "caption": image["caption"],
                    "title": page["title"],
                    "section_path": path_titles,
                    "toc_order": page["toc_order"],
                    "parent_source": page["parent_source"],
                    "previous_source": page["previous_source"],
                    "next_source": page["next_source"],
                    "line_start": image["line"],
                    "line_end": image["line"],
                    "text": context,
                    "embedding_text": f"{prefix}\nFigure {image['asset']}\n\n{context}",
                }
            )
    return chunks, {"manual": manual, "pages": pages, "assets": assets}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    chunks: list[dict[str, Any]] = []
    document_map: dict[str, Any] = {"schema_version": 1, "manuals": {}}
    for manual, directory in MANUALS.items():
        manual_chunks, manual_map = build_manual(manual, directory)
        chunks.extend(manual_chunks)
        document_map["manuals"][manual] = manual_map

    corpus_path = args.output / "corpus.jsonl"
    with corpus_path.open("w", encoding="utf-8") as stream:
        for chunk in chunks:
            stream.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    map_path = args.output / "document_map.json"
    map_path.write_text(
        json.dumps(document_map, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    catalogue = api_catalog(chunks)
    (args.output / "api_catalog.json").write_text(
        json.dumps(catalogue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "chunks": len(chunks),
        "text_chunks": sum(chunk["kind"] == "text" for chunk in chunks),
        "code_chunks": sum(chunk["kind"] == "code" for chunk in chunks),
        "figure_chunks": sum(chunk["kind"] == "figure" for chunk in chunks),
        "pages": sum(
            len(item["pages"]) for item in document_map["manuals"].values()
        ),
        "assets": sum(
            len(item["assets"]) for item in document_map["manuals"].values()
        ),
        "api_entries": len(catalogue),
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
