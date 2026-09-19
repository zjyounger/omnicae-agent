import json
import tempfile
import unittest
from pathlib import Path

from evidence.manifest import (
    ManifestError,
    content_hash,
    load_and_validate,
    load_inventory,
    validate,
)


class SourceManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "knowledge" / "sample.txt"
        self.source.parent.mkdir()
        self.source.write_text("verified public evidence\n", encoding="utf-8")
        self.manifest = {
            "schema_version": 1,
            "id": "official/sample/v1",
            "path_or_url": "knowledge/sample.txt",
            "source_version": "1.0",
            "license": "MIT",
            "redistribution": "allowed",
            "content_hash": content_hash(self.source),
            "authority": "official",
        }

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_valid_local_manifest(self):
        validate(self.manifest, self.root)

    def test_loads_and_validates_json(self):
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        loaded = load_and_validate(manifest_path, self.root)
        self.assertEqual(loaded["id"], self.manifest["id"])

    def test_missing_provenance_is_rejected(self):
        del self.manifest["license"]
        with self.assertRaisesRegex(ManifestError, "missing required fields: license"):
            validate(self.manifest, self.root)

    def test_unknown_licence_is_rejected(self):
        self.manifest["license"] = "unknown"
        with self.assertRaisesRegex(ManifestError, "must identify"):
            validate(self.manifest, self.root)

    def test_changed_content_is_rejected(self):
        self.source.write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "content hash mismatch"):
            validate(self.manifest, self.root)

    def test_path_escape_is_rejected(self):
        self.manifest["path_or_url"] = "../outside.txt"
        with self.assertRaisesRegex(ManifestError, "repository root"):
            validate(self.manifest, self.root)

    def test_symlink_source_is_rejected(self):
        link = self.root / "knowledge" / "linked.txt"
        link.symlink_to(self.source)
        self.manifest["path_or_url"] = "knowledge/linked.txt"
        with self.assertRaisesRegex(ManifestError, "symlinks"):
            validate(self.manifest, self.root)

    def test_remote_source_does_not_require_a_local_copy(self):
        self.manifest["path_or_url"] = "https://example.org/manual-v1.pdf"
        self.manifest["redistribution"] = "fetch_only"
        validate(self.manifest, self.root)

    def test_directory_hash_changes_with_a_child(self):
        first = content_hash(self.source.parent)
        self.source.write_text("changed\n", encoding="utf-8")
        second = content_hash(self.source.parent)
        self.assertNotEqual(first, second)

    def test_duplicate_stable_id_is_rejected(self):
        first = self.root / "first.json"
        second = self.root / "second.json"
        serialized = json.dumps(self.manifest)
        first.write_text(serialized, encoding="utf-8")
        second.write_text(serialized, encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "duplicate source id"):
            load_inventory([first, second], self.root)


if __name__ == "__main__":
    unittest.main()
