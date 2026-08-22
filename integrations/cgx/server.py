#!/usr/bin/env python3
"""Local CGX controlled-process service."""

import argparse
import os

from integrations.common.jsonrpc import QueuedJsonRpcRuntime
from integrations.common.security import PathPolicy
from integrations.cgx.api import CGXAPI
from integrations.cgx.driver import CGXDriver


def default_socket_path():
    configured = os.environ.get("CAE_CGX_BRIDGE_SOCKET")
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return os.path.join(runtime, "omnicae-cgx-{}.sock".format(os.getuid()))


def main():
    parser = argparse.ArgumentParser(description="OmniCAE CGX controlled-process service")
    parser.add_argument("--socket", default=default_socket_path())
    parser.add_argument("--cgx", default="cgx")
    parser.add_argument("--evidence-directory", default="/tmp")
    args = parser.parse_args()
    driver = CGXDriver(args.cgx, args.evidence_directory)
    api = CGXAPI(driver, PathPolicy.from_environment(), args.socket)
    runtime = QueuedJsonRpcRuntime(args.socket, api.dispatch)
    print("OmniCAE CGX service listening at {}".format(args.socket), flush=True)
    try:
        runtime.run()
    except KeyboardInterrupt:
        return 130
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
