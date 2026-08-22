"""Machine-readable Gmsh Bridge contract."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MethodSpec:
    name: str
    title: str
    description: str
    read_only: bool
    destructive: bool = False
    idempotent: bool = False
    expose_mcp: bool = True

    @property
    def mcp_name(self):
        return "gmsh_{}".format(self.name.replace(".", "_"))

    def as_dict(self):
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "annotations": {
                "read_only": self.read_only,
                "destructive": self.destructive,
                "idempotent": self.idempotent,
                "open_world": False,
            },
            "mcp": {"exposed": self.expose_mcp, "name": self.mcp_name},
        }


METHOD_SPECS = (
    MethodSpec("system.ping", "Gmsh status", "Return Bridge, Gmsh, GUI and model status.", True, idempotent=True),
    MethodSpec("system.capabilities", "Gmsh capabilities", "Return the native cooperative Bridge contract.", True, idempotent=True, expose_mcp=False),
    MethodSpec("session.observe", "Observe Gmsh", "Read native model and mesh state and reconcile external human changes.", True),
    MethodSpec("session.acquire", "Acquire Gmsh", "Acquire the single-writer lease at an observed revision.", False),
    MethodSpec("session.release", "Release Gmsh", "Release the current writer lease for human or agent handoff.", False, idempotent=True),
    MethodSpec("session.history", "Gmsh history", "Return recent evidence-bearing atomic action records.", True),
    MethodSpec("model.open", "Open model", "Open STEP, BREP, GEO or MSH in the persistent Gmsh session.", False),
    MethodSpec("model.clear", "Clear model", "Clear the in-memory Gmsh model after revision and lease checks.", False, destructive=True),
    MethodSpec("model.entities", "List entities", "Return entity tags, bounding boxes and physical groups.", True),
    MethodSpec("model.entities_in_bbox", "Find entities", "Find native entities inside a bounding box.", True),
    MethodSpec("mesh.configure", "Configure mesh", "Set allowlisted Gmsh mesh options and return old/new values.", False),
    MethodSpec("mesh.generate", "Generate mesh", "Generate a 1D, 2D or 3D mesh and return native log, counts and quality.", False),
    MethodSpec("mesh.clear", "Clear mesh", "Clear mesh data without removing geometry.", False, destructive=True),
    MethodSpec("mesh.statistics", "Mesh statistics", "Return node, element and native quality statistics.", True),
    MethodSpec("mesh.write", "Write mesh", "Write the current mesh to an allowed path and hash the artifact.", False),
    MethodSpec("groups.create", "Create physical group", "Create and name a physical group from native entity tags.", False),
    MethodSpec("groups.list", "List physical groups", "List physical groups and their native entities.", True),
    MethodSpec("gui.update", "Refresh Gmsh GUI", "Refresh the existing Gmsh GUI without restarting it.", True, idempotent=True),
    MethodSpec("gui.select_entities", "Human entity selection", "Pause for a person to select entities in the existing Gmsh GUI.", False),
    MethodSpec("gui.save_screenshot", "Capture Gmsh", "Write the current native GUI view to an allowed image path.", False),
)

SPEC_BY_NAME = {spec.name: spec for spec in METHOD_SPECS}


def _object(properties=None, required=None):
    return {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False}


ACTOR = {"type": "string", "minLength": 1}
REVISION = {"type": "integer", "minimum": 0}
PATH = {"type": "string", "minLength": 1}
MUTATION = {"actor": ACTOR, "expected_revision": REVISION}


SCHEMAS = {
    "system.ping": _object(),
    "system.capabilities": _object(),
    "session.observe": _object(),
    "session.acquire": _object({**MUTATION, "ttl_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 3600}}, ["actor", "expected_revision"]),
    "session.release": _object({"actor": ACTOR}, ["actor"]),
    "session.history": _object({"limit": {"type": "integer", "minimum": 1, "maximum": 200}}),
    "model.open": _object({**MUTATION, "path": PATH}, ["actor", "expected_revision", "path"]),
    "model.clear": _object(MUTATION, ["actor", "expected_revision"]),
    "model.entities": _object({"dimension": {"type": "integer", "minimum": -1, "maximum": 3}}),
    "model.entities_in_bbox": _object({"minimum": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}, "maximum": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}, "dimension": {"type": "integer", "minimum": -1, "maximum": 3}}, ["minimum", "maximum"]),
    "mesh.configure": _object({**MUTATION, "options": {"type": "object", "additionalProperties": {"type": "number"}, "minProperties": 1}}, ["actor", "expected_revision", "options"]),
    "mesh.generate": _object({**MUTATION, "dimension": {"type": "integer", "minimum": 0, "maximum": 3}}, ["actor", "expected_revision", "dimension"]),
    "mesh.clear": _object(MUTATION, ["actor", "expected_revision"]),
    "mesh.statistics": _object({"quality_name": {"type": "string", "enum": sorted(["minSICN", "minSIGE", "minSJ", "gamma", "minDetJac"])}}),
    "mesh.write": _object({**MUTATION, "path": PATH}, ["actor", "expected_revision", "path"]),
    "groups.create": _object({**MUTATION, "dimension": {"type": "integer", "minimum": 0, "maximum": 3}, "entity_tags": {"type": "array", "items": {"type": "integer", "minimum": 1}, "minItems": 1}, "name": {"type": "string", "minLength": 1}, "tag": {"type": "integer"}}, ["actor", "expected_revision", "dimension", "entity_tags", "name"]),
    "groups.list": _object(),
    "gui.update": _object(),
    "gui.select_entities": _object({**MUTATION, "dimension": {"type": "integer", "minimum": -1, "maximum": 3}}, ["actor", "expected_revision"]),
    "gui.save_screenshot": _object({**MUTATION, "path": PATH}, ["actor", "expected_revision", "path"]),
}
