"""Structured errors shared by local application bridges."""


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
STATE_CONFLICT = 40901
LEASE_CONFLICT = 40902
APPLICATION_UNAVAILABLE = 50301
