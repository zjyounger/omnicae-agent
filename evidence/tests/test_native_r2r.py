import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from evidence.r2r.native_calculix import (
    NativeDocument,
    delete_corpus,
    inventory_documents,
    sync_corpus,
    sync_plan,
)


class FakeNativeClient:
    def __init__(self, document_ids=()):
        self.documents = set(document_ids)
        self.deleted = []
        self.created = []

    def document(self, document_id):
        return {"id": document_id} if document_id in self.documents else None

    def create(self, item):
        self.documents.add(item.document_id)
        self.created.append(item.key)
        return {"document_id": item.document_id}

    def delete(self, document_id):
        self.documents.discard(document_id)
        self.deleted.append(document_id)

    def search(self, query, document_ids, limit=10):
        return [item for item in document_ids if item in self.documents]


class NativeR2RInventoryTests(unittest.TestCase):
    def test_complete_calculix_html_inventory_is_stable(self):
        inventory = inventory_documents()
        self.assertEqual(len(inventory), 820)
        self.assertEqual(
            sum(item.manual == "ccx" for item in inventory.values()), 534
        )
        self.assertEqual(
            sum(item.manual == "cgx" for item in inventory.values()), 286
        )
        self.assertEqual(
            len({item.document_id for item in inventory.values()}), len(inventory)
        )

    def test_plan_distinguishes_add_update_rename_delete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manual = root / "manual"
            manual.mkdir()
            (manual / "keep.html").write_text("same", encoding="utf-8")
            (manual / "change.html").write_text("new", encoding="utf-8")
            (manual / "renamed.html").write_text("moved", encoding="utf-8")
            current = inventory_documents({"ccx": manual}, repo_root=root)
            old_hash = "sha256:" + hashlib.sha256(b"old").hexdigest()
            previous = {
                "calculix-2.23/ccx/keep.html": {
                    "content_hash": current[
                        "calculix-2.23/ccx/keep.html"
                    ].content_hash
                },
                "calculix-2.23/ccx/change.html": {"content_hash": old_hash},
                "calculix-2.23/ccx/old-name.html": {"content_hash": old_hash},
            }
            plan = sync_plan(previous, current)
            self.assertEqual(plan["unchanged"], ["calculix-2.23/ccx/keep.html"])
            self.assertEqual(plan["update"], ["calculix-2.23/ccx/change.html"])
            self.assertEqual(plan["delete"], ["calculix-2.23/ccx/old-name.html"])
            self.assertEqual(plan["create"], ["calculix-2.23/ccx/renamed.html"])

    def test_sync_and_delete_execute_incremental_lifecycle(self):
        def item(name, content_hash, document_id):
            return NativeDocument(
                key=name,
                manual="ccx",
                source_file=name.rsplit("/", 1)[-1],
                source_path="unused",
                content_hash=content_hash,
                document_id=document_id,
            )

        changed = item("calculix-2.23/ccx/changed.html", "sha256:new", "changed")
        kept = item("calculix-2.23/ccx/kept.html", "sha256:kept", "kept")
        added = item("calculix-2.23/ccx/added.html", "sha256:added", "added")
        inventory = {value.key: value for value in (changed, kept, added)}
        previous = {
            "calculix-2.23/ccx/changed.html": {
                "content_hash": "sha256:old",
                "document_id": "changed",
            },
            "calculix-2.23/ccx/kept.html": {
                "content_hash": "sha256:kept",
                "document_id": "kept",
            },
            "calculix-2.23/ccx/deleted.html": {
                "content_hash": "sha256:deleted",
                "document_id": "deleted",
            },
        }
        client = FakeNativeClient(("changed", "deleted"))
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            state_path.write_text(
                json.dumps({"schema_version": 1, "documents": previous}),
                encoding="utf-8",
            )
            result = sync_corpus(client, inventory, state_path)
            self.assertEqual(result["created"], [added.key])
            self.assertEqual(result["updated"], [changed.key])
            self.assertEqual(result["deleted"], ["calculix-2.23/ccx/deleted.html"])
            self.assertEqual(result["repaired"], [kept.key])
            self.assertEqual(client.documents, {"added", "changed", "kept"})

            deleted = delete_corpus(client, state_path)
            self.assertEqual(deleted, {"deleted": 3, "stale_search_results": 0})
            self.assertEqual(client.documents, set())


if __name__ == "__main__":
    unittest.main()
