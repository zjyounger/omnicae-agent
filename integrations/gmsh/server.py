#!/usr/bin/env python3
"""Persistent native Gmsh GUI plus local JSON-RPC Bridge."""

import argparse
import os
import sys

import gmsh

from integrations.common.jsonrpc import QueuedJsonRpcRuntime
from integrations.common.security import PathPolicy
from integrations.gmsh.api import GmshAPI


def default_socket_path():
    configured = os.environ.get("CAE_GMSH_BRIDGE_SOCKET")
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return os.path.join(runtime, "omnicae-gmsh-{}.sock".format(os.getuid()))


def main():
    parser = argparse.ArgumentParser(description="OmniCAE native Gmsh Bridge")
    parser.add_argument("--socket", default=default_socket_path())
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--open", dest="open_path")
    args = parser.parse_args()

    gmsh.initialize(["omnicae-gmsh-bridge"] + (["-nopopup"] if args.headless else []))
    gui = not args.headless
    try:
        if args.open_path:
            gmsh.open(str(PathPolicy.from_environment().resolve_read(args.open_path)))
        if gui:
            gmsh.fltk.initialize()
            gmsh.fltk.update()
        policy = PathPolicy.from_environment()
        api = GmshAPI(gmsh, policy, args.socket, gui)
        runtime = QueuedJsonRpcRuntime(args.socket, api.dispatch)
        print("OmniCAE Gmsh Bridge listening at {}".format(args.socket), flush=True)
        runtime.run(
            pump=(lambda interval: gmsh.fltk.wait(interval)) if gui else None,
            keep_running=(lambda: bool(gmsh.fltk.isAvailable())) if gui else None,
        )
    except KeyboardInterrupt:
        return 130
    finally:
        gmsh.finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
