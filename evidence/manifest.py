"""Source-manifest validation and deterministic content hashing.

This module intentionally uses only the Python standard library. Retrieval
backends consume validated manifests; they do not own the source contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


SCHEMA_VERSION = 1
REQUIRED_FIELDS = {
    "schema_version",
    "id",
    "path_or_url",
    "source_version",
    "license",
    "redistribution",
    "content_hash",
    "authority",
}
OPTIONAL_FIELDS = {"metadata"}
REDISTRIBUTION_VALUES = {"allowed", "fetch_only"}
AUTHORITY_VALUES = {"official", "project", "community", "third-party"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:/-]*$")
HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ManifestError(ValueError):
    """A source manifest is incomplete, unsafe, or inconsistent with disk."""


def _sha256_file(path: Path) -> bytes:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.digest()


def content_hash(path: Path | str) -> str:
    """Return a deterministic SHA-256 hash for a file or directory tree.

    A file is hashed as its raw bytes. A directory is hashed from each regular
    file's POSIX relative path and SHA-256 digest, ordered by relative path.
    Symlinks are rejected so the inventory cannot escape its declared root.
    """

    target = Path(path)
    if target.is_symlink():
        raise ManifestError(f"symlinks are not valid evidence sources: {target}")
    if target.is_file():
        return f"sha256:{_sha256_file(target).hex()}"
    if not target.is_dir():
        raise ManifestError(f"source does not exist: {target}")

    digest = hashlib.sha256()
    for child in sorted(target.rglob("*"), key=lambda item: item.as_posix()):
        if child.is_symlink():
            raise ManifestError(f"symlinks are not valid evidence sources: {child}")
        if not child.is_file():
            continue
        relative = child.relative_to(target).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(_sha256_file(child))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _require_string(manifest: Mapping[str, Any], field: str) -> str:
    value = manifest.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{field} must be a non-empty string")
    return value


def _is_remote_source(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _resolve_local_source(value: str, root: Path) -> Path:
    declared = Path(value)
    if declared.is_absolute() or ".." in declared.parts:
        raise ManifestError("path_or_url must stay within the repository root")
    resolved_root = root.resolve()
    candidate = resolved_root / declared
    current = resolved_root
    for part in declared.parts:
        current = current / part
        if current.is_symlink():
            raise ManifestError(f"symlinks are not valid evidence sources: {current}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ManifestError("path_or_url escapes the repository root") from exc
    return candidate


def validate(manifest: Mapping[str, Any], root: Path | str) -> None:
    """Validate provenance and, for local sources, verify content on disk."""

    if not isinstance(manifest, Mapping):
        raise ManifestError("manifest must be a JSON object")

    fields = set(manifest)
    missing = REQUIRED_FIELDS - fields
    if missing:
        raise ManifestError(f"missing required fields: {', '.join(sorted(missing))}")
    unexpected = fields - REQUIRED_FIELDS - OPTIONAL_FIELDS
    if unexpected:
        raise ManifestError(f"unexpected fields: {', '.join(sorted(unexpected))}")

    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ManifestError(f"schema_version must be {SCHEMA_VERSION}")

    source_id = _require_string(manifest, "id")
    if not ID_PATTERN.fullmatch(source_id):
        raise ManifestError("id must be lowercase and contain only a-z, 0-9, . _ : / -")

    source = _require_string(manifest, "path_or_url")
    _require_string(manifest, "source_version")
    licence = _require_string(manifest, "license")
    if licence.lower() in {"unknown", "tbd", "none"}:
        raise ManifestError("license must identify an upstream licence or LicenseRef")

    redistribution = _require_string(manifest, "redistribution")
    if redistribution not in REDISTRIBUTION_VALUES:
        raise ManifestError("redistribution must be allowed or fetch_only")

    authority = _require_string(manifest, "authority")
    if authority not in AUTHORITY_VALUES:
        raise ManifestError(
            "authority must be official, project, community, or third-party"
        )

    declared_hash = _require_string(manifest, "content_hash")
    if not HASH_PATTERN.fullmatch(declared_hash):
        raise ManifestError("content_hash must use sha256:<64 lowercase hex digits>")

    metadata = manifest.get("metadata")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise ManifestError("metadata must be a JSON object")

    if not _is_remote_source(source):
        local_source = _resolve_local_source(source, Path(root))
        actual_hash = content_hash(local_source)
        if actual_hash != declared_hash:
            raise ManifestError(
                f"content hash mismatch for {source}: expected {declared_hash}, "
                f"found {actual_hash}"
            )


def load_and_validate(path: Path | str, root: Path | str) -> Mapping[str, Any]:
    manifest_path = Path(path)
    try:
        with manifest_path.open("r", encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read manifest {manifest_path}: {exc}") from exc
    validate(manifest, root)
    return manifest


def load_inventory(
    paths: Sequence[Path | str], root: Path | str
) -> list[Mapping[str, Any]]:
    """Load manifests and reject duplicate stable source identifiers."""

    manifests = []
    identifiers: dict[str, Path] = {}
    for path in paths:
        manifest_path = Path(path)
        manifest = load_and_validate(manifest_path, root)
        source_id = str(manifest["id"])
        if source_id in identifiers:
            raise ManifestError(
                f"duplicate source id {source_id}: "
                f"{identifiers[source_id]} and {manifest_path}"
            )
        identifiers[source_id] = manifest_path
        manifests.append(manifest)
    return manifests


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    hash_parser = subparsers.add_parser("hash", help="hash a source file or tree")
    hash_parser.add_argument("path", type=Path)

    validate_parser = subparsers.add_parser("validate", help="validate manifests")
    validate_parser.add_argument("manifests", type=Path, nargs="+")
    validate_parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "hash":
            print(content_hash(args.path))
            return 0
        manifests = load_inventory(args.manifests, args.root)
        for manifest in manifests:
            print(f"valid: {manifest['id']}")
        return 0
    except ManifestError as exc:
        print(f"invalid: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
