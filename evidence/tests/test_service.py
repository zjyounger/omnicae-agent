import json
import tempfile
import unittest
from pathlib import Path

from evidence.r2r.build_calculix_corpus import MANUALS, build_manual
from evidence.service import (
    EvidenceService,
    EvidenceSourceNotFound,
    prepare_retrieval_result,
)


class EvidenceServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temporary = tempfile.TemporaryDirectory()
        data = Path(cls._temporary.name)
        _, ccx_map = build_manual("ccx", MANUALS["ccx"])
        _, cgx_map = build_manual("cgx", MANUALS["cgx"])
        (data / "document_map.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "manuals": {"ccx": ccx_map, "cgx": cgx_map},
                }
            ),
            encoding="utf-8",
        )
        cls.service = EvidenceService(data=data)

    @classmethod
    def tearDownClass(cls):
        cls._temporary.cleanup()

    def test_exact_lookup_returns_authoritative_path(self):
        result = self.service.lookup_exact("calculix-ccx", "CLOAD")
        self.assertEqual(result["matches"][0]["source_file"], "node242.html")
        self.assertTrue(result["matches"][0]["source_path"].endswith("node242.html"))

    def test_document_map_keeps_navigation_separate_from_references(self):
        result = self.service.get_document_map("calculix-ccx", "node242.html")
        references = {item["source_file"] for item in result["references"]}
        self.assertIn("node353.html", references)
        self.assertNotIn(result["previous_source"], references)
        self.assertNotIn(result["next_source"], references)

    def test_open_source_reads_complete_authoritative_page(self):
        result = self.service.open_source("calculix-ccx", "node242.html")
        text = " ".join(block["text"] for block in result["blocks"]).casefold()
        self.assertIn("concentrated forces", text)

    def test_unknown_application_is_rejected(self):
        with self.assertRaises(EvidenceSourceNotFound):
            self.service.lookup_exact("unknown", "CLOAD")

    def test_mcp_retrieval_does_not_preexpand_cross_references(self):
        result = {
            "information_needs": [
                {
                    "routes": {
                        "api_catalogue": [
                            {
                                "manual": "cgx",
                                "source_file": "node95.html",
                                "summary": "x" * 500,
                            }
                        ],
                        "semantic": [
                            {
                                "manual": "cgx",
                                "source_file": "node251.html",
                                "excerpt": "y" * 500,
                            }
                        ],
                    },
                    "explicit_references": [{"source_file": "node1.html"}],
                }
            ]
        }
        need = prepare_retrieval_result(result)["information_needs"][0]
        self.assertNotIn("explicit_references", need)
        self.assertEqual(len(need["routes"]["api_catalogue"][0]["summary"]), 400)
        self.assertEqual(
            need["routes"]["api_catalogue"][0]["open_arguments"]["application"],
            "calculix-cgx",
        )


if __name__ == "__main__":
    unittest.main()
