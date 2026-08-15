"""Versioned Bridge method contract shared by FreeCAD and external adapters."""

from dataclasses import dataclass
from typing import Any, Dict


BRIDGE_VERSION = "0.5.0"
BRIDGE_PROTOCOL_VERSION = "1.4"
CONTRACT_VERSION = "1.4"


@dataclass(frozen=True)
class MethodSpec:
    name: str
    title: str
    description: str
    input_schema: Dict[str, Any]
    read_only: bool
    destructive: bool = False
    idempotent: bool = False
    expose_mcp: bool = True
    deprecated: bool = False

    @property
    def mcp_name(self):
        return "freecad_{}".format(self.name.replace(".", "_"))

    def as_capability(self):
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "input_schema": self.input_schema,
            "annotations": {
                "read_only": self.read_only,
                "destructive": self.destructive,
                "idempotent": self.idempotent,
                "open_world": False,
            },
            "mcp": {"exposed": self.expose_mcp, "name": self.mcp_name},
            "deprecated": self.deprecated,
        }


def _object(properties=None, required=None):
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


def _string(description):
    return {"type": "string", "minLength": 1, "description": description}


DOCUMENT = _string("FreeCAD internal document name; omit to use the active document.")
OBJECT = _string("FreeCAD internal object name.")
PATH = _string("File path inside a Bridge allowed root.")
PLACEMENT = {
    "type": "array",
    "items": {"type": "number"},
    "minItems": 3,
    "maxItems": 3,
    "default": [0, 0, 0],
    "description": "Object origin [x, y, z] in millimetres.",
}
BOX_PARAMETERS = _object(
    {
        "length": {"type": "number", "exclusiveMinimum": 0, "description": "X size in mm."},
        "width": {"type": "number", "exclusiveMinimum": 0, "description": "Y size in mm."},
        "height": {"type": "number", "exclusiveMinimum": 0, "description": "Z size in mm."},
    },
    ["length", "width", "height"],
)
SPHERE_PARAMETERS = _object(
    {
        "radius": {"type": "number", "exclusiveMinimum": 0, "description": "Radius in mm."},
    },
    ["radius"],
)
CYLINDER_PARAMETERS = _object(
    {
        "radius": {"type": "number", "exclusiveMinimum": 0, "description": "Radius in mm."},
        "height": {"type": "number", "exclusiveMinimum": 0, "description": "Z height in mm."},
    },
    ["radius", "height"],
)
CONE_PARAMETERS = _object(
    {
        "radius1": {"type": "number", "minimum": 0, "description": "Base radius in mm; 0 gives a point."},
        "radius2": {"type": "number", "minimum": 0, "description": "Top radius in mm; 0 gives a point."},
        "height": {"type": "number", "exclusiveMinimum": 0, "description": "Z height in mm."},
    },
    ["radius1", "radius2", "height"],
)
TORUS_PARAMETERS = _object(
    {
        "radius1": {"type": "number", "exclusiveMinimum": 0, "description": "Ring radius in mm."},
        "radius2": {"type": "number", "exclusiveMinimum": 0, "description": "Tube radius in mm."},
    },
    ["radius1", "radius2"],
)
PRIMITIVE_PARAMETERS = {
    "box": BOX_PARAMETERS,
    "sphere": SPHERE_PARAMETERS,
    "cylinder": CYLINDER_PARAMETERS,
    "cone": CONE_PARAMETERS,
    "torus": TORUS_PARAMETERS,
}
FEM_OBJECT_KINDS = (
    "analysis",
    "solver_ccx",
    "material_solid",
    "mesh_gmsh",
    "mesh_region",
    "mesh_group",
    "constraint_fixed",
    "constraint_displacement",
    "constraint_force",
    "constraint_pressure",
    "constraint_contact",
    "constraint_tie",
    "constraint_spring",
    "constraint_selfweight",
    "constraint_sectionprint",
    "constraint_transform",
    "constraint_rigidbody",
)
ROTATION = _object(
    {
        "axis": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 3,
            "maxItems": 3,
            "default": [0, 0, 1],
            "description": "Rotation axis [x, y, z]; must not be the zero vector.",
        },
        "angle": {"type": "number", "description": "Rotation angle in degrees."},
    },
    ["angle"],
)


