import unittest
from pathlib import Path

from tools.inspect_deck import constrained_nodes, load_summary, parse


REPO_ROOT = Path(__file__).resolve().parents[2]


class CalculiXInspectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes, cls.nsets, cls.cload, cls.boundary = parse(
            REPO_ROOT / "calculix" / "cantilever.inp"
        )

    def test_cload_node_set_is_expanded_into_resultant(self):
        nodes, resultant, unresolved = load_summary(self.nsets, self.cload)
        self.assertEqual(nodes, {2, 3, 6, 7})
        self.assertEqual(resultant, {1: 1000.0, 2: 0.0, 3: 0.0})
        self.assertEqual(unresolved, [])

    def test_only_boundary_targets_are_reported_as_constrained(self):
        nodes, unresolved = constrained_nodes(self.nsets, self.boundary)
        self.assertEqual(nodes, {1, 4, 5, 8})
        self.assertEqual(unresolved, [])


if __name__ == "__main__":
    unittest.main()
