#!/usr/bin/env python3
"""Call the local Gmsh Bridge."""

import argparse
import json

from integrations.common.client import LocalBridgeClient
from integrations.gmsh.server import default_socket_path


def main():
    parser = argparse.ArgumentParser(description="Call the OmniCAE Gmsh Bridge")
    parser.add_argument("method")
    parser.add_argument("--params", default="{}")
    parser.add_argument("--socket", default=default_socket_path())
    args = parser.parse_args()
    params = json.loads(args.params)
    result = LocalBridgeClient(args.socket).call(args.method, params)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
