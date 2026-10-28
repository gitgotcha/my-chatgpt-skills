"""Contract checks for the RDS-JBryon planning snapshot workflow."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_TEXT = (ROOT / "SKILL.md").read_text(encoding="utf-8")
CONTRACT_TEXT = (ROOT / "references" / "profile-contract.md").read_text(encoding="utf-8")
RUNTIME_TEXT = (ROOT.parent / "references" / "rds-jbryon-runtime.md").read_text(encoding="utf-8")
CAPABILITY = json.loads((ROOT / "schemas" / "profile-capability.json").read_text(encoding="utf-8"))


def build_patch(snapshot: dict, revision: int, date: str, report: dict) -> dict:
    """Build a minimal append-only update without replacing prior records."""
    if not isinstance(revision, int) or revision < 0:
        raise ValueError("invalid_revision")
    records = list(snapshot.get("records", []))
    records.append({"date": date, **report})
    return {"baseRevision": revision, "changes": [{"op": "set", "path": ["records"], "value": records}]}


def confirm_new_route(path: str, confirmed: bool) -> str:
    """Require explicit confirmation before creating a new readable path."""
    if not confirmed:
        raise PermissionError("route_confirmation_required")
    return path


class PlanningSnapshotContractTests(unittest.TestCase):
    def test_capability_uses_single_user_rds_snapshot_route(self):
        runtime = CAPABILITY["runtime"]
        self.assertEqual("rds", runtime["tool"])
        self.assertEqual("snapshot.read", runtime["readOperation"])
        self.assertEqual("snapshot.patch", runtime["writeOperation"])
        self.assertEqual("user-readable-path", runtime["routePolicy"])
        self.assertFalse(runtime["accountIdentityResolution"])
        self.assertFalse(runtime["directDriveAccess"])

    def test_skill_links_runtime_and_reports_read_save_boundaries(self):
        self.assertIn("references/rds-jbryon-runtime.md", SKILL_TEXT)
        self.assertIn("knowledge/study-planning/规划快照.json", SKILL_TEXT)
        self.assertIn("projected", CONTRACT_TEXT)
        self.assertIn("不回退到旧服务", SKILL_TEXT)

    def test_runtime_contract_has_readable_paths_and_request_status(self):
        for phrase in ("\"kind\":\"query\"", "directory.resolve", "snapshot.read", "snapshot.patch", "request.status", "projected"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, RUNTIME_TEXT)
        self.assertNotIn("submit_event", SKILL_TEXT + CONTRACT_TEXT)
        self.assertNotIn("user.resolve", SKILL_TEXT + CONTRACT_TEXT)

    def test_patch_appends_and_uses_current_revision(self):
        old = {"records": [{"date": "2026-10-26", "minutes": 50}]}
        update = build_patch(old, 4, "2026-10-27", {"minutes": 40, "outcome": "partial"})
        self.assertEqual(4, update["baseRevision"])
        self.assertEqual(old["records"][0], update["changes"][0]["value"][0])
        self.assertEqual("2026-10-27", update["changes"][0]["value"][1]["date"])
        self.assertEqual(1, len(old["records"]))

    def test_invalid_revision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_revision"):
            build_patch({}, -1, "2026-10-27", {"minutes": 10})

    def test_explicit_confirmation_is_required_for_a_new_route(self):
        with self.assertRaisesRegex(PermissionError, "route_confirmation_required"):
            confirm_new_route("knowledge/study-planning/规划快照.json", False)
        self.assertEqual(
            "knowledge/study-planning/规划快照.json",
            confirm_new_route("knowledge/study-planning/规划快照.json", True),
        )

    def test_contract_keeps_observation_and_source_boundaries(self):
        for phrase in ("只记录用户明确说出的时间", "当前 revision", "projected"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, CONTRACT_TEXT)
        self.assertNotIn("d1_committed", CONTRACT_TEXT)
        self.assertNotIn("archived", CONTRACT_TEXT)


if __name__ == "__main__":
    unittest.main()
