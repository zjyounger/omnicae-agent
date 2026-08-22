#!/usr/bin/env python3
"""Local CalculiX job service."""

import argparse
import os
import shutil

from integrations.common.jsonrpc import QueuedJsonRpcRuntime
from integrations.common.security import PathPolicy
from integrations.calculix.api import CalculiXAPI
from integrations.calculix.runner import CalculiXRunner


def default_socket_path():
    configured = os.environ.get("CAE_CALCULIX_BRIDGE_SOCKET")
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return os.path.join(runtime, "omnicae-calculix-{}.sock".format(os.getuid()))


def main():
    parser = argparse.ArgumentParser(description="OmniCAE CalculiX job service")
    parser.add_argument("--socket", default=default_socket_path())
    parser.add_argument("--solver", default="ccx")
    args = parser.parse_args()
    solver = shutil.which(args.solver)
    if not solver:
        parser.error("CalculiX solver not found: {}".format(args.solver))
    runner = CalculiXRunner(solver)
    api = CalculiXAPI(runner, PathPolicy.from_environment(), args.socket)
    runtime = QueuedJsonRpcRuntime(args.socket, api.dispatch)
    print("OmniCAE CalculiX service listening at {}".format(args.socket), flush=True)
    try:
        runtime.run()
    except KeyboardInterrupt:
        return 130
    finally:
        runner.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
