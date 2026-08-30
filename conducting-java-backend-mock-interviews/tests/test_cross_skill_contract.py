from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
REVIEWING_ROOT = SKILL_ROOT.parent / "reviewing-java-backend-interviews"

# Every persisted skill resolves identity by display name through the same
# global registry under the same canonical plugin root.
SKILL_FILES = (
    SKILL_ROOT.parent / "algorithm-learning" / "SKILL.md",
    SKILL_ROOT / "SKILL.md",
    REVIEWING_ROOT / "SKILL.md",
)

REQUIRED_CONTRACT_TOKENS = (
    "submit_event",
    "my-chatGPT-skills",
    "userId",
    "姓名",
    "解析",
)

# Adjacent string literals keep retired identifiers out of this file's own
# text, so the repository-wide scan cannot match the checker itself.
RETIRED_IDENTITY_GATE = r"identity\.(list|create|verify)"
RETIRED_CANDIDATE_MODEL = (
    "Candidate" "Index",
    "Confirmed" "CandidateContext",
    "candidate" "_id",
)
RETIRED_ARTIFACT_CALLS = (
    "find_or_create_candidate", "list_candidates", "get_candidate_context",
    "read_artifact", "submit_artifact", "contentBase64", "raw_transcript.md",
)

CURRENT_SCHEMA_ARTIFACTS = {
    "Identity", "Registration", "Question", "SessionEvent",
    "QuestionReview", "ProfileChange", "ReviewEvent", "ProfileSnapshot",
}


class SharedSchemaTests(unittest.TestCase):
    def test_schema_copies_are_byte_identical(self) -> None:
        conducting_schema = SKILL_ROOT / "schemas" / "contracts.schema.json"
        reviewing_schema = REVIEWING_ROOT / "schemas" / "contracts.schema.json"
        self.assertEqual(conducting_schema.read_bytes(), reviewing_schema.read_bytes())
        contract = json.loads(conducting_schema.read_text(encoding="utf-8"))
        self.assertEqual(set(contract["$defs"]), CURRENT_SCHEMA_ARTIFACTS)
        self.assertEqual(contract["$defs"]["SessionEvent"]["properties"]["schemaVersion"]["const"], "1.2")
        self.assertEqual(contract["$defs"]["ReviewEvent"]["properties"]["schemaVersion"]["const"], "1.2")
        self.assertEqual(
            contract["$defs"]["ReviewEvent"]["properties"]["profileChanges"]["items"]["$ref"],
            "#/$defs/ProfileChange",
        )

    def test_manifest_lists_only_current_schema_12_artifacts(self) -> None:
        conducting_manifest = SKILL_ROOT / "schemas" / "manifest.json"
        reviewing_manifest = REVIEWING_ROOT / "schemas" / "manifest.json"
        self.assertEqual(conducting_manifest.read_bytes(), reviewing_manifest.read_bytes())
        manifest = json.loads(conducting_manifest.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "1.2")
        self.assertEqual(set(manifest["artifacts"]), CURRENT_SCHEMA_ARTIFACTS)

    def test_all_skills_resolve_identity_by_name_through_one_submit_event(self) -> None:
        identity_gate = re.compile(RETIRED_IDENTITY_GATE)
        for skill_path in SKILL_FILES:
            with self.subTest(skill=skill_path.parent.name):
                skill = skill_path.read_text(encoding="utf-8")
                for token in REQUIRED_CONTRACT_TOKENS:
                    self.assertIn(token, skill, f"{token} missing from {skill_path}")
                self.assertIsNone(identity_gate.search(skill), skill_path.as_posix())
                for removed in RETIRED_CANDIDATE_MODEL + RETIRED_ARTIFACT_CALLS:
                    self.assertNotIn(removed, skill, f"{removed} in {skill_path}")

    def test_interview_skills_place_events_below_canonical_user_roots(self) -> None:
        expected = {
            SKILL_ROOT.name: "users/<userId>/interview/events/",
            REVIEWING_ROOT.name: "users/<userId>/interview/events/",
        }
        for skill_dir, path in expected.items():
            with self.subTest(skill=skill_dir):
                skill = (SKILL_ROOT.parent / skill_dir / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(path, skill)

    def test_mock_interview_source_mix_is_project_first(self) -> None:
        skill_path = SKILL_ROOT / "SKILL.md"
        skill = skill_path.read_text(encoding="utf-8")
        for ratio in ("简历/项目 55%", "历史弱点变式 15%", "领域知识 10%", "算法与场景 20%"):
            self.assertIn(ratio, skill)
        self.assertIn("主来源", skill)
        self.assertIn("topicTags", skill)
        self.assertIn("最大余数法", skill)

    def test_interview_protocol_matches_the_skill_source_mix(self) -> None:
        protocol = (SKILL_ROOT / "references" / "interview-protocol.md").read_text(encoding="utf-8")
        for ratio in ("简历/项目 55%", "历史弱点变式 15%", "领域知识 10%", "算法与场景 20%"):
            self.assertIn(ratio, protocol)

    def test_profile_integration_uses_global_user_id_not_candidate_index(self) -> None:
        integration = (
            SKILL_ROOT / "references" / "candidate-profile-integration.md"
        ).read_text(encoding="utf-8")
        self.assertIn("userId", integration)
        self.assertIn("submit_event", integration)
        for removed in RETIRED_CANDIDATE_MODEL:
            self.assertNotIn(removed, integration)


if __name__ == "__main__":
    unittest.main()
