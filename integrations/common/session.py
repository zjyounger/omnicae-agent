"""Single-writer coordination and evidence-bearing atomic actions."""

import json
import threading
import time
import uuid
from datetime import datetime, timezone

from .errors import BridgeError, LEASE_CONFLICT, STATE_CONFLICT


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def stable_fingerprint(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SessionCoordinator:
    def __init__(self, application, history_limit=200):
        self.application = application
        self.revision = 0
        self.owner = None
        self.lease_until = 0.0
        self.last_fingerprint = None
        self.last_state = None
        self.history_limit = int(history_limit)
        self.history = []
        self._lock = threading.RLock()

    def snapshot(self):
        with self._lock:
            self._expire_lease()
            return {
                "application": self.application,
                "revision": self.revision,
                "owner": self.owner,
                "lease_expires_at_monotonic": self.lease_until if self.owner else None,
                "last_state": self.last_state,
                "history_size": len(self.history),
            }

    def observe(self, state):
        fingerprint = stable_fingerprint(state)
        with self._lock:
            external_change = False
            if self.last_fingerprint is None:
                self.last_fingerprint = fingerprint
                self.last_state = state
            elif fingerprint != self.last_fingerprint:
                self.revision += 1
                self.last_fingerprint = fingerprint
                self.last_state = state
                external_change = True
            return {
                **self.snapshot(),
                "state": state,
                "external_change": external_change,
            }

    def acquire(self, actor, expected_revision=None, ttl_seconds=300):
        self._validate_actor(actor)
        ttl_seconds = float(ttl_seconds)
        if ttl_seconds <= 0 or ttl_seconds > 3600:
            raise BridgeError(LEASE_CONFLICT, "Lease TTL must be in (0, 3600] seconds")
        with self._lock:
            self._expire_lease()
            self._check_revision(expected_revision)
            if self.owner not in (None, actor):
                raise BridgeError(
                    LEASE_CONFLICT,
                    "Application write lease is held by another actor",
                    {"owner": self.owner, "revision": self.revision},
                )
            self.owner = actor
            self.lease_until = time.monotonic() + ttl_seconds
            return self.snapshot()

    def release(self, actor):
        self._validate_actor(actor)
        with self._lock:
            self._expire_lease()
            if self.owner not in (None, actor):
                raise BridgeError(
                    LEASE_CONFLICT,
                    "Only the current lease owner can release it",
                    {"owner": self.owner},
                )
            self.owner = None
            self.lease_until = 0.0
            return self.snapshot()

    def run_action(self, actor, expected_revision, operation, arguments, observe, action):
        self._validate_actor(actor)
        with self._lock:
            self._expire_lease()
            if self.owner != actor:
                raise BridgeError(
                    LEASE_CONFLICT,
                    "A write lease is required for this action",
                    {"owner": self.owner, "actor": actor, "revision": self.revision},
                )
            self._check_revision(expected_revision)
            before = observe()
            before_fingerprint = stable_fingerprint(before)
            if self.last_fingerprint is not None and before_fingerprint != self.last_fingerprint:
                self.revision += 1
                self.last_fingerprint = before_fingerprint
                self.last_state = before
                raise BridgeError(
                    STATE_CONFLICT,
                    "Application state changed since the last observation",
                    {"revision": self.revision, "state": before},
                )

            action_id = str(uuid.uuid4())
            revision_before = self.revision
            started_at = _utc_now()
            status = "succeeded"
            result = None
            error = None
            try:
                result = action()
            except Exception as exc:
                status = "failed"
                error = {"type": type(exc).__name__, "message": str(exc)}
            after = observe()
            self.revision += 1
            self.last_fingerprint = stable_fingerprint(after)
            self.last_state = after
            self.lease_until = time.monotonic() + 300.0
            record = {
                "action_id": action_id,
                "application": self.application,
                "actor": actor,
                "operation": operation,
                "arguments": arguments,
                "revision_before": revision_before,
                "revision_after": self.revision,
                "before": before,
                "after": after,
                "status": status,
                "result": result,
                "error": error,
                "started_at": started_at,
                "finished_at": _utc_now(),
            }
            self.history.append(record)
            del self.history[:-self.history_limit]
            if error:
                raise BridgeError(50001, "Application action failed", {"step": record})
            return record

    def recent_history(self, limit=20):
        limit = max(1, min(int(limit), self.history_limit))
        with self._lock:
            return list(self.history[-limit:])

    def _check_revision(self, expected_revision):
        if expected_revision is None or int(expected_revision) != self.revision:
            raise BridgeError(
                STATE_CONFLICT,
                "Expected revision does not match live session",
                {"expected_revision": expected_revision, "revision": self.revision},
            )

    def _expire_lease(self):
        if self.owner is not None and time.monotonic() >= self.lease_until:
            self.owner = None
            self.lease_until = 0.0

    @staticmethod
    def _validate_actor(actor):
        if not isinstance(actor, str) or not actor.strip():
            raise BridgeError(LEASE_CONFLICT, "Actor must be a non-empty string")
