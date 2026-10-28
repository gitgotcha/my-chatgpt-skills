from __future__ import annotations

import json
from pathlib import Path
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
REVIEWING_ROOT = SKILL_ROOT.parent / "reviewing-java-backend-interviews"
SNAPSHOT_ARTIFACTS = {
    "Question", "SessionSnapshot", "QuestionReview", "ProfileChange",
    "ReviewSnapshot", "ProjectEvidence", "ProjectAssessment",
}


class SharedSnapshotContractTests(unittest.TestCase):
    def test_schema_and_manifest_copies_match(self) -> None:
        schema_path = SKILL_ROOT / "schemas" / "contracts.schema.json"
        review_schema_path = REVIEWING_ROOT / "schemas" / "contracts.schema.json"
        self.assertEqual(schema_path.read_bytes(), review_schema_path.read_bytes())
        manifest_path = SKILL_ROOT / "schemas" / "manifest.json"
        review_manifest_path = REVIEWING_ROOT / "schemas" / "manifest.json"
        self.assertEqual(manifest_path.read_bytes(), review_manifest_path.read_bytes())
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(set(schema["$defs"]), SNAPSHOT_ARTIFACTS)
        self.assertEqual(set(manifest["artifacts"]), SNAPSHOT_ARTIFACTS)
        self.assertEqual(manifest["schema_version"], "rds-jbryon-interview-snapshots/2")
        serialized = json.dumps(schema)
        for retired in ('"userId"', '"username"', '"eventId"', '"eventKey"', '"eventType"'):
            self.assertNotIn(retired, serialized)

    def test_profile_skills_use_the_single_user_rds_route_contract(self) -> None:
        files = (
            SKILL_ROOT.parent / "algorithm-learning" / "SKILL.md",
            SKILL_ROOT / "SKILL.md",
            REVIEWING_ROOT / "SKILL.md",
        )
        for path in files:
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path.parent.name):
                self.assertIn("RDS-JBryon", text)
                self.assertNotIn("user.resolve", text)
                self.assertNotIn("account.register", text)
                self.assertNotIn("submit_event", text)

    def test_mock_interview_uses_the_project_snapshot(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        integration = (SKILL_ROOT / "references" / "candidate-profile-integration.md").read_text(encoding="utf-8")
        for token in ("project/12306", "学习快照.json", "字节跳动校招 Java 后端"):
            self.assertIn(token, skill + integration)
        self.assertIn("不代表需要建立独立用户画像", integration)

    def test_mock_interview_keeps_the_project_first_question_mix(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        protocol = (SKILL_ROOT / "references" / "interview-protocol.md").read_text(encoding="utf-8")
        self.assertIn("一次只问一道", skill)
        self.assertIn("简历声明", skill)
        for ratio in ("简历/项目 55%", "历史弱点变式 15%", "领域知识 10%", "算法与场景 20%"):
            self.assertIn(ratio, protocol)


if __name__ == "__main__":
    unittest.main()
