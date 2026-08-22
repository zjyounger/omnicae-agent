# Application integrations

Application integrations own the real control boundary for one external
program. MCP is a thin optional adapter over that boundary.

## Install

One pip command installs the Python services, MCP dependencies, and the official
Gmsh application/SDK wheel:

    python3 -m venv .venv-mcp
    .venv-mcp/bin/pip install -r requirements.txt

CalculiX ccx, CalculiX GraphiX cgx, xdotool, and ImageMagick are external
executables, not Python packages. Gmsh does not require a separate system
installation when installed from requirements.txt.

## Start the application services

Run each service once per workstation/session. Agent MCP processes connect to
these sockets; they do not start another GUI.

    # Persistent native Gmsh GUI and Bridge
    .venv-mcp/bin/python -m integrations.gmsh.server --open path/to/model.step

    # Persistent CalculiX batch job service
    .venv-mcp/bin/python -m integrations.calculix.server

    # CGX controller; process.start creates one CGX window, or process.attach
    # binds an existing exact PID/window
    .venv-mcp/bin/python -m integrations.cgx.server

Default sockets live under XDG_RUNTIME_DIR and are user-only. Override them
with CAE_GMSH_BRIDGE_SOCKET, CAE_CALCULIX_BRIDGE_SOCKET, and
CAE_CGX_BRIDGE_SOCKET.

## Cooperative action sequence

Every state-changing call follows the same sequence:

1. session.observe returns native state and a revision.
2. session.acquire obtains the only write lease at that revision.
3. Execute one application operation with the same actor and current revision.
4. Inspect before/after state, application result, verification data and action
   ID.
5. Continue at revision_after, or session.release before human control.
6. After human control, observe again. Changed native state advances the
   revision and invalidates commands based on the old revision.

Gmsh implements this through its native Python/FLTK API on the GUI main thread.
CalculiX is intentionally a batch service. CGX has no supported native command
channel and therefore reports gui-fallback; an exclusive lease and visual
evidence reduce risk but cannot make keyboard automation equivalent to a native
API.

## Direct clients

Each integration has a JSON-RPC CLI independent of MCP:

    python3 -m integrations.gmsh.cli system.ping
    python3 -m integrations.calculix.cli jobs.list
    python3 -m integrations.cgx.cli process.status

## Tests

The live tests intentionally exercise real installed applications:

    python3 -m integrations.gmsh.integration_test --socket /path/to/test.sock
    python3 -m integrations.calculix.integration_test --socket /path/to/test.sock
    python3 -m integrations.cgx.integration_test --socket /path/to/test.sock \
      --pid PID --window-id WINDOW_ID
    .venv-mcp/bin/python -m integrations.mcp_integration_test
