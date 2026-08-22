#!/usr/bin/env python3
"""Attach to one existing CGX window and verify the guarded GUI fallback."""

import argparse

from integrations.common.client import LocalBridgeClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--window-id", required=True)
    args = parser.parse_args()

    client = LocalBridgeClient(args.socket)
    ping = client.call("system.ping")
    assert ping["interaction_level"] == "gui-fallback"
    assert ping["native_command_channel"] is False
    observed = client.call("session.observe")
    actor = "cgx-integration-test"
    client.call(
        "session.acquire",
        {"actor": actor, "expected_revision": observed["revision"], "ttl_seconds": 120},
    )
    attached = client.call(
        "process.attach",
        {
            "actor": actor,
            "expected_revision": observed["revision"],
            "pid": args.pid,
            "window_id": args.window_id,
        },
    )
    assert attached["result"]["running"] is True
    revision = attached["revision_after"]
    executed = client.call(
        "command.execute",
        {
            "actor": actor,
            "expected_revision": revision,
            "command": "frame",
            "settle_seconds": 0.5,
        },
    )
    result = executed["result"]
    assert result["transport"] == "xdotool"
    assert result["acknowledgement"] != "failed", result
    assert result["process_running"] is True
    assert len(result["before_screenshot"]["sha256"]) == 64
    assert len(result["after_screenshot"]["sha256"]) == 64
    client.call("session.release", {"actor": actor})
    print("CGX fallback integration passed: acknowledgement={}".format(result["acknowledgement"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
