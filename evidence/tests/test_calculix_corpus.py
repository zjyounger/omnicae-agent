import unittest

from evidence.r2r.bootstrap_calculix import compose_command
from evidence.r2r.build_calculix_corpus import MANUALS, api_catalog, build_manual
from evidence.r2r.evaluate_calculix import requested_kind, source_rank
from evidence.r2r.evaluate_context_scope import context_scopes, marker_coverage
from evidence.r2r.evaluate_multi_source import need_covered
from evidence.r2r.evaluate_visual_retrieval import lexical_figure_rank
from evidence.r2r.navigate_calculix import (
    child_entries,
    discover_entries,
    exact_entries,
    reference_entries,
    source_blocks,
)


class CalculixCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ccx_chunks, cls.ccx_map = build_manual("ccx", MANUALS["ccx"])
        cls.cgx_chunks, cls.cgx_map = build_manual("cgx", MANUALS["cgx"])

    def test_complete_manual_page_counts(self):
        self.assertEqual(len(self.ccx_map["pages"]), 534)
        self.assertEqual(len(self.cgx_map["pages"]), 286)

    def test_cload_location_and_hierarchy_are_preserved(self):
        chunks = [
            chunk
            for chunk in self.ccx_chunks
            if chunk["source_file"] == "node242.html"
        ]
        self.assertTrue(chunks)
        self.assertEqual(chunks[0]["source_anchor"], "cload")
        self.assertEqual(chunks[0]["section_path"][-2:], ["Input deck format", "*CLOAD"])
        self.assertEqual(chunks[0]["parent_source"], "node223.html")
        self.assertIsNotNone(chunks[0]["previous_source"])
        self.assertIsNotNone(chunks[0]["next_source"])

    def test_document_map_can_be_traversed_to_cload(self):
        children = child_entries(self.ccx_map, "node223.html")
        cload = next(item for item in children if item["title"] == "*CLOAD")
        self.assertEqual(cload["source_file"], "node242.html")

    def test_navigation_opens_authoritative_cload_page(self):
        page, raw, blocks = source_blocks(self.ccx_map, "node242.html")
        self.assertEqual(page["source_path"].split("/")[-1], "node242.html")
        self.assertIn("*CLOAD", raw)
        self.assertIn("concentrated forces", " ".join(block["text"] for block in blocks).lower())

    def test_content_cross_references_are_separate_from_navigation(self):
        references = reference_entries(self.ccx_map, "node242.html")
        sources = {item["source_file"] for item in references}
        self.assertIn("node353.html", sources)
        self.assertNotIn("node241.html", sources)
        self.assertNotIn("node243.html", sources)

    def test_exact_api_lookup_resolves_without_vector_search(self):
        matches = exact_entries(self.ccx_map, "CLOAD")
        self.assertEqual([match["source_file"] for match in matches], ["node242.html"])

    def test_api_catalog_has_keyword_and_command_summaries(self):
        catalogue = api_catalog(self.ccx_chunks + self.cgx_chunks)
        cload = next(item for item in catalogue if item["canonical_name"] == "*CLOAD")
        anim = next(
            item
            for item in catalogue
            if item["manual"] == "cgx" and item["canonical_name"] == "anim"
        )
        self.assertIn("concentrated forces", cload["summary"].lower())
        self.assertEqual(cload["artifact_type"], "keyword")
        self.assertIn("animation", anim["summary"].lower())
        self.assertTrue(anim["syntax"])

    def test_fuzzy_api_discovery_is_scoped_to_catalogue(self):
        catalogue = api_catalog(self.ccx_chunks + self.cgx_chunks)
        concentrated = discover_entries(
            catalogue,
            "How do I apply a concentrated point force to selected nodes?",
            "ccx",
        )
        pressure = discover_entries(
            catalogue,
            "Which input option applies distributed pressure over element faces?",
            "ccx",
        )
        self.assertEqual(concentrated[0]["canonical_name"], "*CLOAD")
        self.assertEqual(pressure[0]["canonical_name"], "*DLOAD")

        coordinate = discover_entries(
            catalogue,
            "CGX select nodes by rectangular coordinates with a tolerance",
            "cgx",
        )
        self.assertEqual(coordinate[0]["canonical_name"], "enq")

    def test_context_scope_expands_around_selected_chunk(self):
        chunks = [
            chunk
            for chunk in self.ccx_chunks
            if chunk["source_file"] == "node242.html" and chunk["kind"] != "figure"
        ]
        scopes = context_scopes("magnitude of the load", chunks)
        self.assertEqual(len(scopes["chunk"]["chunk_indices"]), 1)
        self.assertGreaterEqual(len(scopes["neighbours"]["chunk_indices"]), 2)
        self.assertEqual(len(scopes["page"]["chunk_indices"]), len(chunks))
        self.assertEqual(marker_coverage(scopes["page"]["text"], [["*cload"]]), (1, 1))

    def test_code_and_figure_chunks_have_locations(self):
        chunks = self.ccx_chunks + self.cgx_chunks
        self.assertTrue(any(chunk["kind"] == "code" for chunk in chunks))
        figures = [chunk for chunk in chunks if chunk["kind"] == "figure"]
        self.assertTrue(figures)
        self.assertTrue(all(chunk.get("asset_path") for chunk in figures))
        self.assertTrue(all(chunk.get("line_start") for chunk in figures))

    def test_figure_caption_is_bound_to_the_correct_asset(self):
        figure = next(
            chunk
            for chunk in self.ccx_chunks
            if chunk.get("asset_path", "").endswith("/img237.png")
        )
        self.assertEqual(
            figure["caption"],
            "Figure 53: Normal stress in z-direction for the coarse mesh",
        )
        self.assertIn("coarse mesh", figure["text"].lower())

    def test_caption_search_distinguishes_neighbouring_refinement_figures(self):
        figures = [
            chunk
            for chunk in self.ccx_chunks
            if chunk["kind"] == "figure" and chunk["source_file"] == "node24.html"
        ]
        ranked = lexical_figure_rank("error estimator for the fine mesh", figures)
        self.assertTrue(ranked[0]["asset_path"].endswith("/img240.png"))

    def test_chunks_fit_verified_character_budget(self):
        chunks = self.ccx_chunks + self.cgx_chunks
        self.assertLessEqual(max(len(chunk["text"]) for chunk in chunks), 800)
        self.assertLessEqual(max(len(chunk["embedding_text"]) for chunk in chunks), 1_024)

    def test_artifact_type_routing(self):
        self.assertEqual(requested_kind("diagram showing node numbering"), "figure")
        self.assertEqual(requested_kind("Fortran user subroutine arguments"), "code")
        self.assertIsNone(requested_kind("why does this element hourglass"))

    def test_bootstrap_supports_both_compose_frontends(self):
        self.assertEqual(
            compose_command(lambda name: "/usr/bin/docker-compose" if name == "docker-compose" else None),
            ["docker-compose"],
        )
        self.assertEqual(
            compose_command(lambda name: "/usr/bin/docker" if name == "docker" else None),
            ["docker", "compose"],
        )

    def test_multi_need_routes_are_unioned_without_score_fusion(self):
        need = {
            "acceptable_sources": [{"manual": "cgx", "source_file": "node79.html"}]
        }
        result = {
            "routes": {
                "api_catalogue": [{"manual": "cgx", "source_file": "node95.html"}],
                "semantic": [{"manual": "cgx", "source_file": "node251.html"}],
            },
            "explicit_references": {
                "api_catalogue": [],
                "semantic": [
                    {
                        "manual": "cgx",
                        "source_file": "node79.html",
                        "referenced_by": {
                            "manual": "cgx",
                            "source_file": "node251.html",
                        },
                    }
                ],
            },
        }
        self.assertFalse(
            need_covered(need, result, ["api_catalogue", "semantic"], 1)
        )
        self.assertTrue(
            need_covered(
                need,
                result,
                ["api_catalogue", "semantic"],
                1,
                include_references=True,
            )
        )

    def test_semantic_candidate_preserves_why_it_matched(self):
        ranked = source_rank(
            [{"id": "remote", "text": "matched source text", "score": 0.8}],
            {
                "remote": {
                    "manual": "cgx",
                    "source_file": "node95.html",
                    "title": "enq",
                }
            },
        )
        self.assertEqual(ranked[0]["excerpt"], "matched source text")


if __name__ == "__main__":
    unittest.main()
