import unittest

from bridge.freecad_bridge.console_capture import ConsoleCapture


class ConsoleCaptureTests(unittest.TestCase):
    def test_returns_only_text_added_during_operation(self):
        values = iter(["old line\n", "old line\nnew warning\nnew error\n"])
        result = ConsoleCapture(lambda: next(values)).finish()
        self.assertTrue(result["capture_available"])
        self.assertEqual(result["text"], "new warning\nnew error\n")
        self.assertFalse(result["history_reset"])

    def test_reports_history_reset_instead_of_claiming_a_clean_delta(self):
        values = iter(["old line\n", "replacement text\n"])
        result = ConsoleCapture(lambda: next(values)).finish()
        self.assertEqual(result["text"], "replacement text\n")
        self.assertTrue(result["history_reset"])

    def test_limits_large_console_payloads_from_the_tail(self):
        values = iter(["", "0123456789"])
        result = ConsoleCapture(lambda: next(values), limit=4).finish()
        self.assertEqual(result["text"], "6789")
        self.assertTrue(result["truncated"])

    def test_declares_missing_report_view(self):
        result = ConsoleCapture(lambda: None).finish()
        self.assertFalse(result["capture_available"])
        self.assertEqual(result["reason"], "report_view_unavailable")


if __name__ == "__main__":
    unittest.main()
