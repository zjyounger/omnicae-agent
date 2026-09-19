import tempfile
import unittest
from pathlib import Path

from integrations.calculix.runner import CalculiXRunner


class CalculiXRunnerOutputTests(unittest.TestCase):
    def test_stale_outputs_are_not_attributed_to_a_new_job(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = directory / "case.frd"
            output.write_text("old result", encoding="utf-8")
            baseline = CalculiXRunner._snapshot_outputs(directory, "case")
            job = {
                "working_directory": str(directory),
                "job_name": "case",
                "_output_baseline": baseline,
            }
            self.assertEqual(CalculiXRunner._outputs(job), [])

            output.write_text("new result", encoding="utf-8")
            current = CalculiXRunner._outputs(job)
            self.assertEqual(len(current), 1)
            self.assertEqual(current[0]["path"], str(output))

    def test_new_output_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            job = {
                "working_directory": str(directory),
                "job_name": "case",
                "_output_baseline": {},
            }
            output = directory / "case.dat"
            output.write_text("current result", encoding="utf-8")
            self.assertEqual(
                [item["path"] for item in CalculiXRunner._outputs(job)],
                [str(output)],
            )


if __name__ == "__main__":
    unittest.main()
