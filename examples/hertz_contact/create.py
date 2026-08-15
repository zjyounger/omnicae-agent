#!/usr/bin/env python3
"""Create and verify a CAD-only sphere-on-flat Hertz contact model through MCP."""

import argparse
import json
import os
import sys
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters, stdio_client


DOCUMENT = "HertzContact"
BLOCK = "LowerBlock"
SPHERE = "UpperSphere"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


async def invoke(client, name, arguments=None):
    result = await client.call_tool(name, arguments or {})
    if result.is_error:
        raise RuntimeError("{} failed: {}".format(name, result.structured_content))
    return result.structured_content


async def create_hertz_model(output_dir):
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    fcstd_path = output_dir / "hertz_contact.FCStd"
    step_path = output_dir / "hertz_contact.step"
    screenshot_path = output_dir / "hertz_contact.png"
    manifest_path = output_dir / "hertz_contact.json"

    project_root = Path(__file__).resolve().parents[2]
    adapter = StdioServerParameters(
        command=sys.executable,
        args=[str(project_root / "bridge" / "mcp_server.py")],
        cwd=str(project_root),
        env=dict(os.environ),
    )

    async with Client(stdio_client(adapter), mode="auto") as client:
        open_documents = await invoke(client, "freecad_documents_list")
        if DOCUMENT in {item["name"] for item in open_documents["documents"]}:
            await invoke(client, "freecad_documents_close", {"document": DOCUMENT})

        await invoke(
            client,
            "freecad_documents_new",
            {"name": DOCUMENT, "label": "Hertz Contact - Sphere on Flat"},
        )
        block = await invoke(
            client,
            "freecad_objects_create",
            {
                "document": DOCUMENT,
                "name": BLOCK,
                "label": "Lower flat block 80 x 80 x 10 mm",
                "kind": "box",
                "parameters": {"length": 80.0, "width": 80.0, "height": 10.0},
                "placement": [-40.0, -40.0, 0.0],
            },
        )
        sphere = await invoke(
            client,
            "freecad_objects_create",
            {
                "document": DOCUMENT,
                "name": SPHERE,
                "label": "Upper sphere R20 mm",
                "kind": "sphere",
                "parameters": {"radius": 20.0},
                "placement": [0.0, 0.0, 30.0],
            },
        )

        flat_matches = await invoke(
            client,
            "freecad_shapes_find_planar_faces",
            {
                "document": DOCUMENT,
                "object": BLOCK,
                "axis": "z",
                "value": 10.0,
                "normal": [0.0, 0.0, 1.0],
                "tolerance": 1e-8,
            },
        )
        sphere_faces = await invoke(
            client,
            "freecad_shapes_list_faces",
            {"document": DOCUMENT, "object": SPHERE},
        )

        if len(flat_matches["matches"]) != 1:
            raise AssertionError("Expected exactly one upper planar contact face")
        if len(sphere_faces["faces"]) != 1 or sphere_faces["faces"][0]["surface_type"] != "Sphere":
            raise AssertionError("Expected the upper body to have one spherical face")

        block_top = block["bounding_box"]["max"][2]
        sphere_bottom = sphere["bounding_box"]["min"][2]
        initial_gap = sphere_bottom - block_top
        if abs(initial_gap) > 1e-8:
            raise AssertionError("Bodies are not tangent; initial gap is {}".format(initial_gap))

        await invoke(
            client,
            "freecad_documents_save",
            {"document": DOCUMENT, "path": str(fcstd_path)},
        )
        await invoke(
            client,
            "freecad_io_export_step",
            {"document": DOCUMENT, "objects": [BLOCK, SPHERE], "path": str(step_path)},
        )
        await invoke(client, "freecad_gui_activate_workbench", {"name": "PartWorkbench"})
        await invoke(client, "freecad_gui_set_view", {"view": "axonometric"})
        await invoke(client, "freecad_gui_fit_all")
        await invoke(
            client,
            "freecad_gui_save_screenshot",
            {"path": str(screenshot_path), "width": 1400, "height": 1000},
        )

    manifest = {
        "problem": "3D sphere-on-flat Hertz contact CAD",
        "units": "mm",
        "document": DOCUMENT,
        "lower_body": block,
        "upper_body": sphere,
        "contact": {
            "type": "point_tangent",
            "point": [0.0, 0.0, 10.0],
            "initial_gap": initial_gap,
            "lower_face": flat_matches["matches"][0],
            "upper_face": sphere_faces["faces"][0],
        },
        "artifacts": {
            "fcstd": str(fcstd_path),
            "step": str(step_path),
            "screenshot": str(screenshot_path),
        },
        "scope": "CAD only; no material, load, mesh, contact property, or solve",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    arguments = parse_args()
    anyio.run(create_hertz_model, arguments.output_dir)
