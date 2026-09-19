"""CGX session API that never hides its GUI-fallback status."""

import os

from integrations.common.errors import BridgeError, INVALID_PARAMS, METHOD_NOT_FOUND
from integrations.common.session import SessionCoordinator
from . import BRIDGE_VERSION, PROTOCOL_VERSION
from .contract import METHOD_SPECS, SPEC_BY_NAME


class CGXAPI:
    def __init__(self, driver, path_policy, socket_path):
        self.driver = driver
        self.path_policy = path_policy
        self.socket_path = socket_path
        self.session = SessionCoordinator("cgx")

    def dispatch(self, method, params):
        if method not in SPEC_BY_NAME:
            raise BridgeError(METHOD_NOT_FOUND, "Unknown CGX method", {"method": method})
        return getattr(self, "_" + method.replace(".", "_"))(params)

    def _system_ping(self, params):
        self._empty(params)
        return {
            "bridge_version": BRIDGE_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "interaction_level": "gui-fallback",
            "native_command_channel": False,
            "socket": self.socket_path,
            "pid": os.getpid(),
            "process": self.driver.status(capture=False),
            "session": self.session.snapshot(),
        }

    def _system_capabilities(self, params):
        self._empty(params)
        return {
            "application": "cgx",
            "interaction_level": "gui-fallback",
            "native_command_channel": False,
            "methods": [spec.as_dict() for spec in METHOD_SPECS],
        }

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

    def _process_start(self, params):
        self._mutation_fields(params, "input_path")
        input_path = self.path_policy.resolve_read(params["input_path"])
        deck = self.path_policy.resolve_read(params["deck_path"]) if params.get("deck_path") else None
        return self._mutate(params, "process.start", lambda: self.driver.start(input_path, deck))

    def _process_attach(self, params):
        self._mutation_fields(params, "pid", "window_id")
        return self._mutate(params, "process.attach", lambda: self.driver.attach(params["pid"], params["window_id"]))

    def _process_status(self, params):
        self._empty(params)
        return {"session": self.session.observe(self._state()), "process": self.driver.status()}

    def _process_stop(self, params):
        self._mutation_fields(params)
        return self._mutate(params, "process.stop", self.driver.stop)

    def _command_execute(self, params):
        self._mutation_fields(params, "command")
        settle = params.get("settle_seconds", 0.75)
        return self._mutate(params, "command.execute", lambda: self.driver.execute(params["command"], settle))

    def _gui_save_screenshot(self, params):
        self._mutation_fields(params, "path")
        path = self.path_policy.resolve_write(params["path"])
        return self._mutate(params, "gui.save_screenshot", lambda: {"artifact": self.driver.capture(path)})

    def _mutate(self, params, operation, action):
        arguments = {key: value for key, value in params.items() if key not in ("actor", "expected_revision")}
        return self.session.run_action(
            params["actor"], params["expected_revision"], operation, arguments, self._state, action
        )

    def _state(self):
        return self.driver.status(capture=True)

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
