import unittest

from integrations.cgx.driver import CGXDriver
from integrations.common.errors import BridgeError, INVALID_PARAMS


class CGXCommandValidationTest(unittest.TestCase):
    def test_allows_single_safe_command(self):
        CGXDriver._validate_command("view front")

    def test_rejects_shell_and_file_commands(self):
        for command in ("sys rm file", "read model.fbd", "quit", "unknown argument"):
            with self.subTest(command=command), self.assertRaises(BridgeError) as raised:
                CGXDriver._validate_command(command)
            self.assertEqual(raised.exception.code, INVALID_PARAMS)

    def test_rejects_multiline_input(self):
        with self.assertRaises(BridgeError):
            CGXDriver._validate_command("view front\nsys command")


if __name__ == "__main__":
    unittest.main()
