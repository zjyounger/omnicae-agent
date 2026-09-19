"""Dependency-free client for local application Bridges."""

import json
import socket


class LocalBridgeError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__("{}: {}".format(code, message))
        self.code = code
        self.message = message
        self.data = data


class LocalBridgeClient:
    def __init__(self, socket_path, timeout=120.0):
        self.socket_path = socket_path
        self.timeout = float(timeout)
        self._request_id = 0

    def call(self, method, params=None):
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        payload = (json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)
            sock.sendall(payload)
            buffer = bytearray()
            while b"\n" not in buffer:
                chunk = sock.recv(65536)
                if not chunk:
                    raise RuntimeError("Bridge closed connection without a response")
                buffer.extend(chunk)
        response = json.loads(buffer.split(b"\n", 1)[0].decode("utf-8"))
        if "error" in response:
            error = response["error"]
            raise LocalBridgeError(error["code"], error["message"], error.get("data"))
        return response["result"]
