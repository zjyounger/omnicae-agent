# FreeCAD Bridge

## Start

Development environment:

```bash
export CAE_BRIDGE_ALLOWED_ROOTS="$PWD:/data/CAE"
freecad "$PWD/bridge/bootstrap.py"
```

`CAE_BRIDGE_SOCKET` sets the socket explicitly; if unset, `$XDG_RUNTIME_DIR/opensource-cae-freecad.sock` is preferred, otherwise `/tmp/opensource-cae-freecad-<uid>.sock`. Allowed roots are `:`-separated.

Default socket:

```text
$XDG_RUNTIME_DIR/opensource-cae-freecad.sock
```

## Client

```bash
python3 bridge/cli.py ping
python3 bridge/cli.py capabilities
python3 bridge/cli.py call documents.list
```

Calling with parameters:

```bash
python3 bridge/cli.py call documents.new --params '{"name":"Demo"}'
```

## After changing code

```bash
python3 bridge/cli.py call system.reload
```

Reloads the Bridge modules inside the same FreeCAD process, without restarting FreeCAD or losing open documents and meshes. If the new code fails to import, the old Bridge keeps serving.

Note: the MCP adapter caches its tool table in its own process, so after adding or changing a method it needs restarting to see the change.

## Integration test

Once the Bridge is running:

```bash
python3 bridge/integration_test.py
```

Produces `bridge/test-output/bridge_box.FCStd`, a STEP file, and a PNG, and verifies primitive creation, generic property read/write, boolean operations, dependency-protected delete, STEP round-trip, reconnection, protocol errors, path isolation, and that a client disconnecting mid-way through a slow GUI call does not bring the Bridge down. It covers the CAD Bridge only, not meshing or FEM.

The client default timeout is 30 s, to leave room for slow GUI calls.

## Claude Code / MCP

Create a dedicated MCP environment:

```bash
python3 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install -r requirements-mcp.txt
```

The project's root `.mcp.json` makes Claude Code start `bridge/mcp_server.py` automatically. The FreeCAD Bridge must already be running; the MCP adapter needs no separate terminal.

```bash
claude mcp list
```

If the Bridge uses an explicit socket, export the same variable before starting Claude Code:

```bash
export CAE_BRIDGE_SOCKET=/tmp/opensource-cae-freecad-test.sock
claude
```

MCP integration test:

```bash
.venv-mcp/bin/python bridge/mcp_integration_test.py
```
