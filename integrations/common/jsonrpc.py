"""Queued Unix-socket JSON-RPC runtime for main-thread-owned applications."""

import json
import os
import queue
import socket
import socketserver
import threading
import time

from .errors import (
    BridgeError,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    PARSE_ERROR,
)


MAX_MESSAGE_BYTES = 1024 * 1024


class _Pending:
    def __init__(self, request):
        self.request = request
        self.event = threading.Event()
        self.response = None


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            raw = self.rfile.readline(MAX_MESSAGE_BYTES + 1)
            if not raw:
                return
            if len(raw) > MAX_MESSAGE_BYTES:
                response = _error(None, INVALID_REQUEST, "Message exceeds 1 MiB")
            else:
                response = self.server.runtime.submit(raw)
            if response is not None:
                payload = (json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()


class _UnixServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False


class QueuedJsonRpcRuntime:
    def __init__(self, socket_path, dispatch, timeout=120.0):
        self.socket_path = os.path.abspath(os.path.expanduser(socket_path))
        self.dispatch = dispatch
        self.timeout = float(timeout)
        self.pending = queue.Queue()
        self.running = False
        self._server = None
        self._thread = None

    def start(self):
        if self.running:
            return
        parent = os.path.dirname(self.socket_path)
        os.makedirs(parent, exist_ok=True)
        if os.path.exists(self.socket_path):
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                probe.settimeout(0.15)
                probe.connect(self.socket_path)
            except OSError:
                os.unlink(self.socket_path)
            else:
                raise RuntimeError("Bridge socket is already in use: {}".format(self.socket_path))
            finally:
                probe.close()
        self._server = _UnixServer(self.socket_path, _Handler)
        self._server.runtime = self
        os.chmod(self.socket_path, 0o600)
        self.running = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self._server.shutdown()
        self._server.server_close()
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

    def submit(self, raw):
        request_id = None
        try:
            try:
                request = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                raise BridgeError(PARSE_ERROR, "Parse error", {"detail": str(exc)})
            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                raise BridgeError(INVALID_REQUEST, "Request must be a JSON-RPC 2.0 object")
            request_id = request.get("id")
            if not isinstance(request.get("method"), str) or not request["method"]:
                raise BridgeError(INVALID_REQUEST, "method must be a non-empty string")
            if not isinstance(request.get("params", {}), dict):
                raise BridgeError(INVALID_PARAMS, "params must be an object")
            pending = _Pending(request)
            self.pending.put(pending)
            if not pending.event.wait(self.timeout):
                return _error(request_id, 50401, "Bridge main thread did not respond")
            return pending.response
        except BridgeError as exc:
            return _error(request_id, exc.code, exc.message, exc.data)

    def process_pending(self, maximum=20):
        processed = 0
        while processed < maximum:
            try:
                pending = self.pending.get_nowait()
            except queue.Empty:
                break
            request = pending.request
            request_id = request.get("id")
            try:
                result = self.dispatch(request["method"], request.get("params", {}))
                pending.response = {"jsonrpc": "2.0", "id": request_id, "result": result}
            except BridgeError as exc:
                pending.response = _error(request_id, exc.code, exc.message, exc.data)
            except Exception as exc:
                pending.response = _error(
                    request_id,
                    INTERNAL_ERROR,
                    "Internal error",
                    {"type": type(exc).__name__, "message": str(exc)},
                )
            pending.event.set()
            processed += 1
        return processed

    def run(self, pump=None, keep_running=None, interval=0.05):
        self.start()
        try:
            while self.running and (keep_running is None or keep_running()):
                self.process_pending()
                if pump is not None:
                    pump(interval)
                else:
                    time.sleep(interval)
        finally:
            self.stop()


def _error(request_id, code, message, data=None):
    error = {"code": int(code), "message": str(message)}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}
