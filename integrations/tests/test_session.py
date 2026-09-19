import unittest

from integrations.common.errors import BridgeError, LEASE_CONFLICT, STATE_CONFLICT
from integrations.common.session import SessionCoordinator


class SessionCoordinatorTest(unittest.TestCase):
    def setUp(self):
        self.live = {"value": 1}
        self.session = SessionCoordinator("test", history_limit=3)

    def observe_live(self):
        return dict(self.live)

    def test_external_change_advances_revision_and_invalidates_stale_action(self):
        first = self.session.observe(self.observe_live())
        self.session.acquire("agent", first["revision"])
        self.live["value"] = 2

        with self.assertRaises(BridgeError) as raised:
            self.session.run_action(
                "agent", first["revision"], "change", {}, self.observe_live, lambda: None
            )

        self.assertEqual(raised.exception.code, STATE_CONFLICT)
        self.assertEqual(self.session.revision, 1)

    def test_only_lease_owner_can_mutate_or_release(self):
        observed = self.session.observe(self.observe_live())
        self.session.acquire("human", observed["revision"])

        with self.assertRaises(BridgeError) as raised:
            self.session.acquire("agent", observed["revision"])
        self.assertEqual(raised.exception.code, LEASE_CONFLICT)

        with self.assertRaises(BridgeError) as raised:
            self.session.release("agent")
        self.assertEqual(raised.exception.code, LEASE_CONFLICT)

    def test_atomic_action_records_before_after_and_result(self):
        observed = self.session.observe(self.observe_live())
        self.session.acquire("agent", observed["revision"])

        def change():
            self.live["value"] = 2
            return {"acknowledged": True}

        step = self.session.run_action(
            "agent", observed["revision"], "change", {"value": 2}, self.observe_live, change
        )

        self.assertEqual(step["before"], {"value": 1})
        self.assertEqual(step["after"], {"value": 2})
        self.assertEqual(step["result"], {"acknowledged": True})
        self.assertEqual(step["revision_after"], 1)
        self.assertEqual(self.session.recent_history(), [step])


if __name__ == "__main__":
    unittest.main()
