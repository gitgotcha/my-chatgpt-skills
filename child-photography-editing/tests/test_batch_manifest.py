import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from batch_manifest import create_manifest, record_item, finalize_batch


PASS_QA = {key: "pass" for key in ("identity", "childhood", "expression", "skin", "artifact", "theme", "batchConsistency")}


class BatchManifestTest(unittest.TestCase):
    def test_failed_item_cannot_become_anchor_or_enter_edited_outputs(self):
        manifest = create_manifest("batch-1", {"palette": ["green"], "approvedTreatmentHints": {"elements": {"density": "light"}}})
        record_item(manifest, {"sourceId": "a", "qa": {"identity": "fail"}, "output": "edited/a.png"})
        result = finalize_batch(manifest)
        self.assertIsNone(result["anchorSourceId"])
        self.assertEqual(result["editedOutputs"], [])
        self.assertEqual(result["items"][0]["status"], "rejected")
        self.assertIn("candidateOutput", result["items"][0])
        self.assertEqual(result["items"][0]["candidateOutput"], "edited/a.png")
        self.assertEqual(result["items"][0]["output"], "rejected/a.png")
        self.assertEqual(result["rejectedOutputs"], ["rejected/a.png"])

    def test_first_passing_item_becomes_immutable_anchor(self):
        manifest = create_manifest("batch-1", {"palette": ["cream", "orange"]})
        record_item(manifest, {"sourceId": "a", "qa": PASS_QA, "output": "edited/a.png"})
        record_item(manifest, {"sourceId": "b", "qa": PASS_QA, "output": "edited/b.png"})
        result = finalize_batch(manifest)
        self.assertEqual(result["anchorSourceId"], "a")
        self.assertEqual(result["editedOutputs"], ["edited/a.png", "edited/b.png"])

    def test_required_batch_consistency_qa_key_is_enforced(self):
        manifest = create_manifest("batch-1", {})
        qa = dict(PASS_QA)
        del qa["batchConsistency"]
        record_item(manifest, {"sourceId": "a", "qa": qa, "output": "edited/a.png"})
        self.assertEqual(finalize_batch(manifest)["items"][0]["status"], "rejected")

    def test_mutating_the_frozen_batch_lock_is_rejected(self):
        manifest = create_manifest("batch-1", {"palette": ["cream", "orange"]})
        self.assertIn("batchStyleLockHash", manifest)
        self.assertEqual(len(manifest["batchStyleLockHash"]), 64)
        manifest["batchStyleLock"]["palette"].append("old-green")
        with self.assertRaisesRegex(ValueError, "Batch Style Lock"):
            record_item(manifest, {"sourceId": "a", "qa": PASS_QA, "output": "edited/a.png"})

    def test_repeated_finalization_keeps_the_original_anchor(self):
        manifest = create_manifest("batch-1", {"palette": ["cream"]})
        record_item(manifest, {"sourceId": "b", "qa": PASS_QA, "output": "edited/b.png"})
        finalize_batch(manifest)
        record_item(manifest, {"sourceId": "a", "qa": PASS_QA, "output": "edited/a.png"})
        manifest["items"].insert(0, manifest["items"].pop())
        result = finalize_batch(manifest)
        self.assertEqual(result["anchorSourceId"], "b")

    def test_mutating_the_selected_anchor_is_rejected(self):
        manifest = create_manifest("batch-1", {"palette": ["cream"]})
        record_item(manifest, {"sourceId": "a", "qa": PASS_QA, "output": "edited/a.png"})
        record_item(manifest, {"sourceId": "b", "qa": PASS_QA, "output": "edited/b.png"})
        finalize_batch(manifest)
        manifest["anchorSourceId"] = "b"
        with self.assertRaisesRegex(ValueError, "anchor.*mutated"):
            finalize_batch(manifest)

    def test_invalidated_anchor_fails_loudly(self):
        manifest = create_manifest("batch-1", {"palette": ["cream"]})
        record_item(manifest, {"sourceId": "a", "qa": PASS_QA, "output": "edited/a.png"})
        record_item(manifest, {"sourceId": "b", "qa": PASS_QA, "output": "edited/b.png"})
        finalize_batch(manifest)
        manifest["items"][0]["qa"]["identity"] = "fail"
        with self.assertRaisesRegex(ValueError, "anchor.*invalid"):
            finalize_batch(manifest)


if __name__ == "__main__":
    unittest.main()
