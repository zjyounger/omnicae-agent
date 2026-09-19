"""CGX controlled-process contract."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MethodSpec:
    name: str
    description: str
    read_only: bool
    destructive: bool = False

    @property
    def mcp_name(self):
        return "cgx_{}".format(self.name.replace(".", "_"))

    def as_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "annotations": {
                "read_only": self.read_only,
                "destructive": self.destructive,
                "idempotent": False,
                "open_world": False,
            },
            "mcp": {"name": self.mcp_name},
        }


METHOD_SPECS = (
    MethodSpec("system.ping", "Return CGX process, window and fallback availability.", True),
    MethodSpec("system.capabilities", "Return the explicitly limited gui-fallback contract.", True),
    MethodSpec("session.observe", "Capture process and visual state and reconcile human changes.", True),
    MethodSpec("session.acquire", "Acquire exclusive GUI write control at an observed revision.", False),
    MethodSpec("session.release", "Release GUI control before a person interacts.", False),
    MethodSpec("session.history", "Return recent command records and evidence.", True),
    MethodSpec("process.start", "Start one persistent CGX window on an allowed input file.", False),
    MethodSpec("process.attach", "Attach to one exact existing CGX PID and window.", False),
    MethodSpec("process.status", "Return exact PID, window, title, log and confidence.", True),
    MethodSpec("process.stop", "Stop the exact attached CGX process.", False, destructive=True),
    MethodSpec("command.execute", "Send one allowlisted CGX command through the declared GUI fallback.", False),
    MethodSpec("gui.save_screenshot", "Capture the exact attached CGX window and hash it.", False),
)

SPEC_BY_NAME = {spec.name: spec for spec in METHOD_SPECS}


def _object(properties=None, required=None):
    return {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False}


ACTOR = {"type": "string", "minLength": 1}
REVISION = {"type": "integer", "minimum": 0}
MUTATION = {"actor": ACTOR, "expected_revision": REVISION}
PATH = {"type": "string", "minLength": 1}
SCHEMAS = {
    "system.ping": _object(), "system.capabilities": _object(), "session.observe": _object(),
    "session.acquire": _object({**MUTATION, "ttl_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 3600}}, ["actor", "expected_revision"]),
    "session.release": _object({"actor": ACTOR}, ["actor"]),
    "session.history": _object({"limit": {"type": "integer", "minimum": 1, "maximum": 200}}),
    "process.start": _object({**MUTATION, "input_path": PATH, "deck_path": PATH}, ["actor", "expected_revision", "input_path"]),
    "process.attach": _object({**MUTATION, "pid": {"type": "integer", "minimum": 1}, "window_id": {"type": "string", "minLength": 1}}, ["actor", "expected_revision", "pid", "window_id"]),
    "process.status": _object(),
    "process.stop": _object(MUTATION, ["actor", "expected_revision"]),
    "command.execute": _object({**MUTATION, "command": {"type": "string", "minLength": 1}, "settle_seconds": {"type": "number", "minimum": 0.1, "maximum": 10}}, ["actor", "expected_revision", "command"]),
    "gui.save_screenshot": _object({**MUTATION, "path": PATH}, ["actor", "expected_revision", "path"]),
}
