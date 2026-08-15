"""Structured errors used by the FreeCAD bridge."""


class BridgeError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = int(code)
        self.message = str(message)
        self.data = data


PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
APPLICATION_ERROR = -32000


def invalid_params(message, field=None, value=None):
    data = {}
    if field is not None:
        data["field"] = field
    if value is not None:
        data["value"] = value
    return BridgeError(INVALID_PARAMS, message, data or None)
