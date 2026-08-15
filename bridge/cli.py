#!/usr/bin/env python3
"""Command-line client for the FreeCAD bridge."""

import argparse
import json
import sys

from client import BridgeClient, BridgeRemoteError


def main():
    parser = argparse.ArgumentParser(description="Call the Open Source CAE FreeCAD Bridge")
    parser.add_argument("--socket", help="Unix socket path")
    parser.add_argument("--timeout", type=float, default=BridgeClient.DEFAULT_TIMEOUT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ping")
    subparsers.add_parser("capabilities")

    call_parser = subparsers.add_parser("call")
    call_parser.add_argument("method")
    call_parser.add_argument("--params", default="{}", help="JSON object")

    args = parser.parse_args()
    if args.command == "ping":
        method, params = "system.ping", {}
    elif args.command == "capabilities":
        method, params = "system.capabilities", {}
    else:
        method = args.method
        try:
            params = json.loads(args.params)
        except ValueError as exc:
            parser.error("--params is not valid JSON: {}".format(exc))
        if not isinstance(params, dict):
            parser.error("--params must decode to a JSON object")

    try:
        with BridgeClient(args.socket, args.timeout) as client:
            result = client.call(method, params)
    except BridgeRemoteError as exc:
        print(
            json.dumps(
                {"error": {"code": exc.code, "message": exc.message, "data": exc.data}},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
