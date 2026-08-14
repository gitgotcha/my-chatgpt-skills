from __future__ import annotations

import json
from pathlib import Path
import unittest


class SharedSchemaTests(unittest.TestCase):
    def test_schema_copies_are_byte_identical(self) -> None:
        conducting_root = Path(__file__).resolve().parents[1]
        reviewing_root = conducting_root.parent / "reviewing-java-backend-interviews"
        conducting_schema = conducting_root / "schemas" / "contracts.schema.json"
        reviewing_schema = reviewing_root / "schemas" / "contracts.schema.json"
        self.assertEqual(conducting_schema.read_bytes(), reviewing_schema.read_bytes())
        contract = json.loads(conducting_schema.read_text(encoding="utf-8"))
        self.assertEqual(set(contract["$defs"]), {
            "Identity", "Registration", "Question", "SessionEvent",
            "QuestionReview", "ReviewEvent", "ProfileSnapshot",
        })
        self.assertEqual(contract["$defs"]["SessionEvent"]["properties"]["schemaVersion"]["const"], "1.2")

    def test_all_interview_skills_use_identity_gate_and_one_submit_event(self) -> None:
        skill_root = Path(__file__).resolve().parents[1]
        skills = [
            skill_root.parent / "algorithm-learning" / "SKILL.md",
            skill_root / "SKILL.md",
            skill_root.parent / "reviewing-java-backend-interviews" / "SKILL.md",
        ]
        for skill_path in skills:
            skill = skill_path.read_text(encoding="utf-8")
            self.assertIn("submit_event", skill, skill_path.as_posix())
            self.assertIn("identity.list", skill, skill_path.as_posix())
            self.assertIn("identity.verify", skill, skill_path.as_posix())
            self.assertIn("identity.create", skill, skill_path.as_posix())
            for removed in (
                "find_or_create_candidate", "list_candidates", "get_candidate_context",
                "read_artifact", "submit_artifact", "contentBase64", "raw_transcript.md",
            ):
                self.assertNotIn(removed, skill, f"{removed} in {skill_path}")
