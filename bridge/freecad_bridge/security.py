"""Filesystem policy for bridge file operations."""

import os
from pathlib import Path

from .errors import BridgeError, INVALID_PARAMS


class PathPolicy:
    def __init__(self, roots):
        normalized = []
        for root in roots:
            path = Path(root).expanduser().resolve()
            if path not in normalized:
                normalized.append(path)
        if not normalized:
            raise ValueError("At least one allowed root is required")
        self.roots = tuple(normalized)

    @classmethod
    def from_environment(cls):
        raw = os.environ.get("CAE_BRIDGE_ALLOWED_ROOTS", "")
        roots = [item for item in raw.split(os.pathsep) if item]
        if not roots:
            roots = [os.getcwd()]
        return cls(roots)

    def describe(self):
        return [str(root) for root in self.roots]

    def resolve_read(self, value, suffixes=None):
        path = self._resolve(value, suffixes)
        if not path.is_file():
            raise BridgeError(
                INVALID_PARAMS,
                "Input file does not exist",
                {"path": str(path)},
            )
        return path

    def resolve_directory(self, value):
        path = self._resolve(value, None)
        if not path.is_dir():
            raise BridgeError(
                INVALID_PARAMS,
                "Directory does not exist",
                {"path": str(path)},
            )
        return path

    def resolve_write(self, value, suffixes=None):
        path = self._resolve(value, suffixes)
        if not path.parent.is_dir():
            raise BridgeError(
                INVALID_PARAMS,
                "Output parent directory does not exist",
                {"path": str(path.parent)},
            )
        return path

    def _resolve(self, value, suffixes):
        if not isinstance(value, str) or not value.strip():
            raise BridgeError(INVALID_PARAMS, "Path must be a non-empty string")
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = self.roots[0] / candidate
        candidate = candidate.resolve(strict=False)

        if not any(self._is_within(candidate, root) for root in self.roots):
            raise BridgeError(
                INVALID_PARAMS,
                "Path is outside the allowed roots",
                {"path": str(candidate), "allowed_roots": self.describe()},
            )

        if suffixes:
            expected = tuple(item.lower() for item in suffixes)
            if candidate.suffix.lower() not in expected:
                raise BridgeError(
                    INVALID_PARAMS,
                    "File extension is not allowed",
                    {"path": str(candidate), "allowed_suffixes": list(expected)},
                )
        return candidate

    @staticmethod
    def _is_within(path, root):
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
