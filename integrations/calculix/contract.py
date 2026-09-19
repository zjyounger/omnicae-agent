"""CalculiX job-service contract."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MethodSpec:
    name: str
    description: str
    read_only: bool
    destructive: bool = False

    @property
    def mcp_name(self):
        return "calculix_{}".format(self.name.replace(".", "_"))

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
    MethodSpec("system.ping", "Return solver executable, version and running jobs.", True),
    MethodSpec("system.capabilities", "Return the CalculiX batch integration contract.", True),
    MethodSpec("session.observe", "Observe job state and reconcile completed external work.", True),
    MethodSpec("session.acquire", "Acquire the single-writer solver-job lease.", False),
    MethodSpec("session.release", "Release the solver-job lease.", False),
    MethodSpec("session.history", "Return recent atomic job action records.", True),
    MethodSpec("jobs.start", "Start ccx from an allowed .inp deck and capture its exact log.", False),
    MethodSpec("jobs.status", "Return one job, output files and solver error lines.", True),
    MethodSpec("jobs.list", "List every job known to this service.", True),
    MethodSpec("jobs.cancel", "Terminate an explicitly named running solver job.", False, destructive=True),
)

SPEC_BY_NAME = {spec.name: spec for spec in METHOD_SPECS}


def _object(properties=None, required=None):
    return {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False}


ACTOR = {"type": "string", "minLength": 1}
REVISION = {"type": "integer", "minimum": 0}
MUTATION = {"actor": ACTOR, "expected_revision": REVISION}
SCHEMAS = {
    "system.ping": _object(), "system.capabilities": _object(), "session.observe": _object(),
    "session.acquire": _object({**MUTATION, "ttl_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 3600}}, ["actor", "expected_revision"]),
    "session.release": _object({"actor": ACTOR}, ["actor"]),
    "session.history": _object({"limit": {"type": "integer", "minimum": 1, "maximum": 200}}),
    "jobs.start": _object({**MUTATION, "deck_path": {"type": "string", "minLength": 1}}, ["actor", "expected_revision", "deck_path"]),
    "jobs.status": _object({"job_id": {"type": "string", "minLength": 1}}, ["job_id"]),
    "jobs.list": _object(),
    "jobs.cancel": _object({**MUTATION, "job_id": {"type": "string", "minLength": 1}}, ["actor", "expected_revision", "job_id"]),
}
