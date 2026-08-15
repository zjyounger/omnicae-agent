#!/usr/bin/env python3
"""CAD-only integration test against a running FreeCAD bridge."""

import json
import math
import socket
import time
from pathlib import Path

from client import BridgeClient, BridgeClientError, BridgeRemoteError, default_socket_path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def raw_request(socket_path, payload):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(60.0)
        connection.connect(socket_path)
        connection.sendall(payload + b"\n")
        response = bytearray()
        while b"\n" not in response:
            chunk = connection.recv(65536)
            if not chunk:
                raise AssertionError("Bridge closed before returning a response")
            response.extend(chunk)
    raw, _ = response.split(b"\n", 1)
    return json.loads(raw.decode("utf-8"))


def main():
    output_dir = Path(__file__).resolve().parent / "test-output"
    output_dir.mkdir(exist_ok=True)
    fcstd_path = output_dir / "bridge_box.FCStd"
    step_path = output_dir / "bridge_box.step"
    image_path = output_dir / "bridge_box.png"
    socket_path = default_socket_path()

    for path in (fcstd_path, step_path, image_path):
        if path.exists():
            path.unlink()

    client = BridgeClient(timeout=60.0)
    client.connect()
    ping = client.call("system.ping")
    capabilities = client.call("system.capabilities")

    existing = client.call("documents.list")["documents"]
    for document_name in ("BridgeImported", "BridgeIntegration"):
        if any(item["name"] == document_name for item in existing):
            client.call("documents.close", {"document": document_name})

    client.call("documents.new", {"name": "BridgeIntegration", "label": "Bridge Integration"})
    box = client.call(
        "objects.create",
        {
            "document": "BridgeIntegration",
            "name": "TestBox",
            "label": "Bridge test box",
            "kind": "box",
            "parameters": {"length": 40.0, "width": 20.0, "height": 10.0},
        },
    )
    require(abs(box["volume"] - 8000.0) < 1e-8, "Unexpected box volume")
    require(box["bounding_box"]["size"] == [40.0, 20.0, 10.0], "Unexpected bounds")

    faces = client.call(
        "shapes.list_faces", {"document": "BridgeIntegration", "object": "TestBox"}
    )["faces"]
    require(len(faces) == 6, "A box must have six faces")
    left = client.call(
        "shapes.find_planar_faces",
        {
            "document": "BridgeIntegration",
            "object": "TestBox",
            "axis": "x",
            "value": 0.0,
            "tolerance": 1e-8,
        },
    )["matches"]
    right = client.call(
        "shapes.find_planar_faces",
        {
            "document": "BridgeIntegration",
            "object": "TestBox",
            "axis": "x",
            "value": 40.0,
            "tolerance": 1e-8,
        },
    )["matches"]
    require(len(left) == 1 and len(right) == 1, "Could not identify both end faces")

    # A rejected create must not leave a half-configured object behind, and the
    # same name must stay usable afterwards.
    try:
        client.call(
            "objects.create",
            {
                "document": "BridgeIntegration",
                "name": "Rejected",
                "kind": "box",
                "parameters": {"length": "forty", "width": 20, "height": 10},
            },
        )
    except BridgeRemoteError as exc:
        require(exc.code == -32602, "Wrong error code for invalid dimensions")
    else:
        raise AssertionError("Invalid dimensions were accepted")
    listed = client.call("objects.list", {"document": "BridgeIntegration"})["objects"]
    require(
        not any(item["name"] == "Rejected" for item in listed),
        "A failed create left a partial object behind",
    )
    retried = client.call(
        "objects.create",
        {
            "document": "BridgeIntegration",
            "name": "Rejected",
            "kind": "box",
            "parameters": {"length": 40, "width": 20, "height": 10},
        },
    )
    require(abs(retried["volume"] - 8000.0) < 1e-8, "Retry after a rejected create failed")
    client.call("objects.delete", {"document": "BridgeIntegration", "object": "Rejected"})

    # Generic property API: create a plain cylinder, then narrow it to a half
    # cylinder through a property that objects.create deliberately does not expose.
    cylinder = client.call(
        "objects.create",
        {
            "document": "BridgeIntegration",
            "name": "Pin",
            "kind": "cylinder",
            "parameters": {"radius": 5.0, "height": 20.0},
            "placement": [100.0, 0.0, 0.0],
        },
    )
    require(abs(cylinder["volume"] - math.pi * 25.0 * 20.0) < 1e-6, "Unexpected cylinder volume")
    updated = client.call(
        "objects.set_properties",
        {"document": "BridgeIntegration", "object": "Pin", "values": {"Angle": 180.0}},
    )
    require(abs(updated["properties"]["Angle"]["value"] - 180.0) < 1e-9, "Property write was lost")
    half = client.call("objects.inspect", {"document": "BridgeIntegration", "object": "Pin"})
    require(
        abs(half["volume"] - math.pi * 25.0 * 20.0 / 2.0) < 1e-6,
        "Property change did not affect the shape",
    )
    try:
        client.call(
            "objects.set_properties",
            {"document": "BridgeIntegration", "object": "Pin", "values": {"Proxy": "x"}},
        )
    except BridgeRemoteError as exc:
        require(exc.code == -32602, "Wrong error code for an unwritable property")
    else:
        raise AssertionError("An unsupported property type was accepted")

    # Rotation and boolean cut.
    client.call(
        "objects.transform",
        {
            "document": "BridgeIntegration",
            "object": "Pin",
            "position": [20.0, 10.0, -5.0],
            "rotation": {"axis": [1.0, 0.0, 0.0], "angle": 0.0},
        },
    )
    client.call(
        "objects.create",
        {
            "document": "BridgeIntegration",
            "name": "Blank",
            "kind": "box",
            "parameters": {"length": 40.0, "width": 20.0, "height": 10.0},
            "placement": [0.0, 0.0, -40.0],
        },
    )
    client.call(
        "objects.create",
        {
            "document": "BridgeIntegration",
            "name": "Hole",
            "kind": "cylinder",
            "parameters": {"radius": 4.0, "height": 30.0},
            "placement": [20.0, 10.0, -50.0],
        },
    )
    drilled = client.call(
        "objects.boolean",
        {
            "document": "BridgeIntegration",
            "name": "Drilled",
            "operation": "cut",
            "objects": ["Blank", "Hole"],
        },
    )
    expected = 40.0 * 20.0 * 10.0 - math.pi * 16.0 * 10.0
    require(abs(drilled["volume"] - expected) < 1e-6, "Boolean cut volume is wrong")
    require(drilled["face_count"] > 6, "Boolean cut did not add the bore face")
    try:
        client.call("objects.delete", {"document": "BridgeIntegration", "object": "Blank"})
    except BridgeRemoteError as exc:
        require(exc.code == -32602, "Wrong error code for deleting a used operand")
    else:
        raise AssertionError("Deleting a boolean operand was accepted")

    client.call(
        "documents.save",
        {"document": "BridgeIntegration", "path": str(fcstd_path)},
    )
    client.call(
        "io.export_step",
        {
            "document": "BridgeIntegration",
            "objects": ["TestBox"],
            "path": str(step_path),
        },
    )
    client.call("gui.set_view", {"view": "axonometric"})
    client.call("gui.fit_all")
    client.call(
        "gui.save_screenshot",
        {"path": str(image_path), "width": 1200, "height": 800},
    )
    client.call("documents.new", {"name": "BridgeImported", "label": "STEP import"})
    imported = client.call(
        "io.import_step",
        {"document": "BridgeImported", "path": str(step_path)},
    )
    require(imported["created_objects"], "STEP import created no objects")
    imported_shape = client.call(
        "objects.inspect",
        {"document": "BridgeImported", "object": imported["created_objects"][0]},
    )
    require(abs(imported_shape["volume"] - 8000.0) < 1e-8, "STEP round-trip changed volume")
    client.call("documents.close", {"document": "BridgeImported"})
    active_workbench = client.call("gui.activate_workbench", {"name": "PartWorkbench"})
    require(active_workbench["workbench"] == "PartWorkbench", "Workbench activation failed")
    client.close()

    with BridgeClient(timeout=60.0) as reconnected:
        documents = reconnected.call("documents.list")["documents"]
        require(any(item["name"] == "BridgeIntegration" for item in documents), "Reconnect lost state")
        try:
            reconnected.call(
                "documents.save",
                {"document": "BridgeIntegration", "path": "/etc/bridge-escape.FCStd"},
            )
        except BridgeRemoteError as exc:
            require(exc.code == -32602, "Wrong error code for path escape")
        else:
            raise AssertionError("Path escape was accepted")
        try:
            reconnected.call("python.eval", {"code": "1+1"})
        except BridgeRemoteError as exc:
            require(exc.code == -32601, "Wrong error code for unknown method")
        else:
            raise AssertionError("Unknown method was accepted")
        try:
            reconnected.call(
                "objects.create",
                {
                    "document": "BridgeIntegration",
                    "name": "BadBox",
                    "kind": "box",
                    "parameters": {"length": "forty", "width": 20, "height": 10},
                },
            )
        except BridgeRemoteError as exc:
            require(exc.code == -32602, "Wrong error code for invalid parameters")
        else:
            raise AssertionError("Invalid CAD parameters were accepted")

    parse_error = raw_request(socket_path, b"{broken json")
    require(parse_error["error"]["code"] == -32700, "Malformed JSON was not rejected")

    # A client that disappears while a slow GUI call is still running used to
    # raise inside the Qt event loop when the Bridge wrote the reply back.
    abandoned = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    abandoned.connect(socket_path)
    abandoned.sendall(b'{"jsonrpc":"2.0","id":99,"method":"gui.fit_all","params":{}}\n')
    abandoned.close()

    with BridgeClient(socket_path=socket_path, timeout=60.0) as survivor:
        survivor.call("system.ping")

    for path in (fcstd_path, step_path, image_path):
        require(path.is_file() and path.stat().st_size > 0, "Missing artifact: {}".format(path))

    # Hot reload: the Bridge must come back on the same FreeCAD process, and a
    # reload that cannot import must leave the running Bridge serving.
    with BridgeClient(timeout=60.0) as reloader:
        pid_before = reloader.call("system.ping")["pid"]
        require(reloader.call("system.reload")["scheduled"] is True, "Reload was not scheduled")
    deadline = time.time() + 30.0
    reloaded = None
    while time.time() < deadline:
        try:
            with BridgeClient(timeout=60.0) as probe:
                reloaded = probe.call("system.ping")
            break
        except (OSError, BridgeClientError):
            time.sleep(0.5)
    require(reloaded is not None, "Bridge did not come back after reload")
    require(reloaded["pid"] == pid_before, "Reload restarted FreeCAD instead of reloading in place")

    summary = {
        "ping": ping,
        "method_count": len(capabilities["methods"]),
        "box": box,
        "left_face": left[0],
        "right_face": right[0],
        "artifacts": [str(fcstd_path), str(step_path), str(image_path)],
        "reconnect": True,
        "step_round_trip": True,
        "partial_object_not_left_behind": True,
        "generic_property_api": True,
        "boolean_cut": True,
        "dependency_protected_delete": True,
        "malformed_json_rejected": True,
        "invalid_params_rejected": True,
        "path_escape_rejected": True,
        "abandoned_client_survived": True,
        "hot_reload_same_process": True,
        "arbitrary_eval_rejected": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
