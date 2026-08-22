"""One-process CGX driver with explicit, evidence-checked GUI fallback."""

import hashlib
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from integrations.common.errors import BridgeError, APPLICATION_UNAVAILABLE, INVALID_PARAMS


SAFE_COMMANDS = {
    "anim", "capt", "comp", "cont", "ds", "enq", "frame", "graph", "hcpy",
    "max", "min", "minus", "mm", "movi", "plot", "plus", "prnt", "rot",
    "scal", "send", "seta", "setc", "seto", "setr", "steps", "ulin", "view",
}
DENIED_COMMANDS = {"sys", "quit", "exit", "zap", "del", "read", "break", "stop"}


class CGXDriver:
    def __init__(self, executable="cgx", evidence_directory="/tmp"):
        self.executable = shutil.which(executable)
        self.xdotool = shutil.which("xdotool")
        self.capture_tool = shutil.which("import")
        self.evidence_directory = Path(evidence_directory)
        self.pid = None
        self.window_id = None
        self.process = None
        self.log_path = None
        self.log_offset = 0

    @property
    def fallback_available(self):
        return bool(self.xdotool and self.capture_tool and os.environ.get("DISPLAY"))

    def start(self, input_path, deck_path=None):
        if not self.executable:
            raise BridgeError(APPLICATION_UNAVAILABLE, "cgx executable was not found")
        if self.is_running():
            raise BridgeError(INVALID_PARAMS, "A CGX process is already attached", self.status(capture=False))
        input_path = Path(input_path)
        if input_path.suffix.lower() == ".frd":
            command = [self.executable, "-v", str(input_path)]
            if deck_path:
                command.append(str(deck_path))
        elif input_path.suffix.lower() == ".inp":
            command = [self.executable, "-c", str(input_path)]
        elif input_path.suffix.lower() in (".fbd", ".fbl"):
            command = [self.executable, "-b", str(input_path)]
        else:
            raise BridgeError(INVALID_PARAMS, "CGX input must be .frd, .inp, .fbd or .fbl")
        self.log_path = input_path.parent / (input_path.stem + ".cgx-bridge.log")
        log = open(self.log_path, "wb")
        self.process = subprocess.Popen(
            command,
            cwd=str(input_path.parent),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.process._omnicae_log = log
        self.pid = self.process.pid
        self.window_id = self._wait_for_window(self.pid)
        self.log_offset = 0
        return {"command": command, "status": self.status()}

    def attach(self, pid, window_id):
        pid = int(pid)
        self._check_pid(pid)
        actual_pid = self._window_pid(window_id)
        if actual_pid is not None and actual_pid != pid:
            raise BridgeError(
                INVALID_PARAMS,
                "Window does not belong to the requested PID",
                {"pid": pid, "window_pid": actual_pid, "window_id": window_id},
            )
        self.pid = pid
        self.window_id = str(window_id)
        self.process = None
        self.log_path = None
        self.log_offset = 0
        return self.status()

    def stop(self):
        if not self.is_running():
            return {"stopped": True, "already_stopped": True}
        os.kill(self.pid, signal.SIGTERM)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and self.is_running():
            time.sleep(0.1)
        stopped = not self.is_running()
        return {"stopped": stopped, "pid": self.pid}

    def execute(self, command, settle_seconds=0.75):
        self._require_fallback()
        self._validate_command(command)
        if not self.is_running():
            raise BridgeError(APPLICATION_UNAVAILABLE, "Attached CGX process is not running")
        before = self.capture()
        log_before = self._read_log_increment()
        self._run_xdotool(["windowactivate", "--sync", self.window_id])
        self._run_xdotool(["key", "--window", self.window_id, "--repeat", "256", "--delay", "1", "BackSpace"])
        self._run_xdotool(["type", "--window", self.window_id, "--delay", "20", command])
        self._run_xdotool(["key", "--window", self.window_id, "Return"])
        time.sleep(max(0.1, min(float(settle_seconds), 10.0)))
        after = self.capture()
        log_delta = self._read_log_increment()
        running = self.is_running()
        lower_log = log_delta.lower()
        rejected = "not known" in lower_log or "error" in lower_log
        echoed = command.lower() in lower_log
        if not running or rejected:
            acknowledgement = "failed"
        elif echoed:
            acknowledgement = "console"
        elif before["sha256"] != after["sha256"]:
            acknowledgement = "visual-only"
        else:
            acknowledgement = "uncertain"
        return {
            "command": command,
            "transport": "xdotool",
            "acknowledgement": acknowledgement,
            "process_running": running,
            "before_screenshot": before,
            "after_screenshot": after,
            "console_before": log_before,
            "console_delta": log_delta,
        }

    def status(self, capture=True):
        state = {
            "pid": self.pid,
            "running": self.is_running(),
            "window_id": self.window_id,
            "window_title": self._window_title() if self.window_id else None,
            "interaction_level": "gui-fallback",
            "fallback_available": self.fallback_available,
            "log_path": str(self.log_path) if self.log_path else None,
            "state_confidence": "visual-and-process-only",
        }
        if capture and state["running"] and self.fallback_available:
            state["screenshot"] = self.capture()
        return state

    def capture(self, path=None):
        self._require_fallback()
        if not self.window_id:
            raise BridgeError(APPLICATION_UNAVAILABLE, "No CGX window is attached")
        if path is None:
            self.evidence_directory.mkdir(parents=True, exist_ok=True)
            path = self.evidence_directory / "omnicae-cgx-state-{}.png".format(self.pid)
        else:
            path = Path(path)
        subprocess.run([self.capture_tool, "-window", self.window_id, str(path)], check=True)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}

    def is_running(self):
        if self.pid is None:
            return False
        try:
            os.kill(self.pid, 0)
        except OSError:
            return False
        return True

    def close(self):
        if self.process is not None:
            log = getattr(self.process, "_omnicae_log", None)
            if log and not log.closed:
                log.close()

    def _wait_for_window(self, pid):
        self._require_fallback()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            completed = subprocess.run(
                [self.xdotool, "search", "--pid", str(pid), "--onlyvisible"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            windows = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
            if windows:
                return windows[-1]
            if not self.is_running():
                break
            time.sleep(0.1)
        raise BridgeError(APPLICATION_UNAVAILABLE, "CGX window did not appear", {"pid": pid})

    def _window_pid(self, window_id):
        xprop = shutil.which("xprop")
        if not xprop:
            return None
        completed = subprocess.run(
            [xprop, "-id", str(window_id), "_NET_WM_PID"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        fields = completed.stdout.split("=")
        try:
            return int(fields[-1].strip())
        except (ValueError, IndexError):
            return None

    def _window_title(self):
        completed = subprocess.run(
            [self.xdotool, "getwindowname", self.window_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return completed.stdout.strip() or None

    def _read_log_increment(self):
        if not self.log_path or not Path(self.log_path).is_file():
            return ""
        with open(self.log_path, "rb") as stream:
            stream.seek(self.log_offset)
            data = stream.read()
            self.log_offset = stream.tell()
        return data.decode("utf-8", errors="replace")[-20000:]

    def _run_xdotool(self, arguments):
        subprocess.run([self.xdotool] + arguments, check=True, stdout=subprocess.DEVNULL)

    def _require_fallback(self):
        if not self.fallback_available:
            raise BridgeError(
                APPLICATION_UNAVAILABLE,
                "CGX GUI fallback requires DISPLAY, xdotool and ImageMagick import",
            )

    @staticmethod
    def _validate_command(command):
        if not isinstance(command, str) or not command.strip() or "\n" in command or "\r" in command:
            raise BridgeError(INVALID_PARAMS, "CGX command must be one non-empty line")
        keyword = command.split()[0].lower()
        if keyword in DENIED_COMMANDS or keyword not in SAFE_COMMANDS:
            raise BridgeError(
                INVALID_PARAMS,
                "CGX command is not allowlisted for GUI fallback",
                {"keyword": keyword, "allowed": sorted(SAFE_COMMANDS)},
            )

    @staticmethod
    def _check_pid(pid):
        try:
            os.kill(pid, 0)
        except OSError as exc:
            raise BridgeError(INVALID_PARAMS, "PID is not running", {"pid": pid}) from exc
