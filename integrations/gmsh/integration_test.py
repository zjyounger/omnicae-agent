#!/usr/bin/env python3
"""Live contract test for a running headless Gmsh Bridge."""

import argparse
import os

from integrations.common.client import LocalBridgeClient, LocalBridgeError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    args = parser.parse_args()
    client = LocalBridgeClient(args.socket)

    ping = client.call("system.ping")
    assert ping["interaction_level"] == "native-cooperative"
    assert ping["gui"] is False

    observed = client.call("session.observe")
    assert observed["state"]["entity_counts"]["3"] == 3
    revision = observed["revision"]
    actor = "gmsh-integration-test"
    client.call(
        "session.acquire",
        {"actor": actor, "expected_revision": revision, "ttl_seconds": 120},
    )

    configured = client.call(
        "mesh.configure",
        {
            "actor": actor,
            "expected_revision": revision,
            "options": {"Mesh.MeshSizeMin": 2.5, "Mesh.MeshSizeMax": 5.0},
        },
    )
    assert configured["status"] == "succeeded"
    revision = configured["revision_after"]

    generated = client.call(
        "mesh.generate",
        {"actor": actor, "expected_revision": revision, "dimension": 3},
    )
    stats = generated["result"]["statistics"]
    assert stats["nodes"] > 1000
    assert stats["volume_elements"] > 1000
    assert stats["quality"]["minimum"] > 0
    revision = generated["revision_after"]

    output = os.path.abspath("bridge/test-output/gmsh_native_bridge.msh")
    written = client.call(
        "mesh.write",
        {"actor": actor, "expected_revision": revision, "path": output},
    )
    artifact = written["result"]["artifact"]
    assert artifact["bytes"] > 0
    assert len(artifact["sha256"]) == 64
    revision = written["revision_after"]

    history = client.call("session.history", {"limit": 10})["steps"]
    assert [step["operation"] for step in history[-3:]] == [
        "mesh.configure",
        "mesh.generate",
        "mesh.write",
    ]

    try:
        client.call(
            "mesh.clear",
            {"actor": actor, "expected_revision": revision - 1},
        )
    except LocalBridgeError as exc:
        assert exc.code == 40901
    else:
        raise AssertionError("stale revision was accepted")

    client.call("session.release", {"actor": actor})
    print(
        "Gmsh Bridge integration passed: {} nodes, {} volume elements, min quality {:.6f}".format(
            stats["nodes"], stats["volume_elements"], stats["quality"]["minimum"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
