"""Shared local-bridge primitives; no application-specific behaviour."""

from .errors import BridgeError
from .session import SessionCoordinator

__all__ = ["BridgeError", "SessionCoordinator"]
