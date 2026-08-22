#!/usr/bin/env python3
"""Live contract test for a running CalculiX job service."""

import argparse
import os
import shutil
import time

from integrations.common.client import LocalBridgeClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    args = parser.parse_args()

    output_dir = os.path.abspath("bridge/test-output/calculix_bridge")
    os.makedirs(output_dir, exist_ok=True)
    deck = os.path.join(output_dir, "cantilever.inp")
    shutil.copyfile("calculix/cantilever.inp", deck)

    client = LocalBridgeClient(args.socket)
    assert client.call("system.ping")["interaction_level"] == "batch"
    observed = client.call("session.observe")
    actor = "calculix-integration-test"
    client.call(
        "session.acquire",
        {"actor": actor, "expected_revision": observed["revision"], "ttl_seconds": 120},
    )
    started = client.call(
        "jobs.start",
        {
            "actor": actor,
            "expected_revision": observed["revision"],
            "deck_path": deck,
        },
    )
    job_id = started["result"]["job_id"]
    deadline = time.monotonic() + 30
    while True:
        status = client.call("jobs.status", {"job_id": job_id})
        if status["job"]["state"] != "running":
            break
        if time.monotonic() > deadline:
            raise AssertionError("CalculiX job did not finish")
        time.sleep(0.1)
    job = status["job"]
    assert job["state"] == "succeeded", job
    assert job["return_code"] == 0
    assert not job["solver_errors"]
    suffixes = {os.path.splitext(item["path"])[1] for item in job["outputs"]}
    assert ".frd" in suffixes
    assert any(item["path"].endswith(".omnicae.log") for item in job["outputs"])
    client.call("session.release", {"actor": actor})
    print("CalculiX service integration passed: job {}, outputs {}".format(job_id, sorted(suffixes)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
