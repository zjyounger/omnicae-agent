#!/usr/bin/env python3
"""Build the disposable CalculiX retrieval index with one command."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
COMPOSE_FILE = SCRIPT_DIR / "compose.yaml"
PROJECT_NAME = "omnicae-r2r-evaluation"
MODEL = "mxbai-embed-large"


def compose_command(which=shutil.which) -> list[str]:
    if which("docker-compose"):
        return ["docker-compose"]
    if which("docker"):
        return ["docker", "compose"]
    raise RuntimeError("Docker Compose is required (docker-compose or docker compose)")


def ollama_has_model(base_url: str, model: str = MODEL) -> bool:
    try:
        with urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=5) as response:
            models = json.load(response).get("models", [])
    except (OSError, URLError, json.JSONDecodeError):
        return False
    names = {item.get("name", "") for item in models}
    return model in names or f"{model}:latest" in names


def wait_for_url(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=5) as response:
                if 200 <= response.status < 300:
                    return
        except (OSError, URLError) as error:
            last_error = error
        time.sleep(2)
    raise RuntimeError(f"service did not become ready: {url} ({last_error})")


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--r2r-url", default="http://127.0.0.1:7272")
    parser.add_argument("--skip-start", action="store_true")
    parser.add_argument("--skip-model-pull", action="store_true")
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()

    if not ollama_has_model(args.ollama_url):
        if args.skip_model_pull:
            raise SystemExit(f"Ollama model is unavailable: {MODEL}")
        if not shutil.which("ollama"):
            raise SystemExit("Ollama is not installed or is not on PATH")
        run(["ollama", "pull", MODEL])
    wait_for_url(f"{args.ollama_url.rstrip('/')}/api/tags", args.timeout)

    if not args.skip_start:
        command = compose_command()
        run(
            command
            + [
                "-p",
                PROJECT_NAME,
                "-f",
                str(COMPOSE_FILE),
                "up",
                "-d",
            ]
        )
    wait_for_url(f"{args.r2r_url.rstrip('/')}/v3/health", args.timeout)

    run(
        [sys.executable, str(SCRIPT_DIR / "check_embedder.py")],
        env={**os.environ, "OLLAMA_API_BASE": args.ollama_url},
    )
    run([sys.executable, str(SCRIPT_DIR / "build_calculix_corpus.py")])
    run(
        [
            sys.executable,
            str(SCRIPT_DIR / "ingest_calculix.py"),
            "--base-url",
            args.r2r_url,
        ]
    )
    print("CalculiX retrieval index is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
