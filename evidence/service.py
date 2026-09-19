"""Project-owned, read-only evidence retrieval service."""

from __future__ import annotations

import os
from pathlib import Path

from evidence.r2r.navigate_calculix import (
    child_entries,
    exact_entries,
    load_manual,
    reference_entries,
    source_blocks,
)
from evidence.r2r.retrieve_calculix import retrieve_task


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = REPO_ROOT / ".evidence-data" / "calculix-r2r"
APPLICATIONS = {
    "calculix-ccx": "ccx",
    "calculix-cgx": "cgx",
}


def prepare_retrieval_result(result: dict) -> dict:
    """Keep MCP discovery compact; navigation expands links only after selection."""
    for need in result["information_needs"]:
        need.pop("explicit_references", None)
        for candidates in need["routes"].values():
            for candidate in candidates:
                for key in ["summary", "excerpt"]:
                    if candidate.get(key):
                        candidate[key] = candidate[key][:400]
                candidate["open_arguments"] = {
                    "application": (
                        "calculix-ccx"
                        if candidate["manual"] == "ccx"
                        else "calculix-cgx"
                    ),
                    "source_file": candidate["source_file"],
                }
        need["next_step"] = (
            "Select a candidate from route-specific evidence, then call "
            "evidence_open_source. Use evidence_get_document_map only when "
            "hierarchy or explicit cross-references are needed."
        )
    return result


class EvidenceError(RuntimeError):
    """Base error returned at the evidence-service boundary."""


class EvidenceDataUnavailable(EvidenceError):
    """The derived local corpus is absent or incomplete."""


class EvidenceSourceNotFound(EvidenceError):
    """A requested application or source location does not exist."""


class EvidenceBackendUnavailable(EvidenceError):
    """The semantic retrieval backend could not answer."""


class EvidenceService:
    def __init__(self, data: Path | None = None, r2r_url: str | None = None) -> None:
        self.data = Path(
            data or os.environ.get("OMNICAE_EVIDENCE_DATA", DEFAULT_DATA)
        ).resolve()
        self.r2r_url = r2r_url or os.environ.get(
            "R2R_API_URL", "http://127.0.0.1:7272"
        )

    @staticmethod
    def _manual(application: str) -> str:
        try:
            return APPLICATIONS[application]
        except KeyError as error:
            raise EvidenceSourceNotFound(
                f"unsupported evidence application: {application}"
            ) from error

    def _manual_map(self, application: str) -> tuple[str, dict]:
        manual = self._manual(application)
        try:
            return manual, load_manual(self.data, manual)
        except (FileNotFoundError, KeyError) as error:
            raise EvidenceDataUnavailable(
                f"CalculiX evidence data is unavailable under {self.data}"
            ) from error

    def lookup_exact(self, application: str, term: str) -> dict:
        manual, manual_map = self._manual_map(application)
        matches = exact_entries(manual_map, term)
        return {
            "application": application,
            "term": term,
            "matches": [
                {
                    **match,
                    "source_path": manual_map["pages"][match["source_file"]][
                        "source_path"
                    ],
                    "manual": manual,
                }
                for match in matches
            ],
        }

    def get_document_map(
        self, application: str, source_file: str | None = None
    ) -> dict:
        manual, manual_map = self._manual_map(application)
        source_file = source_file or f"{manual}.html"
        pages = manual_map["pages"]
        if source_file not in pages:
            raise EvidenceSourceNotFound(
                f"source page not found: {application}/{source_file}"
            )
        page = pages[source_file]
        return {
            "application": application,
            "manual": manual,
            "source_file": source_file,
            "source_path": page["source_path"],
            "title": page["title"],
            "section_path": page["section_path"],
            "parent_source": page["parent_source"],
            "previous_source": page["previous_source"],
            "next_source": page["next_source"],
            "children": child_entries(manual_map, source_file),
            "references": reference_entries(manual_map, source_file),
        }

    def open_source(self, application: str, source_file: str) -> dict:
        manual, manual_map = self._manual_map(application)
        if source_file not in manual_map["pages"]:
            raise EvidenceSourceNotFound(
                f"source page not found: {application}/{source_file}"
            )
        page, _, blocks = source_blocks(manual_map, source_file)
        return {
            "application": application,
            "manual": manual,
            "source_file": source_file,
            "source_path": page["source_path"],
            "title": page["title"],
            "section_path": page["section_path"],
            "blocks": blocks,
        }

    def retrieve(
        self,
        query: str,
        information_needs: list[dict],
        application_scope: list[str],
        limit: int = 5,
    ) -> dict:
        manuals = [self._manual(application) for application in application_scope]
        needs = []
        for need in information_needs:
            item = {"id": need["id"], "query": need["query"]}
            if need.get("application_scope"):
                item["scope"] = [
                    self._manual(application)
                    for application in need["application_scope"]
                ]
            needs.append(item)
        task = {
            "id": "mcp-request",
            "query": query,
            "scope": manuals,
            "information_needs": needs,
        }
        try:
            result = retrieve_task(
                task,
                self.data,
                self.r2r_url,
                limit=limit,
                open_top=0,
            )
        except FileNotFoundError as error:
            raise EvidenceDataUnavailable(
                f"CalculiX evidence data is unavailable under {self.data}"
            ) from error
        except Exception as error:
            try:
                import requests
            except ModuleNotFoundError:
                raise EvidenceBackendUnavailable(str(error)) from error
            if isinstance(error, requests.RequestException):
                raise EvidenceBackendUnavailable(
                    f"R2R semantic backend is unavailable: {error}"
                ) from error
            raise
        prepare_retrieval_result(result)
        result["application_scope"] = application_scope
        result["semantic_backend"] = "r2r"
        return result
