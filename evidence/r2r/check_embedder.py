#!/usr/bin/env python3
"""Verify the optional local Ollama embedder used by the R2R adapter."""

from __future__ import annotations

import json
import os
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


MODEL = "mxbai-embed-large"
EXPECTED_DIMENSIONS = 1024
DEFAULT_BASE_URL = "http://127.0.0.1:11434"


def main() -> int:
    base_url = os.environ.get("OLLAMA_API_BASE", DEFAULT_BASE_URL).rstrip("/")
    payload = json.dumps(
        {
            "model": MODEL,
            "input": [
                "apply a concentrated force to selected nodes",
                "define a pressure load on an element surface",
            ],
        }
    ).encode("utf-8")
    request = Request(
        f"{base_url}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            result = json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        print(f"embedder unavailable: {exc}", file=sys.stderr)
        return 2

    embeddings = result.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != 2:
        print("invalid response: expected two embeddings", file=sys.stderr)
        return 2

    dimensions = {len(vector) for vector in embeddings if isinstance(vector, list)}
    if dimensions != {EXPECTED_DIMENSIONS}:
        print(
            f"invalid dimensions: expected {EXPECTED_DIMENSIONS}, found {dimensions}",
            file=sys.stderr,
        )
        return 2

    print(f"ok: model={MODEL} vectors={len(embeddings)} dimensions=1024")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
