"""Filesystem confinement for external application integrations."""

import os
from pathlib import Path

from .errors import BridgeError, INVALID_PARAMS


class PathPolicy:
    def __init__(self, roots):
        resolved = []
        for root in roots:
            path = Path(root).expanduser().resolve()
            if path not in resolved:
                resolved.append(path)
        if not resolved:
            raise ValueError("At least one allowed root is required")
        self.roots = tuple(resolved)

    @classmethod
    def from_environment(cls, start_directory=None):
        roots = [start_directory or os.getcwd()]
        configured = os.environ.get("CAE_BRIDGE_ALLOWED_ROOTS", "")
        roots.extend(item for item in configured.split(os.pathsep) if item)
        return cls(roots)

    def describe(self):
        return [str(root) for root in self.roots]

    def resolve_read(self, value):
        path = self._resolve(value)
        if not path.is_file():
            raise BridgeError(INVALID_PARAMS, "Input file does not exist", {"path": str(path)})
        return path

    def resolve_write(self, value):
        path = self._resolve(value)
        if not path.parent.is_dir():
            raise BridgeError(
                INVALID_PARAMS,
                "Output directory does not exist",
                {"path": str(path), "parent": str(path.parent)},
            )
        return path

    def _resolve(self, value):
        if not isinstance(value, str) or not value:
            raise BridgeError(INVALID_PARAMS, "Path must be a non-empty string")
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.roots[0] / path
        path = path.resolve()
        if not any(path == root or root in path.parents for root in self.roots):
            raise BridgeError(
                INVALID_PARAMS,
                "Path is outside allowed roots",
                {"path": str(path), "allowed_roots": self.describe()},
            )
        return path
