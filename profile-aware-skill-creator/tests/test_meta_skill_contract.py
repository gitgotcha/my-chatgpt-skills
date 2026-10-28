"""Contract checks for RDS-JBryon-aware Skill authoring."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
SCHEMA = json.loads((ROOT / "schemas" / "profile-capability.schema.json").read_text(encoding="utf-8"))
AUTHORING = (ROOT / "references" / "profile-authoring-standard.md").read_text(encoding="utf-8")
RUNTIME = (ROOT.parent / "references" / "rds-jbryon-runtime.md").read_text(encoding="utf-8")


class MetaSkillContractTests(unittest.TestCase):
    def test_profile_branch_uses_the_shared_single_user_runtime(self):
        self.assertIn("RDS-JBryon runtime contract", SKILL)
        self.assertIn("rds` MCP", SKILL)
        self.assertIn("Do not generate account identity resolution", SKILL)
        self.assertIn("directory.resolve", RUNTIME)
        self.assertIn("snapshot.read", RUNTIME)
        self.assertIn("snapshot.patch", RUNTIME)
        self.assertNotIn("submit_event", SKILL + RUNTIME)
        self.assertNotIn("user.resolve", SKILL + RUNTIME)

    def test_schema_forbids_identity_and_event_protocol_fields(self):
        runtime = SCHEMA["properties"]["runtime"]
        fields = runtime["properties"]
        self.assertEqual("rds", fields["tool"]["const"])
        self.assertEqual("snapshot.read", fields["readOperation"]["const"])
        self.assertEqual("snapshot.patch", fields["writeOperation"]["const"])
        self.assertFalse(fields["accountIdentityResolution"]["const"])
        self.assertNotIn("identityResolveEvent", fields)
        self.assertNotIn("evidenceWriteEvent", fields)
        self.assertFalse(fields["directDriveAccess"]["const"])

    def test_authoring_standard_requires_route_and_snapshot_design(self):
        lowered = AUTHORING.lower()
        for phrase in ("json snapshot", "route", "revision", "preserve", "record conditions"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, lowered)
        self.assertNotIn("user.resolve", lowered)
        self.assertNotIn("submit_event", lowered)

    def test_plain_branch_does_not_acquire_persistent_state_artifacts(self):
        for phrase in (
            "references/profile-contract.md",
            "schemas/profile-capability.json",
            "tests/test_profile_contract.py",
        ):
            self.assertIn(phrase, SKILL)
        self.assertIn("plain Skill must not contain", SKILL)

    def test_meta_skill_preserves_user_approval_for_new_routes(self):
        self.assertIn("confirmation", SKILL.lower())
        self.assertIn("resolved target path", SKILL)
        self.assertIn("preserve every unrelated file", SKILL)

    def test_profile_schema_contains_no_legacy_protocol_vocabulary(self):
        serialized = json.dumps(SCHEMA)
        for term in ("submit_event", "user.resolve", "projection.read", "profile.evidence.recorded"):
            with self.subTest(term=term):
                self.assertNotIn(term, serialized)


if __name__ == "__main__":
    unittest.main()
