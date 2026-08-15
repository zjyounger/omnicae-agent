"""Dependency-free external client for the FreeCAD bridge."""

import json
import os
import socket


def default_socket_path():
    configured = os.environ.get("CAE_BRIDGE_SOCKET")
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return os.path.join(runtime_dir, "opensource-cae-freecad.sock")
    return "/tmp/opensource-cae-freecad-{}.sock".format(os.getuid())


class BridgeClientError(Exception):
    pass


class BridgeRemoteError(BridgeClientError):
    def __init__(self, code, message, data=None):
        super().__init__("{}: {}".format(code, message))
        self.code = code
        self.message = message
        self.data = data


class BridgeClient:
    # GUI calls run on the FreeCAD main thread and gui.fit_all alone has been
    # measured at 11 s on a small model, so the default has to clear that.
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, socket_path=None, timeout=DEFAULT_TIMEOUT):
        self.socket_path = socket_path or default_socket_path()
        self.timeout = float(timeout)
        self._socket = None
        self._buffer = bytearray()
        self._request_id = 0

    def connect(self):
        if self._socket is not None:
            return self
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(self.socket_path)
        except Exception:
            sock.close()
            raise
        self._socket = sock
        return self

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None
            self._buffer.clear()

    def call(self, method, params=None):
        if self._socket is None:
            self.connect()
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        payload = (json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        self._socket.sendall(payload)
        response = self._read_response()
        if response.get("id") != self._request_id:
            raise BridgeClientError("Mismatched response id")
        if "error" in response:
            error = response["error"]
            raise BridgeRemoteError(error["code"], error["message"], error.get("data"))
        if "result" not in response:
            raise BridgeClientError("Response has neither result nor error")
        return response["result"]

    def _read_response(self):
        while b"\n" not in self._buffer:
            chunk = self._socket.recv(65536)
            if not chunk:
                raise BridgeClientError("Bridge closed the connection")
            self._buffer.extend(chunk)
        raw, remainder = self._buffer.split(b"\n", 1)
        self._buffer[:] = remainder
        try:
            response = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise BridgeClientError("Invalid JSON response: {}".format(exc)) from exc
        if not isinstance(response, dict) or response.get("jsonrpc") != "2.0":
            raise BridgeClientError("Invalid JSON-RPC response")
        return response

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
