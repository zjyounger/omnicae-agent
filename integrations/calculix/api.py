"""CalculiX batch job API with cooperative session semantics."""

import os
import subprocess

from integrations.common.errors import BridgeError, INVALID_PARAMS, METHOD_NOT_FOUND
from integrations.common.session import SessionCoordinator
from . import BRIDGE_VERSION, PROTOCOL_VERSION
from .contract import METHOD_SPECS, SPEC_BY_NAME


class CalculiXAPI:
    def __init__(self, runner, path_policy, socket_path):
        self.runner = runner
        self.path_policy = path_policy
        self.socket_path = socket_path
        self.session = SessionCoordinator("calculix")

    def dispatch(self, method, params):
        if method not in SPEC_BY_NAME:
            raise BridgeError(METHOD_NOT_FOUND, "Unknown CalculiX method", {"method": method})
        return getattr(self, "_" + method.replace(".", "_"))(params)

    def _system_ping(self, params):
        self._empty(params)
        return {
            "bridge_version": BRIDGE_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "interaction_level": "batch",
            "solver": self.runner.solver_path,
            "solver_version": self._solver_version(),
            "socket": self.socket_path,
            "pid": os.getpid(),
            "jobs": self.runner.list(),
            "session": self.session.snapshot(),
        }

    def _system_capabilities(self, params):
        self._empty(params)
        return {"application": "calculix", "interaction_level": "batch", "methods": [s.as_dict() for s in METHOD_SPECS]}

    def _session_observe(self, params):
        self._empty(params)
        return self.session.observe(self._state())

    def _session_acquire(self, params):
        self._require(params, "actor", "expected_revision")
        return self.session.acquire(params["actor"], params["expected_revision"], params.get("ttl_seconds", 300))

    def _session_release(self, params):
        self._require(params, "actor")
        return self.session.release(params["actor"])

    def _session_history(self, params):
        return {"steps": self.session.recent_history(params.get("limit", 20))}

    def _jobs_start(self, params):
        self._mutation_fields(params, "deck_path")
        deck = self.path_policy.resolve_read(params["deck_path"])
        if deck.suffix.lower() != ".inp":
            raise BridgeError(INVALID_PARAMS, "CalculiX deck must use .inp extension")
        return self._mutate(params, "jobs.start", lambda: self.runner.start(deck))

    def _jobs_status(self, params):
        self._require(params, "job_id")
        if params["job_id"] not in self.runner.jobs:
            raise BridgeError(INVALID_PARAMS, "Unknown job_id")
        return {"session": self.session.observe(self._state()), "job": self.runner.describe(params["job_id"])}

    def _jobs_list(self, params):
        self._empty(params)
        return {"session": self.session.observe(self._state()), "jobs": self.runner.list()}

    def _jobs_cancel(self, params):
        self._mutation_fields(params, "job_id")
        if params["job_id"] not in self.runner.jobs:
            raise BridgeError(INVALID_PARAMS, "Unknown job_id")
        return self._mutate(params, "jobs.cancel", lambda: self.runner.cancel(params["job_id"]))

    def _mutate(self, params, operation, action):
        arguments = {key: value for key, value in params.items() if key not in ("actor", "expected_revision")}
        return self.session.run_action(
            params["actor"], params["expected_revision"], operation, arguments, self._state, action
        )

    def _state(self):
        jobs = []
        for job in self.runner.list():
            jobs.append(
                {
                    "job_id": job["job_id"],
                    "state": job["state"],
                    "return_code": job["return_code"],
                    "outputs": [(item["path"], item["bytes"], item["sha256"]) for item in job["outputs"]],
                }
            )
        return {"jobs": jobs}

    def _solver_version(self):
        completed = subprocess.run(
            [self.runner.solver_path, "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
        return completed.stdout.strip().splitlines()[0:3]

    @staticmethod
    def _empty(params):
        if params:
            raise BridgeError(INVALID_PARAMS, "This method takes no parameters")

    @staticmethod
    def _require(params, *names):
        missing = [name for name in names if name not in params]
        if missing:
            raise BridgeError(INVALID_PARAMS, "Missing required parameters", {"missing": missing})

    def _mutation_fields(self, params, *extra):
        self._require(params, "actor", "expected_revision", *extra)