METHOD_SPECS = (
    MethodSpec(
        "system.ping",
        "FreeCAD status",
        "Check Bridge and FreeCAD versions, process, socket, and active document.",
        _object(),
        read_only=True,
        idempotent=True,
    ),
    MethodSpec(
        "system.capabilities",
        "Bridge capabilities",
        "Return the versioned Bridge contract used by client adapters.",
        _object(),
        read_only=True,
        idempotent=True,
        expose_mcp=False,
    ),
    MethodSpec(
        "system.reload",
        "Reload the Bridge",
        "Reload Bridge modules in place so edited code takes effect without restarting "
        "FreeCAD. If the new code fails to import, the running Bridge keeps serving.",
        _object(),
        read_only=False,
        expose_mcp=False,
    ),
    MethodSpec(
        "documents.list",
        "List documents",
        "List open FreeCAD documents and their basic state.",
        _object(),
        read_only=True,
        idempotent=True,
    ),
    MethodSpec(
        "documents.new",
        "Create document",
        "Create and activate an empty FreeCAD document.",
        _object(
            {
                "name": _string("Stable internal document name using letters, digits, or underscores."),
                "label": {"type": "string", "description": "Optional user-visible document label."},
            },
            ["name"],
        ),
        read_only=False,
    ),
    MethodSpec(
        "documents.activate",
        "Activate document",
        "Make an open FreeCAD document active.",
        _object({"name": _string("Internal name of an open document.")}, ["name"]),
        read_only=False,
        idempotent=True,
    ),
    MethodSpec(
        "documents.open",
        "Open FCStd",
        "Open an FCStd file from an allowed path.",
        _object({"path": PATH}, ["path"]),
        read_only=False,
    ),
    MethodSpec(
        "documents.save",
        "Save document",
        "Save a document as FCStd; path is required until the document has a filename.",
        _object({"document": DOCUMENT, "path": PATH}),
        read_only=False,
        idempotent=True,
    ),
    MethodSpec(
        "documents.close",
        "Close document",
        "Close a FreeCAD document. Unsaved state can be discarded.",
        _object({"document": DOCUMENT}),
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    MethodSpec(
        "objects.create",
        "Create CAD object",
        "Create a parametric CAD primitive: box, sphere, cylinder, cone, or torus. "
        "Use objects.set_properties for any parameter not covered here.",
        {
            "type": "object",
            "properties": {
                "document": DOCUMENT,
                "name": _string("Stable internal object name."),
                "label": {"type": "string", "description": "Optional user-visible object label."},
                "kind": {
                    "type": "string",
                    "enum": sorted(PRIMITIVE_PARAMETERS),
                    "description": "Primitive kind.",
                },
                "parameters": {"type": "object"},
                "placement": PLACEMENT,
                "rotation": ROTATION,
            },
            "required": ["name", "kind", "parameters"],
            "additionalProperties": False,
            "oneOf": [
                {"properties": {"kind": {"const": kind}, "parameters": schema}}
                for kind, schema in sorted(PRIMITIVE_PARAMETERS.items())
            ],
        },
        read_only=False,
    ),
    MethodSpec(
        "objects.list",
        "List objects",
        "List objects in a document with name, label, type, visibility, and shape state.",
        _object({"document": DOCUMENT}),
        read_only=True,
        idempotent=True,
    ),
    MethodSpec(
        "objects.delete",
        "Delete object",
        "Delete an object. Refuses while other objects still depend on it.",
        _object({"document": DOCUMENT, "object": OBJECT}, ["object"]),
        read_only=False,
        destructive=True,
    ),
    MethodSpec(
        "objects.get_properties",
        "Read object properties",
        "Read editable properties of an object, including parametric dimensions.",
        _object(
            {
                "document": DOCUMENT,
                "object": OBJECT,
                "properties": {
                    "type": "array",
                    "items": _string("Property name."),
                    "minItems": 1,
                    "description": "Optional subset; omit to read every supported property.",
                },
            },
            ["object"],
        ),
        read_only=True,
        idempotent=True,
    ),
    MethodSpec(
        "objects.set_properties",
        "Set object properties",
        "Set scalar, enumeration, vector, or placement properties on any object. "
        "This is the generic way to adjust parameters without a dedicated method.",
        _object(
            {
                "document": DOCUMENT,
                "object": OBJECT,
                "values": {
                    "type": "object",
                    "minProperties": 1,
                    "description": "Property name to value. Numbers are millimetres or degrees.",
                },
            },
            ["object", "values"],
        ),
        read_only=False,
        idempotent=True,
    ),
    MethodSpec(
        "objects.transform",
        "Move or rotate object",
        "Set or apply an object placement using a position and an axis-angle rotation.",
        _object(
            {
                "document": DOCUMENT,
                "object": OBJECT,
                "position": PLACEMENT,
                "rotation": ROTATION,
                "relative": {
                    "type": "boolean",
                    "default": False,
                    "description": "Apply on top of the current placement instead of replacing it.",
                },
            },
            ["object"],
        ),
        read_only=False,
    ),
    MethodSpec(
        "objects.boolean",
        "Boolean operation",
        "Combine solids with cut, fuse, or common. Operands become children of the result.",
        _object(
            {
                "document": DOCUMENT,
                "name": _string("Stable internal name for the result object."),
                "label": {"type": "string", "description": "Optional user-visible label."},
                "operation": {
                    "type": "string",
                    "enum": ["cut", "fuse", "common"],
                    "description": "cut uses exactly two operands: base minus tool.",
                },
                "objects": {
                    "type": "array",
                    "items": OBJECT,
                    "minItems": 2,
                    "description": "Operand names in order; for cut the first is the base.",
                },
            },
            ["name", "operation", "objects"],
        ),
        read_only=False,
    ),
    MethodSpec(
        "objects.inspect",
        "Inspect CAD object",
        "Read type, label, volume, area, solids, faces, and bounding box for an object.",
        _object({"document": DOCUMENT, "object": OBJECT}, ["object"]),
        read_only=True,
        idempotent=True,
    ),
    MethodSpec(
        "shapes.list_faces",
        "List shape faces",
        "List face index, surface type, area, center, and representative normal.",
        _object({"document": DOCUMENT, "object": OBJECT}, ["object"]),
        read_only=True,
        idempotent=True,
    ),
    MethodSpec(
        "shapes.find_planar_faces",
        "Find planar faces",
        "Find planar faces by center coordinate and optional normal direction.",
        _object(
            {
                "document": DOCUMENT,
                "object": OBJECT,
                "axis": {"type": "string", "enum": ["x", "y", "z"]},
                "value": {"type": "number"},
                "tolerance": {"type": "number", "minimum": 0, "default": 1e-7},
                "normal": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "normal_tolerance": {"type": "number", "minimum": 0, "default": 1e-6},
            },
            ["object", "axis", "value"],
        ),
        read_only=True,
        idempotent=True,
    ),
    MethodSpec(
        "fem.create",
        "Create FEM object",
        "Create an analysis, solver, material, mesh, or constraint object and optionally "
        "add it to an analysis. Configure it afterwards with objects.set_properties; the "
        "reply lists the property names available on the new object.",
        _object(
            {
                "document": DOCUMENT,
                "name": _string("Stable internal object name."),
                "label": {"type": "string", "description": "Optional user-visible label."},
                "kind": {
                    "type": "string",
                    "enum": sorted(FEM_OBJECT_KINDS),
                    "description": "FEM object kind.",
                },
                "analysis": _string("Optional analysis object to add this member to."),
            },
            ["name", "kind"],
        ),
        read_only=False,
    ),
    MethodSpec(
        "fem.mesh",
        "Generate FEM mesh",
        "Run Gmsh for a mesh object and report the resulting node and element counts.",
        _object({"document": DOCUMENT, "object": OBJECT}, ["object"]),
        read_only=False,
        idempotent=True,
    ),
    MethodSpec(
        "fem.solve",
        "Solve with CalculiX",
        "Write the CalculiX deck, run the solver, load results, and report result extremes. "
        "Can take minutes; raise the client timeout accordingly.",
        _object(
            {
                "document": DOCUMENT,
                "analysis": _string("Analysis object name."),
                "solver": _string("Solver object name inside that analysis."),
                "working_dir": _string("Existing directory inside a Bridge allowed root."),
            },
            ["analysis", "solver", "working_dir"],
        ),
        read_only=False,
    ),
    MethodSpec(
        "io.import_step",
        "Import STEP",
        "Import a STEP file from an allowed path into an open document.",
        _object({"document": DOCUMENT, "path": PATH}, ["path"]),
        read_only=False,
    ),
    MethodSpec(
        "io.export_step",
        "Export STEP",
        "Export selected shape objects, or all shape objects, to an allowed STEP path.",
        _object(
            {
                "document": DOCUMENT,
                "objects": {"type": "array", "items": OBJECT, "minItems": 1},
                "path": PATH,
            },
            ["path"],
        ),
        read_only=False,
        idempotent=True,
    ),
    MethodSpec(
        "gui.activate_workbench",
        "Activate workbench",
        "Activate an installed FreeCAD GUI workbench by internal name.",
        _object({"name": _string("Workbench internal name, such as PartWorkbench.")}, ["name"]),
        read_only=False,
        idempotent=True,
    ),
    MethodSpec(
        "gui.set_view",
        "Set camera view",
        "Set the active 3D view to a standard orientation.",
        _object(
            {
                "view": {
                    "type": "string",
                    "enum": ["axonometric", "front", "rear", "left", "right", "top", "bottom"],
                }
            },
            ["view"],
        ),
        read_only=False,
        idempotent=True,
    ),
    MethodSpec(
        "gui.fit_all",
        "Fit all",
        "Fit all visible geometry into the active 3D view.",
        _object(),
        read_only=False,
        idempotent=True,
    ),
    MethodSpec(
        "gui.save_screenshot",
        "Save 3D screenshot",
        "Save the active 3D view as PNG or JPEG inside an allowed root.",
        _object(
            {
                "path": PATH,
                "width": {"type": "integer", "minimum": 64, "maximum": 8192, "default": 1600},
                "height": {"type": "integer", "minimum": 64, "maximum": 8192, "default": 1000},
            },
            ["path"],
        ),
        read_only=False,
        idempotent=True,
    ),
    # Compatibility aliases remain callable by older clients but are intentionally
    # hidden from MCP discovery so they do not consume agent context.
    MethodSpec(
        "cad.create_box",
        "Create box (legacy)",
        "Deprecated compatibility alias for objects.create kind=box.",
        _object(),
        read_only=False,
        expose_mcp=False,
        deprecated=True,
    ),
    MethodSpec(
        "cad.inspect_object",
        "Inspect object (legacy)",
        "Deprecated compatibility alias for objects.inspect.",
        _object(),
        read_only=True,
        expose_mcp=False,
        deprecated=True,
    ),
    MethodSpec(
        "cad.list_faces",
        "List faces (legacy)",
        "Deprecated compatibility alias for shapes.list_faces.",
        _object(),
        read_only=True,
        expose_mcp=False,
        deprecated=True,
    ),
    MethodSpec(
        "cad.find_planar_faces",
        "Find planar faces (legacy)",
        "Deprecated compatibility alias for shapes.find_planar_faces.",
        _object(),
        read_only=True,
        expose_mcp=False,
        deprecated=True,
    ),
)

METHOD_SPEC_BY_NAME = {spec.name: spec for spec in METHOD_SPECS}
MCP_SPEC_BY_NAME = {spec.mcp_name: spec for spec in METHOD_SPECS if spec.expose_mcp}
